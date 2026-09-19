"""Local PII sanitization for text sent to template classification."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import InAadhaarRecognizer, InPanRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.entities import RecognizerResult as AnonymizerRecognizerResult

from .template_syntax import TEMPLATE_PARAMETER_PATTERN

_MODEL_NAME = "en_core_web_md"
_LANGUAGE = "en"
_MINIMUM_SCORE = 0.35

# This list is intentionally limited to recognizers included with Presidio.
_ANALYZED_ENTITIES = (
    "PERSON",
    "LOCATION",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "URL",
    "IN_PAN",
    "IN_AADHAAR",
)

_REPLACEMENTS = {
    "PERSON": "<PERSON>",
    "LOCATION": "<LOCATION>",
    "EMAIL_ADDRESS": "<EMAIL>",
    "PHONE_NUMBER": "<PHONE_NUMBER>",
    "CREDIT_CARD": "<CREDIT_CARD>",
    "IBAN_CODE": "<IBAN>",
    "URL": "<URL>",
    "IN_PAN": "<PAN>",
    "IN_AADHAAR": "<AADHAAR>",
}

_ENTITY_PRIORITY = {
    "LOCATION": 10,
    "PERSON": 20,
    "URL": 30,
    "PHONE_NUMBER": 40,
    "EMAIL_ADDRESS": 50,
    "CREDIT_CARD": 60,
    "IBAN_CODE": 60,
    "IN_PAN": 60,
    "IN_AADHAAR": 60,
}


class PiiSanitizationError(RuntimeError):
    """Raised when local PII sanitization cannot safely complete."""


@dataclass(frozen=True, slots=True)
class _Engines:
    analyzer: AnalyzerEngine
    anonymizer: AnonymizerEngine


@dataclass(frozen=True, slots=True)
class _Detection:
    entity_type: str
    start: int
    end: int
    score: float


def _build_engines() -> _Engines:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": _LANGUAGE, "model_name": _MODEL_NAME}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=configuration).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=[_LANGUAGE])

    # Presidio ships these recognizers but disables them in its default registry.
    analyzer.registry.add_recognizer(InPanRecognizer())
    analyzer.registry.add_recognizer(InAadhaarRecognizer())
    return _Engines(analyzer=analyzer, anonymizer=AnonymizerEngine())


@lru_cache(maxsize=1)
def _get_engines() -> _Engines:
    try:
        return _build_engines()
    except Exception:
        raise PiiSanitizationError(
            "Unable to initialize the PII sanitizer. Run `uv sync` and verify that "
            "the en_core_web_md package is installed."
        ) from None


def _exclude_placeholders(
    detections: list[_Detection], placeholder_spans: list[tuple[int, int]]
) -> list[_Detection]:
    protected: list[_Detection] = []
    for detection in detections:
        segments = [(detection.start, detection.end)]
        for placeholder_start, placeholder_end in placeholder_spans:
            next_segments: list[tuple[int, int]] = []
            for start, end in segments:
                if placeholder_end <= start or placeholder_start >= end:
                    next_segments.append((start, end))
                    continue
                if start < placeholder_start:
                    next_segments.append((start, placeholder_start))
                if placeholder_end < end:
                    next_segments.append((placeholder_end, end))
            segments = next_segments
        protected.extend(
            _Detection(
                entity_type=detection.entity_type,
                start=start,
                end=end,
                score=detection.score,
            )
            for start, end in segments
            if start < end
        )
    return protected


def _resolve_overlaps(detections: list[_Detection]) -> list[_Detection]:
    """Merge overlapping spans and retain the most specific Presidio entity."""
    if not detections:
        return []

    ordered = sorted(detections, key=lambda item: (item.start, item.end))
    resolved: list[_Detection] = []
    group = [ordered[0]]
    group_end = ordered[0].end

    def append_group(items: list[_Detection], end: int) -> None:
        selected = max(
            items,
            key=lambda item: (
                _ENTITY_PRIORITY[item.entity_type],
                item.score,
                item.end - item.start,
            ),
        )
        resolved.append(
            _Detection(
                entity_type=selected.entity_type,
                start=min(item.start for item in items),
                end=end,
                score=max(item.score for item in items),
            )
        )

    for detection in ordered[1:]:
        if detection.start < group_end:
            group.append(detection)
            group_end = max(group_end, detection.end)
            continue
        append_group(group, group_end)
        group = [detection]
        group_end = detection.end
    append_group(group, group_end)
    return resolved


def sanitize_template_text(text: str) -> str:
    """Replace Presidio-detected PII while preserving mining placeholders."""
    if not text:
        return text

    try:
        engines = _get_engines()
        analyzer_results = engines.analyzer.analyze(
            text=text,
            language=_LANGUAGE,
            entities=list(_ANALYZED_ENTITIES),
            score_threshold=_MINIMUM_SCORE,
        )
        detections = [
            _Detection(
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
                score=result.score,
            )
            for result in analyzer_results
            if result.entity_type in _REPLACEMENTS
        ]
        placeholder_spans = [
            (match.start(), match.end()) for match in TEMPLATE_PARAMETER_PATTERN.finditer(text)
        ]
        detections = _resolve_overlaps(_exclude_placeholders(detections, placeholder_spans))
        anonymizer_results = [
            AnonymizerRecognizerResult(
                entity_type=detection.entity_type,
                start=detection.start,
                end=detection.end,
                score=detection.score,
            )
            for detection in detections
        ]
        operators = {
            entity_type: OperatorConfig("replace", {"new_value": replacement})
            for entity_type, replacement in _REPLACEMENTS.items()
        }
        return engines.anonymizer.anonymize(
            text=text,
            analyzer_results=anonymizer_results,
            operators=operators,
            merge_entities_with_spaces=False,
        ).text
    except PiiSanitizationError:
        raise
    except Exception:
        raise PiiSanitizationError(
            "Unable to sanitize template text; no TypeSafe request was made."
        ) from None
