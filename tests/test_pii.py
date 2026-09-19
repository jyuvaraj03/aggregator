# Tests intentionally exercise lazy initialization and span handling internals.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

from aggregator import pii


@pytest.fixture(autouse=True)
def clear_cached_engines() -> Generator[None]:
    original_get_engines = pii._get_engines
    original_get_engines.cache_clear()
    try:
        yield
    finally:
        original_get_engines.cache_clear()


def _recognition(text: str, value: str, entity_type: str, *, offset: int = 0) -> RecognizerResult:
    start = text.index(value, offset)
    return RecognizerResult(
        entity_type=entity_type,
        start=start,
        end=start + len(value),
        score=0.9,
    )


def _stub_analyzer(monkeypatch: pytest.MonkeyPatch, results: list[RecognizerResult]) -> MagicMock:
    analyzer = MagicMock(spec=AnalyzerEngine)
    analyzer.analyze.return_value = results
    engines = pii._Engines(analyzer=analyzer, anonymizer=AnonymizerEngine())
    monkeypatch.setattr(pii, "_get_engines", lambda: engines)
    return analyzer


def test_sanitizer_uses_only_presidio_supported_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = _stub_analyzer(monkeypatch, [])

    assert pii.sanitize_template_text("Payment completed") == "Payment completed"

    analyzer.analyze.assert_called_once_with(
        text="Payment completed",
        language="en",
        entities=[
            "PERSON",
            "LOCATION",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "IBAN_CODE",
            "URL",
            "IN_PAN",
            "IN_AADHAAR",
        ],
        score_threshold=0.35,
    )


def test_sanitizer_replaces_repeated_and_overlapping_detections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "Email amit@example.com, then repeat amit@example.com."
    first_email = _recognition(text, "amit@example.com", "EMAIL_ADDRESS")
    first_domain = _recognition(text, "example.com", "URL")
    second_start = text.index("amit@example.com", first_email.end)
    second_email = _recognition(
        text,
        "amit@example.com",
        "EMAIL_ADDRESS",
        offset=second_start,
    )
    second_domain = _recognition(text, "example.com", "URL", offset=second_start)
    _stub_analyzer(
        monkeypatch,
        [first_email, first_domain, second_email, second_domain],
    )

    sanitized = pii.sanitize_template_text(text)

    assert sanitized == "Email <EMAIL>, then repeat <EMAIL>."
    assert "amit@example.com" not in sanitized
    assert "example.com" not in sanitized


def test_sanitizer_preserves_placeholders_inside_detection_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "private<NUMBER>value on <DATE> ref <*>"
    _stub_analyzer(
        monkeypatch,
        [
            RecognizerResult(
                entity_type="URL",
                start=0,
                end=len("private<NUMBER>value"),
                score=0.9,
            ),
            _recognition(text, "<DATE>", "PERSON"),
            _recognition(text, "<*>", "LOCATION"),
        ],
    )

    assert pii.sanitize_template_text(text) == "<URL><NUMBER><URL> on <DATE> ref <*>"


def test_empty_input_does_not_initialize_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    get_engines = MagicMock(side_effect=AssertionError("engines should not load"))
    monkeypatch.setattr(pii, "_get_engines", get_engines)

    assert pii.sanitize_template_text("") == ""
    get_engines.assert_not_called()


def test_engines_are_initialized_once_per_process(monkeypatch: pytest.MonkeyPatch) -> None:
    engines = pii._Engines(
        analyzer=MagicMock(spec=AnalyzerEngine),
        anonymizer=AnonymizerEngine(),
    )
    build_engines = MagicMock(return_value=engines)
    monkeypatch.setattr(pii, "_build_engines", build_engines)

    assert pii._get_engines() is engines
    assert pii._get_engines() is engines
    build_engines.assert_called_once_with()


def test_initialization_failure_has_actionable_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pii,
        "_build_engines",
        MagicMock(side_effect=OSError("private model path")),
    )

    with pytest.raises(pii.PiiSanitizationError) as error:
        pii._get_engines()

    assert "uv sync" in str(error.value)
    assert "private model path" not in str(error.value)


def test_sanitization_failure_does_not_include_input_in_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = MagicMock(spec=AnalyzerEngine)
    analyzer.analyze.side_effect = ValueError("failed on amit@example.com")
    engines = SimpleNamespace(analyzer=analyzer, anonymizer=AnonymizerEngine())
    monkeypatch.setattr(pii, "_get_engines", lambda: engines)

    with pytest.raises(pii.PiiSanitizationError) as error:
        pii.sanitize_template_text("Email amit@example.com")

    assert "no TypeSafe request was made" in str(error.value)
    assert "amit@example.com" not in str(error.value)


def test_real_model_sanitizes_supported_english_and_indian_entities() -> None:
    text = (
        "Amit Patel paid INR <NUMBER> in Bengaluru on <DATE>.\n"
        "Email: amit.patel@example.com\n"
        "Phone: +91 98765 43210\n"
        "Card: 4111 1111 1111 1111\n"
        "IBAN: GB82 WEST 1234 5698 7654 32\n"
        "PAN: ABCDE1234F\n"
        "Aadhaar: 2345 6789 0124\n"
        "Portal: https://www.example.com/customer/amit-patel\n"
        "Reference: <*>"
    )

    sanitized = pii.sanitize_template_text(text)

    for sensitive_value in (
        "Amit Patel",
        "Bengaluru",
        "amit.patel@example.com",
        "+91 98765 43210",
        "4111 1111 1111 1111",
        "GB82 WEST 1234 5698 7654 32",
        "ABCDE1234F",
        "2345 6789 0124",
        "https://www.example.com/customer/amit-patel",
    ):
        assert sensitive_value not in sanitized
    assert "paid INR <NUMBER>" in sanitized
    assert "on <DATE>" in sanitized
    assert "Reference: <*>" in sanitized
    for marker in {
        "<PERSON>",
        "<LOCATION>",
        "<EMAIL>",
        "<PHONE_NUMBER>",
        "<CREDIT_CARD>",
        "<IBAN>",
        "<PAN>",
        "<AADHAAR>",
        "<URL>",
    }:
        assert marker in sanitized
