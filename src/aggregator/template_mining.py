"""Pure Drain3 template mining primitives."""

# Drain3 is intentionally dynamically typed.
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import re
from collections.abc import Hashable, Iterable
from dataclasses import dataclass

from drain3 import TemplateMiner
from drain3.masking import AbstractMaskingInstruction, MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig
from iso4217 import Currency

MINIMUM_CLUSTER_SIZE = 3

_AMOUNT_BODY_PATTERN = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3}|\d+)(?:\.\d+)?"
_AMOUNT_END_PATTERN = r"(?![\w]|\.\d|,\d)"
_ISO_CURRENCY_CODES_PATTERN = "|".join(currency.code for currency in Currency)
_CURRENCY_BODY_PATTERN = (
    rf"(?:[$€£¥₹]|(?<!\w)(?:(?i:{_ISO_CURRENCY_CODES_PATTERN})|"
    r"(?i:RS\.?))(?![A-Za-z_]))"
)


class MoneyMaskingInstruction(AbstractMaskingInstruction):
    """Mask a currency and amount atomically while retaining both parameter types."""

    def __init__(self) -> None:
        super().__init__("MONEY")
        self.regex = re.compile(
            rf"{_CURRENCY_BODY_PATTERN}\s*{_AMOUNT_BODY_PATTERN}{_AMOUNT_END_PATTERN}"
        )

    @property
    def pattern(self) -> str:
        return self.regex.pattern

    def mask(self, content: str, mask_prefix: str, mask_suffix: str) -> str:
        currency_mask = f"{mask_prefix}CURRENCY_CODE{mask_suffix}"
        amount_mask = f"{mask_prefix}NUMBER{mask_suffix}"
        return self.regex.sub(currency_mask + amount_mask, content)


# Keep dates and times before generic numbers so their components remain intact.
# Money is masked first so its currency and amount form one Drain3 token. The
# component masks remain available for exact extraction and standalone values.
MASKING_INSTRUCTIONS = (
    MoneyMaskingInstruction(),
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
        rf"{_CURRENCY_BODY_PATTERN}(?=\s*{_AMOUNT_BODY_PATTERN}{_AMOUNT_END_PATTERN})\s*",
        "CURRENCY_CODE",
    ),
    MaskingInstruction(
        rf"(?:(?<![\w.,])|(?<=(?i:rs\.))){_AMOUNT_BODY_PATTERN}{_AMOUNT_END_PATTERN}",
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
    return [
        ExtractedParameter(
            parameter.value.strip() if parameter.mask_name == "CURRENCY_CODE" else parameter.value,
            parameter.mask_name,
        )
        for parameter in parameters
    ]


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
    existing_templates = tuple(existing_templates)
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
