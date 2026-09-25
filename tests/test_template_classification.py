from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from playhouse.migrations import Runner
from typesafe_sdk import Noul, NoulAnswer, SystemOneResponse, Usage

from aggregator import background_tasks, template_classification
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


@pytest.fixture(autouse=True)
def stub_langfuse(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    langfuse = MagicMock()
    generation = MagicMock()
    langfuse.start_as_current_observation.return_value.__enter__.return_value = generation
    monkeypatch.setattr(
        template_classification,
        "_langfuse_tracing",
        MagicMock(return_value=langfuse),
    )
    return langfuse


def _typesafe_response(
    probability: float,
    *,
    model: str = "jev-1",
    input_tokens: int | None = 12,
    output_tokens: int | None = 3,
) -> SystemOneResponse:
    return SystemOneResponse(
        model=model,
        usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
        answers={"is_transaction_alert": NoulAnswer(noul=probability)},
    )


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
    client.system_one.return_value = _typesafe_response(probability)
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
    client.system_one.return_value = _typesafe_response(0.8)
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


def test_sanitizer_failure_prevents_client_creation_and_tracing(
    monkeypatch: pytest.MonkeyPatch,
    stub_langfuse: MagicMock,
) -> None:
    sanitizer = MagicMock(side_effect=PiiSanitizationError("sanitizer unavailable"))
    client_class = MagicMock()
    monkeypatch.setattr(template_classification, "sanitize_template_text", sanitizer)
    monkeypatch.setattr(template_classification, "TypeSafeClient", client_class)
    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    with pytest.raises(PiiSanitizationError, match="sanitizer unavailable"):
        predictor.predict("Amit Patel paid <NUMBER>")

    client_class.assert_not_called()
    stub_langfuse.start_as_current_observation.assert_not_called()
    stub_langfuse.flush.assert_not_called()


def test_typesafe_predictor_records_langfuse_generation(
    monkeypatch: pytest.MonkeyPatch,
    stub_langfuse: MagicMock,
) -> None:
    sanitized_text = "<PERSON> paid <NUMBER>"
    monkeypatch.setattr(
        template_classification,
        "sanitize_template_text",
        MagicMock(return_value=sanitized_text),
    )
    response = _typesafe_response(
        0.82,
        model="jev-2026-09-18",
        input_tokens=41,
        output_tokens=7,
    )
    client = MagicMock()
    client.__enter__.return_value = client
    client.system_one.return_value = response
    monkeypatch.setattr(template_classification, "TypeSafeClient", MagicMock(return_value=client))
    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    assert predictor.predict("Amit Patel paid <NUMBER>") is True

    stub_langfuse.start_as_current_observation.assert_called_once_with(
        name="classify-template",
        as_type="generation",
        input={
            "state": {"email_template": sanitized_text},
            "questions": {
                "is_transaction_alert": {
                    "type": "noul",
                    "instructions": (
                        "Is the given email template a bank/wallet/card transaction alert?"
                    ),
                }
            },
        },
    )
    generation = stub_langfuse.start_as_current_observation.return_value.__enter__.return_value
    generation.update.assert_called_once_with(
        output=response.model_dump(mode="json"),
        model="jev-2026-09-18",
        usage_details={"input": 41, "output": 7},
    )
    stub_langfuse.flush.assert_called_once_with()


def test_typesafe_predictor_propagates_service_failure_and_flushes_langfuse(
    monkeypatch: pytest.MonkeyPatch,
    stub_langfuse: MagicMock,
) -> None:
    client = MagicMock()
    client.__enter__.return_value = client
    service_error = ConnectionError("TypeSafe unavailable")
    client.system_one.side_effect = service_error
    monkeypatch.setattr(template_classification, "TypeSafeClient", MagicMock(return_value=client))
    predictor = template_classification.TemplateClassificationPredictor(api_key="test-key")

    with pytest.raises(ConnectionError, match="TypeSafe unavailable") as error:
        predictor.predict("Paid <NUMBER>")

    assert error.value is service_error
    client.__exit__.assert_called_once()
    observation = stub_langfuse.start_as_current_observation.return_value
    assert observation.__exit__.call_args.args[:2] == (ConnectionError, service_error)
    stub_langfuse.flush.assert_called_once_with()


def test_typesafe_predictor_rejects_response_without_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.__enter__.return_value = client
    client.system_one.return_value = SystemOneResponse(
        model="jev-1",
        usage=Usage(input_tokens=8, output_tokens=1),
        answers={},
    )
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


@pytest.mark.parametrize("approval_phase", ["before_prediction", "during_prediction"])
def test_approval_prevents_classifier_write_and_parser_job(
    monkeypatch: pytest.MonkeyPatch, approval_phase: str
) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>", is_transaction_alert=True)
        if approval_phase == "before_prediction":
            template.field_parsers_approved = True
            template.save(only=[Template.field_parsers_approved])

    predictor = MagicMock(spec=template_classification.TemplateClassificationPredictor)

    def predict(_: str) -> bool:
        with database_connection():
            Template.update(field_parsers_approved=True).where(Template.id == template.id).execute()
        return False

    predictor.predict.side_effect = predict
    predictor_class = MagicMock(return_value=predictor)
    monkeypatch.setattr(template_classification, "TemplateClassificationPredictor", predictor_class)
    monkeypatch.setattr(
        background_tasks.generate_field_parsers_task,
        "delay",
        lambda _: pytest.fail("parser was queued"),
    )

    result = background_tasks.classify_template_task.run(template.id)

    assert result == {
        "template_id": template.id,
        "is_transaction_alert": True,
        "parser_generation_job_id": None,
    }
    with database_connection():
        assert Template.get_by_id(template.id).is_transaction_alert is True
    if approval_phase == "before_prediction":
        predictor_class.assert_not_called()
    else:
        predictor.predict.assert_called_once_with("Paid <NUMBER>")
