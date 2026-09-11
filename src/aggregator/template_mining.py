"""Pure Drain3 template mining primitives."""

# Drain3 is intentionally dynamically typed.
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from collections.abc import Hashable, Iterable
from dataclasses import dataclass

from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

MINIMUM_CLUSTER_SIZE = 3

# Keep dates and times before generic numbers so their components remain intact.
# Currency codes are masked separately, leaving their amounts as number masks.
MASKING_INSTRUCTIONS = (
    MaskingInstruction(
        r"(?<!\w)(?:"
        r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|"
        r"(?i:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\.?\s+\d{1,2}(?i:st|nd|rd|th)?\s*,?\s*\d{2,4}|"
        r"\d{1,2}(?i:st|nd|rd|th)?\s+(?i:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
        r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
        r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s*,?\s*\d{2,4}"
        r")(?!\w)",
        "DATE",
    ),
    MaskingInstruction(
        r"(?<![\w:])(?:0?\d|1\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:[.,]\d{1,6})?)?(?:\s*(?i:a\.?m\.?|p\.?m\.?))?(?:\s*(?:Z|(?i:UTC|GMT)(?:\s*[+-]\d{1,2}(?::?\d{2})?)?|[+-]\d{2}:?\d{2}))?(?![\w:])",
        "TIME",
    ),
    MaskingInstruction(
        r"(?:[$€£¥₹]|(?<!\w)(?:(?i:USD|EUR|GBP|INR|JPY|CAD|AUD)(?!\w)|(?i:RS\.?)(?![A-Za-z_])))\s*",
        "CURRENCY_CODE",
    ),
    MaskingInstruction(
        r"(?:(?<![\w.,])|(?<=(?i:rs\.)))[+-]?(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3}|\d+)(?:\.\d+)?(?![\w]|\.\d|,\d)",
        "NUMBER",
    ),
)


@dataclass(frozen=True, slots=True)
class ExtractedParameter:
    """Application-owned value extracted from a template parameter."""

    value: str
    mask_name: str


@dataclass(frozen=True, slots=True)
class MiningRecord:
    """A single piece of text supplied to the in-memory miner."""

    record_id: Hashable
    text: str


@dataclass(frozen=True, slots=True)
class MinedPattern:
    """An eligible Drain3 pattern and its source records, in input order."""

    text: str
    record_ids: tuple[Hashable, ...]


@dataclass(frozen=True, slots=True)
class MiningResult:
    """The database-independent outcome of mining a batch of records."""

    processed: int
    skipped_record_ids: tuple[Hashable, ...]
    patterns: tuple[MinedPattern, ...]


def _create_miner() -> TemplateMiner:
    """Create the in-memory miner with this module's masking rules."""
    config = TemplateMinerConfig()
    config.masking_instructions = list(MASKING_INSTRUCTIONS)
    # config.drain_extra_delimiters = ["."]
    return TemplateMiner(config=config)


def get_extracted_parameters(
    mining_record: MiningRecord, template_text: str
) -> list[ExtractedParameter]:
    """Extract the ordered masked values for a record and a mined template."""
    miner = _create_miner()
    parameters = miner.extract_parameters(template_text, mining_record.text) or []
    return [ExtractedParameter(parameter.value, parameter.mask_name) for parameter in parameters]


def bulk_mine_templates(
    records: Iterable[MiningRecord], existing_templates: Iterable[str] = ()
) -> MiningResult:
    """Mine eligible patterns from records without reading or writing persistence.

    Each non-empty record is first matched against the existing templates in
    their supplied order. Unmatched records are mined for new patterns. Existing
    template order is followed by Drain3's cluster creation order, and each
    pattern's record IDs retain input order.
    """
    miner = _create_miner()
    record_ids_by_existing_template: dict[str, list[Hashable]] = {}
    record_ids_by_cluster: dict[int, list[Hashable]] = {}
    skipped_record_ids: list[Hashable] = []
    processed = 0

    for record in records:
        if not record.text.strip():
            skipped_record_ids.append(record.record_id)
            continue
        processed += 1

        matching_template = next(
            (
                template_text
                for template_text in existing_templates
                if miner.extract_parameters(template_text, record.text) is not None
            ),
            None,
        )
        if matching_template is not None:
            record_ids_by_existing_template.setdefault(matching_template, []).append(
                record.record_id
            )
            continue

        result = miner.add_log_message(record.text)
        cluster_id = int(result["cluster_id"])
        record_ids_by_cluster.setdefault(cluster_id, []).append(record.record_id)

    existing_patterns = tuple(
        MinedPattern(
            text=template_text,
            record_ids=tuple(record_ids_by_existing_template[template_text]),
        )
        for template_text in existing_templates
        if template_text in record_ids_by_existing_template
    )
    mined_patterns = tuple(
        MinedPattern(
            text=cluster.get_template(),
            record_ids=tuple(record_ids_by_cluster[cluster.cluster_id]),
        )
        for cluster in miner.drain.clusters
        if cluster.size >= MINIMUM_CLUSTER_SIZE
    )
    return MiningResult(
        processed=processed,
        skipped_record_ids=tuple(skipped_record_ids),
        patterns=existing_patterns + mined_patterns,
    )
