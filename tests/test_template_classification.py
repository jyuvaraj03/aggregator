from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownMemberType=false
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from playhouse.migrations import Runner
from typesafe_sdk import Noul

from aggregator import template_classification
from aggregator.database import PROJECT_ROOT, close_database, database, database_connection
from aggregator.models import Template
from aggregator.pii import PiiSanitizationError
from aggregator.queries import TemplateNotFoundError


@pytest.fixture(autouse=True)
def isolated_database(tmp_path: Path) -> Generator[None]:
    close_database()
    original_path = database.database
    database.init(str(tmp_path / "classification.sqlite3"))
    with database_connection():
        Runner(database, directory=str(PROJECT_ROOT / "migrations")).up()
    try:
        yield
    finally:
        close_database()
        database.init(original_path)


@pytest.fixture(autouse=True)
def stub_pii_sanitizer(monkeypatch: pytest.MonkeyPatch) -> None:
    def identity(text: str) -> str:
        return text

    monkeypatch.setattr(template_classification, "sanitize_template_text", identity)


@pytest.mark.parametrize(
    ("probability", "prediction"),
    [
        (0.0, False),
        (0.3, False),
        (0.31, None),
        (0.5, None),
        (0.69, None),
        (0.7, True),
        (1.0, True),
    ],
)
def test_typesafe_predictor_maps_probability_to_classification(
    monkeypatch: pytest.MonkeyPatch,
    probability: float,
    prediction: bool | None,
) -> None:
    client = MagicMock()
    client.__enter__.return_value = client
    client.system_one.return_value = SimpleNamespace(
        nouls={"is_transaction_alert": SimpleNamespace(noul=probability)}
    )
    client_class = MagicMock(return_value=client)
    monkeypatch.setattr(template_classification, "TypeSafeClient", client_class)
    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    assert predictor.predict("Paid <NUMBER>") is prediction

    client_class.assert_called_once()
    assert client_class.call_args.kwargs["api_key"] == "test-key"
    assert client_class.call_args.kwargs["retry"].max_retries == 0
    client.system_one.assert_called_once_with(
        state={"email_template": "Paid <NUMBER>"},
        questions={
            "is_transaction_alert": Noul(
                instructions="Is the given email template a bank/wallet/card transaction alert?"
            )
        },
    )


def test_typesafe_predictor_requires_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    monkeypatch.setattr(template_classification, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeError, match="JEV_API_KEY must be set"):
        template_classification.TemplateClassificationPredictor()


def test_typesafe_predictor_sends_only_sanitized_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_text = "Amit Patel paid <NUMBER>; email amit@example.com"
    sanitized_text = "<PERSON> paid <NUMBER>; email <EMAIL>"
    sanitizer = MagicMock(return_value=sanitized_text)
    monkeypatch.setattr(template_classification, "sanitize_template_text", sanitizer)
    client = MagicMock()
    client.__enter__.return_value = client
    client.system_one.return_value = SimpleNamespace(
        nouls={"is_transaction_alert": SimpleNamespace(noul=0.8)}
    )
    client_class = MagicMock(return_value=client)
    monkeypatch.setattr(template_classification, "TypeSafeClient", client_class)

    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    assert predictor.predict(raw_text) is True
    sanitizer.assert_called_once_with(raw_text)
    client.system_one.assert_called_once()
    request_state = client.system_one.call_args.kwargs["state"]
    assert request_state == {"email_template": sanitized_text}
    assert "Amit Patel" not in request_state["email_template"]
    assert "amit@example.com" not in request_state["email_template"]
    assert "paid <NUMBER>" in request_state["email_template"]


def test_sanitizer_failure_prevents_client_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    sanitizer = MagicMock(side_effect=PiiSanitizationError("sanitizer unavailable"))
    client_class = MagicMock()
    monkeypatch.setattr(template_classification, "sanitize_template_text", sanitizer)
    monkeypatch.setattr(template_classification, "TypeSafeClient", client_class)
    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    with pytest.raises(PiiSanitizationError, match="sanitizer unavailable"):
        predictor.predict("Amit Patel paid <NUMBER>")

    client_class.assert_not_called()


def test_typesafe_predictor_propagates_service_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.__enter__.return_value = client
    client.system_one.side_effect = ConnectionError("TypeSafe unavailable")
    monkeypatch.setattr(template_classification, "TypeSafeClient", MagicMock(return_value=client))
    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    with pytest.raises(ConnectionError, match="TypeSafe unavailable"):
        predictor.predict("Paid <NUMBER>")

    client.__exit__.assert_called_once()


def test_typesafe_predictor_rejects_response_without_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.__enter__.return_value = client
    client.system_one.return_value = SimpleNamespace(nouls={})
    monkeypatch.setattr(template_classification, "TypeSafeClient", MagicMock(return_value=client))
    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    with pytest.raises(KeyError, match="is_transaction_alert"):
        predictor.predict("Paid <NUMBER>")


def test_classification_failure_preserves_existing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>", is_transaction_alert=True)

    predictor = MagicMock(spec=template_classification.TemplateClassificationPredictor)
    predictor.predict.side_effect = ConnectionError("TypeSafe unavailable")
    predictor_class = MagicMock(return_value=predictor)
    monkeypatch.setattr(
        template_classification,
        "TemplateClassificationPredictor",
        predictor_class,
    )

    with pytest.raises(ConnectionError, match="TypeSafe unavailable"):
        template_classification.classify_template(template.id)

    predictor_class.assert_called_once_with()
    with database_connection():
        assert Template.get_by_id(template.id).is_transaction_alert is True


def test_sanitizer_failure_preserves_template_and_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_text = "Amit Patel paid <NUMBER>"
    with database_connection():
        template = Template.create(text=original_text, is_transaction_alert=True)

    monkeypatch.setenv("JEV_API_KEY", "test-key")
    monkeypatch.setattr(
        template_classification,
        "sanitize_template_text",
        MagicMock(side_effect=PiiSanitizationError("sanitizer unavailable")),
    )
    client_class = MagicMock()
    monkeypatch.setattr(template_classification, "TypeSafeClient", client_class)

    with pytest.raises(PiiSanitizationError, match="sanitizer unavailable"):
        template_classification.classify_template(template.id)

    client_class.assert_not_called()
    with database_connection():
        stored_template = Template.get_by_id(template.id)
        assert stored_template.text == original_text
        assert stored_template.is_transaction_alert is True


@pytest.mark.parametrize("prediction", [True, False, None])
def test_classification_persists_and_returns_detached_result(
    monkeypatch: pytest.MonkeyPatch,
    prediction: bool | None,
) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>", is_transaction_alert=not prediction)

    predictor = MagicMock(spec=template_classification.TemplateClassificationPredictor)
    predictor.predict.return_value = prediction
    predictor_class = MagicMock(return_value=predictor)
    monkeypatch.setattr(
        template_classification,
        "TemplateClassificationPredictor",
        predictor_class,
    )

    result = template_classification.classify_template(template.id)

    assert result == template_classification.TemplateClassificationResult(template.id, prediction)
    predictor_class.assert_called_once_with()
    predictor.predict.assert_called_once_with("Paid <NUMBER>")
    assert database.is_closed()
    with database_connection():
        stored_template = Template.get_by_id(template.id)
        assert stored_template.text == "Paid <NUMBER>"
        assert stored_template.is_transaction_alert is prediction


def test_missing_template_does_not_create_predictor(monkeypatch: pytest.MonkeyPatch) -> None:
    predictor_class = MagicMock()
    monkeypatch.setattr(
        template_classification,
        "TemplateClassificationPredictor",
        predictor_class,
    )

    with pytest.raises(TemplateNotFoundError, match="Template not found"):
        template_classification.classify_template(999)
    predictor_class.assert_not_called()
    assert database.is_closed()
