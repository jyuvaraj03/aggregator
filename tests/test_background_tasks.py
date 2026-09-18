"""Tests for Celery task adapters without requiring a Redis server."""

# Celery task proxies are untyped.
# pyright: reportFunctionMemberAccess=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false

from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from typing import Any, cast

import pytest
from celery.exceptions import Ignore, Retry

from aggregator import background_tasks
from aggregator.email_pull import CredentialsError
from aggregator.email_sync import SyncResult
from aggregator.template_assignment import TemplateAssignmentResult
from aggregator.transaction_extraction import TransactionExtractionResult


def test_sync_task_serializes_operation_result(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[object] = []

    def sync(from_date: date) -> SyncResult:
        events.append(("sync", from_date))
        return SyncResult(pulled=3, inserted=2, already_stored=1)

    monkeypatch.setattr(background_tasks, "sync_messages", sync)
    monkeypatch.setattr(
        background_tasks,
        "queue_email_template_assignment",
        lambda: events.append("queue assignment") or SimpleNamespace(id="assignment-job"),
    )

    assert background_tasks.sync_email_task.run("2026-09-01") == {
        "pulled": 3,
        "inserted": 2,
        "already_stored": 1,
        "template_assignment_job_id": "assignment-job",
    }
    assert events == [("sync", date(2026, 9, 1)), "queue assignment"]


def test_zero_insert_sync_still_queues_template_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        background_tasks,
        "sync_messages",
        lambda _: SyncResult(pulled=3, inserted=0, already_stored=3),
    )
    queued: list[bool] = []
    monkeypatch.setattr(
        background_tasks,
        "queue_email_template_assignment",
        lambda: queued.append(True) or SimpleNamespace(id="assignment-job"),
    )

    result = background_tasks.sync_email_task.run("2026-09-01")

    assert result["template_assignment_job_id"] == "assignment-job"
    assert queued == [True]


def test_sync_failure_does_not_queue_template_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_sync(_: date) -> SyncResult:
        raise CredentialsError("credentials unavailable")

    monkeypatch.setattr(background_tasks, "sync_messages", fail_sync)
    monkeypatch.setattr(
        background_tasks,
        "queue_email_template_assignment",
        lambda: pytest.fail("assignment was queued"),
    )

    with pytest.raises(CredentialsError, match="credentials unavailable"):
        background_tasks.sync_email_task.run("2026-09-01")


def test_sync_submission_retry_keeps_completed_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_calls = 0
    queue_calls = 0
    retry_args: tuple[object, ...] | None = None

    def sync(_: date) -> SyncResult:
        nonlocal sync_calls
        sync_calls += 1
        return SyncResult(pulled=2, inserted=1, already_stored=1)

    def queue() -> object:
        nonlocal queue_calls
        queue_calls += 1
        if queue_calls == 1:
            raise RuntimeError("broker unavailable")
        return SimpleNamespace(id="assignment-job")

    def retry(**options: object) -> Retry:
        nonlocal retry_args
        retry_args = cast(tuple[object, ...], options["args"])
        return Retry()

    monkeypatch.setattr(background_tasks, "sync_messages", sync)
    monkeypatch.setattr(background_tasks, "queue_email_template_assignment", queue)
    monkeypatch.setattr(background_tasks.sync_email_task, "retry", retry)

    with pytest.raises(Retry):
        background_tasks.sync_email_task.run("2026-09-01")
    assert retry_args is not None
    assert background_tasks.sync_email_task.run(*retry_args) == {
        "pulled": 2,
        "inserted": 1,
        "already_stored": 1,
        "template_assignment_job_id": "assignment-job",
    }
    assert sync_calls == 1


def test_other_tasks_serialize_operation_results(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def current_job(_: str) -> Any:
        yield

    monkeypatch.setattr(
        background_tasks,
        "assign_email_templates",
        lambda **_: TemplateAssignmentResult(
            processed=4,
            skipped=1,
            templates_created=2,
            created_template_ids=(10, 20),
        ),
    )
    monkeypatch.setattr(background_tasks, "current_job_guard", current_job)
    monkeypatch.setattr(
        background_tasks.classify_template_task,
        "delay",
        lambda template_id: SimpleNamespace(id=f"classification-{template_id}"),
    )
    monkeypatch.setattr(
        background_tasks,
        "run_transaction_extraction",
        lambda: TransactionExtractionResult(
            pending=8, created=4, skipped=1, failed_templates=1, failed_emails=2
        ),
    )

    assert background_tasks.assign_email_templates_task.run("job-1") == {
        "processed": 4,
        "skipped": 1,
        "templates_created": 2,
        "created_template_ids": [10, 20],
        "template_classification_jobs": [
            {"template_id": 10, "job_id": "classification-10"},
            {"template_id": 20, "job_id": "classification-20"},
        ],
    }
    assert background_tasks.extract_transactions_task.run() == {
        "pending": 8,
        "created": 4,
        "skipped": 1,
        "failed_templates": 1,
        "failed_emails": 2,
    }


def test_template_assignment_with_no_created_templates_queues_no_classifications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def current_job(_: str) -> Any:
        yield

    monkeypatch.setattr(background_tasks, "current_job_guard", current_job)
    monkeypatch.setattr(
        background_tasks,
        "assign_email_templates",
        lambda **_: TemplateAssignmentResult(
            processed=2,
            skipped=0,
            templates_created=0,
            created_template_ids=(),
        ),
    )
    monkeypatch.setattr(
        background_tasks.classify_template_task,
        "delay",
        lambda _: pytest.fail("classification was queued"),
    )

    assert background_tasks.assign_email_templates_task.run("job-1") == {
        "processed": 2,
        "skipped": 0,
        "templates_created": 0,
        "created_template_ids": [],
        "template_classification_jobs": [],
    }


def test_classification_submission_retry_keeps_mining_result_and_completed_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assignment_calls = 0
    submissions: list[int] = []
    retry_args: tuple[object, ...] | None = None

    @contextmanager
    def current_job(_: str) -> Any:
        yield

    def assign(**_: object) -> TemplateAssignmentResult:
        nonlocal assignment_calls
        assignment_calls += 1
        return TemplateAssignmentResult(
            processed=5,
            skipped=1,
            templates_created=3,
            created_template_ids=(10, 20, 30),
        )

    def submit(template_id: int) -> object:
        submissions.append(template_id)
        if submissions == [10, 20]:
            raise RuntimeError("broker unavailable")
        return SimpleNamespace(id=f"classification-{template_id}")

    def retry(**options: object) -> Retry:
        nonlocal retry_args
        retry_args = cast(tuple[object, ...], options["args"])
        return Retry()

    monkeypatch.setattr(background_tasks, "current_job_guard", current_job)
    monkeypatch.setattr(background_tasks, "assign_email_templates", assign)
    monkeypatch.setattr(background_tasks.classify_template_task, "delay", submit)
    monkeypatch.setattr(background_tasks.assign_email_templates_task, "retry", retry)

    with pytest.raises(Retry):
        background_tasks.assign_email_templates_task.run("job-1")
    assert retry_args is not None

    monkeypatch.setattr(
        background_tasks,
        "current_job_guard",
        lambda _: pytest.fail("latest-wins check repeated after commit"),
    )
    result = background_tasks.assign_email_templates_task.run(*retry_args)

    assert assignment_calls == 1
    assert submissions == [10, 20, 20, 30]
    assert result == {
        "processed": 5,
        "skipped": 1,
        "templates_created": 3,
        "created_template_ids": [10, 20, 30],
        "template_classification_jobs": [
            {"template_id": 10, "job_id": "classification-10"},
            {"template_id": 20, "job_id": "classification-20"},
            {"template_id": 30, "job_id": "classification-30"},
        ],
    }


@pytest.mark.parametrize("classification", [False, None])
def test_classification_task_does_not_queue_parser_for_ineligible_result(
    monkeypatch: pytest.MonkeyPatch, classification: bool | None
) -> None:
    from aggregator.template_classification import TemplateClassificationResult

    monkeypatch.setattr(
        background_tasks,
        "classify_template",
        lambda template_id: TemplateClassificationResult(template_id, classification),
    )
    monkeypatch.setattr(
        background_tasks.generate_field_parsers_task,
        "delay",
        lambda _: pytest.fail("parser was queued"),
    )

    assert background_tasks.classify_template_task.run(12) == {
        "template_id": 12,
        "is_transaction_alert": classification,
        "parser_generation_job_id": None,
    }


def test_classification_task_queues_parser_for_transaction_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aggregator.template_classification import TemplateClassificationResult

    monkeypatch.setattr(
        background_tasks,
        "classify_template",
        lambda template_id: TemplateClassificationResult(template_id, True),
    )
    monkeypatch.setattr(
        background_tasks.generate_field_parsers_task,
        "delay",
        lambda template_id: SimpleNamespace(id=f"parser-{template_id}"),
    )

    assert background_tasks.classify_template_task.run(12) == {
        "template_id": 12,
        "is_transaction_alert": True,
        "parser_generation_job_id": "parser-12",
    }


def test_parser_submission_retry_keeps_completed_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aggregator.template_classification import TemplateClassificationResult

    classification_calls = 0
    submissions = 0
    retry_args: tuple[object, ...] | None = None

    def classify(template_id: int) -> TemplateClassificationResult:
        nonlocal classification_calls
        classification_calls += 1
        return TemplateClassificationResult(template_id, True)

    def submit(_: int) -> object:
        nonlocal submissions
        submissions += 1
        if submissions == 1:
            raise RuntimeError("broker unavailable")
        return SimpleNamespace(id="parser-12")

    def retry(**options: object) -> Retry:
        nonlocal retry_args
        retry_args = cast(tuple[object, ...], options["args"])
        return Retry()

    monkeypatch.setattr(background_tasks, "classify_template", classify)
    monkeypatch.setattr(background_tasks.generate_field_parsers_task, "delay", submit)
    monkeypatch.setattr(background_tasks.classify_template_task, "retry", retry)

    with pytest.raises(Retry):
        background_tasks.classify_template_task.run(12)
    assert retry_args is not None
    assert background_tasks.classify_template_task.run(*retry_args) == {
        "template_id": 12,
        "is_transaction_alert": True,
        "parser_generation_job_id": "parser-12",
    }
    assert classification_calls == 1


def test_template_assignment_queue_uses_one_id_for_marker_and_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    queued = object()

    def publish_as_latest(job_id: str, publish: Any) -> object:
        captured["marker_job_id"] = job_id
        return publish()

    def apply_async(*, args: tuple[str], task_id: str) -> object:
        captured.update(args=args, task_id=task_id)
        return queued

    monkeypatch.setattr(background_tasks, "uuid4", lambda: "job-1")
    monkeypatch.setattr(background_tasks, "publish_as_latest", publish_as_latest)
    monkeypatch.setattr(background_tasks.assign_email_templates_task, "apply_async", apply_async)

    assert background_tasks.queue_email_template_assignment() is queued
    assert captured == {
        "marker_job_id": "job-1",
        "args": ("job-1",),
        "task_id": "job-1",
    }


def test_template_assignment_task_is_superseded_before_mining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def superseded(_: str) -> Any:
        raise background_tasks.TemplateAssignmentSupersededError
        yield

    states: list[str] = []
    monkeypatch.setattr(background_tasks, "current_job_guard", superseded)
    monkeypatch.setattr(
        background_tasks, "assign_email_templates", lambda **_: pytest.fail("mining started")
    )
    monkeypatch.setattr(
        background_tasks.assign_email_templates_task,
        "update_state",
        lambda *, state: states.append(state),
    )

    with pytest.raises(Ignore):
        background_tasks.assign_email_templates_task.run("old-job")

    assert states == ["SUPERSEDED"]


def test_template_assignment_task_is_superseded_before_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = 0

    @contextmanager
    def current_then_superseded(_: str) -> Any:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise background_tasks.TemplateAssignmentSupersededError
        yield

    def assign(*, commit_guard: Any) -> TemplateAssignmentResult:
        with commit_guard():
            pytest.fail("commit started")
        raise AssertionError("unreachable")

    states: list[str] = []
    monkeypatch.setattr(background_tasks, "current_job_guard", current_then_superseded)
    monkeypatch.setattr(background_tasks, "assign_email_templates", assign)
    monkeypatch.setattr(
        background_tasks.assign_email_templates_task,
        "update_state",
        lambda *, state: states.append(state),
    )

    with pytest.raises(Ignore):
        background_tasks.assign_email_templates_task.run("old-job")

    assert checks == 2
    assert states == ["SUPERSEDED"]
