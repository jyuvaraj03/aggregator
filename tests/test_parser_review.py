from __future__ import annotations

# Peewee and migration helpers expose dynamic query methods.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportPrivateUsage=false
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.exceptions import OutputParserException
from playhouse.migrations import Runner

from aggregator import background_tasks, parser_review
from aggregator.database import DATABASE_PATH, PROJECT_ROOT, close_database, database
from aggregator.field_parsers import InvalidParserPreviewError
from aggregator.models import Email, FieldParser, ParserGenerationSession, Template
from aggregator.parser_configuration import FieldParserSet
from aggregator.parser_generation import _workflow
from aggregator.parser_generation._schemas import GeneratedFieldParsers


@pytest.fixture
def review_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    close_database()
    database.init(str(tmp_path / "review.sqlite3"))  # pyright: ignore[reportUnknownMemberType]
    database.connect()
    Runner(database, directory=str(PROJECT_ROOT / "migrations")).up()

    @contextmanager
    def unlocked(_: int) -> Generator[None]:
        yield

    monkeypatch.setattr(parser_review, "template_lock", unlocked)
    try:
        yield
    finally:
        close_database()
        database.init(str(DATABASE_PATH))  # pyright: ignore[reportUnknownMemberType]


def _parser(payee: str) -> GeneratedFieldParsers:
    return GeneratedFieldParsers.model_validate(
        {
            "amount": {"rule": "extracted", "parameter_indices": [0]},
            "currency_code": {"rule": "missing"},
            "payee": {"rule": "constant", "constant_value": payee},
            "description": {"rule": "missing"},
            "transaction_date": {"rule": "missing"},
            "account_hint": {"rule": "missing"},
            "is_credit": {"rule": "constant", "constant_value": "false"},
        }
    )


def _template() -> Template:
    template = Template.create(text="Paid <NUMBER>", is_transaction_alert=True)
    Email.create(
        message_id="example",
        received_at=datetime.now(UTC),
        sender="bank@example.com",
        body="Paid 19",
        template=template,
    )
    return template


def _submit(template_id: int, session_id: int, job_id: str, feedback: str | None) -> Any:
    return SimpleNamespace(id=job_id, args=(template_id, session_id, job_id, feedback))


def test_feedback_resumes_from_sqlite_checkpoint_and_approval(
    review_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = _template()
    replies = iter([_parser("First Shop"), _parser("Correct Shop")])
    requests: list[list[Any]] = []

    class FakeModel:
        def invoke(self, messages: list[Any]) -> GeneratedFieldParsers:
            requests.append(messages)
            return next(replies)

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())

    first_job = parser_review.queue_generation(template.id, None, _submit)
    first = parser_review.run_generation_job(*first_job.args)
    assert first.parsers.payee is not None
    assert first.parsers.payee.constant_value == "First Shop"  # type: ignore[union-attr]
    assert first.session_round == 1
    assert first.session_status == "awaiting_review"

    close_database()
    database.connect()
    feedback_job = parser_review.queue_generation(template.id, " Use the right shop ", _submit)
    second = parser_review.run_generation_job(*feedback_job.args)
    assert second.parsers.payee is not None
    assert second.parsers.payee.constant_value == "Correct Shop"  # type: ignore[union-attr]
    assert second.session_id == first.session_id
    assert second.session_round == 2
    assert len(requests) == 2
    assert "Use the right shop" in str(requests[1][-1].content)

    approved = parser_review.approve_review(template.id)
    assert approved.field_parser_status == "approved"
    assert approved.session_status == "approved"
    assert ParserGenerationSession.get_by_id(approved.session_id).active_job_id is None


def test_validation_retries_and_failed_feedback_preserve_approved_parser(
    review_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = _template()
    invalid = GeneratedFieldParsers.model_validate(
        {
            **_parser("Bad Shop").model_dump(),
            "amount": {"rule": "constant", "constant_value": "not an amount"},
        }
    )
    replies = iter([_parser("Saved Shop"), invalid, invalid, invalid])

    class FakeModel:
        def invoke(self, _: list[Any]) -> GeneratedFieldParsers:
            return next(replies)

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())
    first_job = parser_review.queue_generation(template.id, None, _submit)
    parser_review.run_generation_job(*first_job.args)
    parser_review.approve_review(template.id)
    assert Template.get_by_id(template.id).field_parsers_approved is True

    feedback_job = parser_review.queue_generation(template.id, "Use a different amount", _submit)
    with pytest.raises(ValueError, match="after 3 attempts"):
        parser_review.run_generation_job(*feedback_job.args)

    snapshot = parser_review.field_parser_snapshot(template.id)
    assert snapshot.parsers.payee == _parser("Saved Shop").payee
    assert snapshot.field_parser_status == "approved"
    assert snapshot.session_status == "failed"
    assert ParserGenerationSession.get_by_id(snapshot.session_id).active_job_id is None

    next_job = parser_review.queue_generation(template.id, "Try another correction", _submit)
    assert next_job.args[1] != feedback_job.args[1]


def test_publication_replay_and_duplicate_task_keep_one_draft(
    review_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = _template()
    calls = 0

    class FakeModel:
        def invoke(self, _: list[Any]) -> GeneratedFieldParsers:
            nonlocal calls
            calls += 1
            return _parser("Draft Shop")

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())
    original_publish = parser_review._publish
    injected = False

    def publish_then_fail(session_id: int, round_number: int, parsers: FieldParserSet) -> None:
        nonlocal injected
        original_publish(session_id, round_number, parsers)
        if not injected:
            injected = True
            raise ConnectionError("checkpoint write interrupted")

    monkeypatch.setattr(parser_review, "_publish", publish_then_fail)
    job = parser_review.queue_generation(template.id, None, _submit)
    with pytest.raises(ConnectionError, match="checkpoint"):
        parser_review.run_generation_job(*job.args)
    assert FieldParser.select().where(FieldParser.template == template).count() == 7

    snapshot = parser_review.run_generation_job(*job.args)
    duplicate = parser_review.run_generation_job(*job.args)
    assert snapshot.session_id == duplicate.session_id
    assert snapshot.session_status == "awaiting_review"
    assert calls == 1
    assert FieldParser.select().where(FieldParser.template == template).count() == 7


@pytest.mark.parametrize("interruption", ["before_resume", "after_publish", "after_checkpoint"])
def test_feedback_retry_applies_correction_once(
    review_database: None, monkeypatch: pytest.MonkeyPatch, interruption: str
) -> None:
    template = _template()
    calls = 0

    class FakeModel:
        def invoke(self, _: list[Any]) -> GeneratedFieldParsers:
            nonlocal calls
            calls += 1
            return _parser(f"Shop {calls}")

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())
    first_job = parser_review.queue_generation(template.id, None, _submit)
    parser_review.run_generation_job(*first_job.args)
    feedback_job = parser_review.queue_generation(template.id, "Fix the payee", _submit)
    original_checkpointer = parser_review._checkpointer
    original_publish = parser_review._publish

    @contextmanager
    def interrupted_checkpointer() -> Generator[Any]:
        if interruption == "before_resume":
            raise ConnectionError("worker interrupted")
        with original_checkpointer() as saver:
            yield saver
        if interruption == "after_checkpoint":
            raise ConnectionError("worker interrupted")

    def interrupted_publish(session_id: int, round_number: int, parsers: FieldParserSet) -> None:
        original_publish(session_id, round_number, parsers)
        if interruption == "after_publish":
            raise ConnectionError("worker interrupted")

    with monkeypatch.context() as interrupted:
        interrupted.setattr(parser_review, "_checkpointer", interrupted_checkpointer)
        interrupted.setattr(parser_review, "_publish", interrupted_publish)
        with pytest.raises(ConnectionError, match="worker interrupted"):
            parser_review.run_generation_job(*feedback_job.args)

    assert ParserGenerationSession.get_by_id(feedback_job.args[1]).active_job_id == feedback_job.id
    close_database()
    snapshot = parser_review.run_generation_job(*feedback_job.args)
    duplicate = parser_review.run_generation_job(*feedback_job.args)

    assert snapshot.session_round == duplicate.session_round == 2
    assert snapshot.session_status == "awaiting_review"
    assert snapshot.parsers.payee == duplicate.parsers.payee == _parser("Shop 2").payee
    assert calls == 2
    assert ParserGenerationSession.get_by_id(feedback_job.args[1]).active_job_id is None
    assert parser_review.approve_review(template.id).session_status == "approved"


def test_malformed_output_and_invalid_transaction_share_attempt_limit(
    review_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = _template()
    invalid = GeneratedFieldParsers.model_validate(
        {
            **_parser("Wrong").model_dump(),
            "amount": {"rule": "constant", "constant_value": "not an amount"},
        }
    )
    responses: list[GeneratedFieldParsers | Exception] = [
        OutputParserException("malformed JSON", llm_output="{broken"),
        invalid,
        _parser("Correct"),
    ]
    requests: list[list[Any]] = []

    class FakeModel:
        def invoke(self, messages: list[Any]) -> GeneratedFieldParsers:
            requests.append(messages)
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())
    job = parser_review.queue_generation(template.id, None, _submit)
    snapshot = parser_review.run_generation_job(*job.args)
    assert snapshot.parsers.payee == _parser("Correct").payee
    assert len(requests) == 3
    assert any("{broken" in str(message.content) for message in requests[1])
    assert "invalid amount" in str(requests[2][-1].content)


def test_manual_save_and_changed_template_supersede_review(
    review_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = _template()
    requests: list[list[Any]] = []

    class FakeModel:
        def invoke(self, messages: list[Any]) -> GeneratedFieldParsers:
            requests.append(messages)
            return _parser("Generated")

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())
    first_job = parser_review.queue_generation(template.id, None, _submit)
    parser_review.run_generation_job(*first_job.args)
    manual_snapshot = parser_review.replace_manual(
        template.id, FieldParserSet.model_validate(_parser("Manual").model_dump())
    )
    assert manual_snapshot.session_id is None
    assert ParserGenerationSession.get_by_id(first_job.args[1]).status == "superseded"
    feedback_job = parser_review.queue_generation(template.id, "Fix the payee", _submit)
    assert feedback_job.args[1] != first_job.args[1]
    parser_review.run_generation_job(*feedback_job.args)
    assert "Manual" in str(requests[-1][-1].content)

    template.text = "Paid <NUMBER> today"
    template.save()
    email = Email.get(Email.template == template)
    email.body = "Paid 19 today"
    email.save()
    fresh_job = parser_review.queue_generation(template.id, None, _submit)
    assert fresh_job.args[1] != feedback_job.args[1]
    assert ParserGenerationSession.get_by_id(feedback_job.args[1]).status == "superseded"


def test_queued_job_blocks_overlap_and_failed_submission_rolls_back(review_database: None) -> None:
    template = _template()
    job = parser_review.queue_generation(template.id, None, _submit)
    parsers = FieldParserSet.model_validate(_parser("Manual").model_dump())
    with pytest.raises(parser_review.ParserSessionConflictError):
        parser_review.queue_generation(template.id, "Fix amount", _submit)
    with pytest.raises(parser_review.ParserSessionConflictError):
        parser_review.replace_manual(template.id, parsers)
    with pytest.raises(parser_review.ParserSessionConflictError):
        parser_review.approve_review(template.id)
    assert ParserGenerationSession.get_by_id(job.args[1]).active_job_id == job.id

    parser_review.mark_job_failed(job.args[1], job.id)

    def unavailable(*_: object) -> Any:
        raise ConnectionError("broker unavailable")

    with pytest.raises(ConnectionError, match="broker"):
        parser_review.queue_generation(template.id, None, unavailable)
    assert ParserGenerationSession.select().count() == 1
    assert ParserGenerationSession.get_by_id(job.args[1]).status == "failed"


def test_failed_approval_keeps_review_interrupt_for_feedback(
    review_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = Template.create(text="Paid <*>", is_transaction_alert=True)
    email = Email.create(
        message_id="wildcard",
        received_at=datetime.now(UTC),
        sender="bank@example.com",
        body="Paid 19",
        template=template,
    )
    replies = iter([_parser("First"), _parser("Second")])

    class FakeModel:
        def invoke(self, _: list[Any]) -> GeneratedFieldParsers:
            return next(replies)

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())
    job = parser_review.queue_generation(template.id, None, _submit)
    parser_review.run_generation_job(*job.args)
    email.body = "Paid nonsense"
    email.save()
    with pytest.raises(InvalidParserPreviewError):
        parser_review.approve_review(template.id)
    assert parser_review.field_parser_snapshot(template.id).session_status == "awaiting_review"

    email.body = "Paid 19"
    email.save()
    feedback_job = parser_review.queue_generation(template.id, "Use another payee", _submit)
    corrected = parser_review.run_generation_job(*feedback_job.args)
    assert corrected.parsers.payee == _parser("Second").payee
    assert corrected.session_round == 2


def test_generation_job_result_reports_session_and_revokes_approval(
    review_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = _template()
    parser_review.replace_manual(
        template.id, FieldParserSet.model_validate(_parser("Manual").model_dump())
    )
    parser_review.approve_review(template.id)
    assert Template.get_by_id(template.id).field_parsers_approved is True

    class FakeModel:
        def invoke(self, _: list[Any]) -> GeneratedFieldParsers:
            return _parser("Generated")

    monkeypatch.setattr(_workflow, "_structured_model", lambda _: FakeModel())
    job = parser_review.queue_generation(template.id, None, _submit)
    result = background_tasks.generate_field_parsers_task.run(*job.args)  # pyright: ignore[reportFunctionMemberAccess]
    assert result["session_id"] == job.args[1]
    assert result["session_round"] == 1
    assert result["session_status"] == "awaiting_review"
    assert Template.get_by_id(template.id).field_parsers_approved is False


def test_changed_template_invalidates_queued_session_even_when_example_is_stale(
    review_database: None,
) -> None:
    template = _template()
    old_job = parser_review.queue_generation(template.id, None, _submit)
    template.text = "Paid <NUMBER> today"
    template.save()

    with pytest.raises(parser_review.FieldParserGenerationError, match="does not match"):
        parser_review.queue_generation(template.id, None, _submit)

    old_session = ParserGenerationSession.get_by_id(old_job.args[1])
    assert old_session.status == "superseded"
    assert old_session.active_job_id is None
