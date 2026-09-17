"""Tests for Celery task adapters without requiring a Redis server."""

# Celery task proxies are untyped.
# pyright: reportFunctionMemberAccess=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false

from contextlib import contextmanager
from datetime import date
from typing import Any

import pytest
from celery.exceptions import Ignore

from aggregator import background_tasks
from aggregator.email_sync import SyncResult
from aggregator.template_assignment import TemplateAssignmentResult
from aggregator.transaction_extraction import TransactionExtractionResult


def test_sync_task_serializes_operation_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def sync(from_date: date) -> SyncResult:
        captured.update(from_date=from_date)
        return SyncResult(pulled=3, inserted=2, already_stored=1)

    monkeypatch.setattr(background_tasks, "sync_messages", sync)

    assert background_tasks.sync_email_task.run("2026-09-01") == {
        "pulled": 3,
        "inserted": 2,
        "already_stored": 1,
    }
    assert captured == {"from_date": date(2026, 9, 1)}


def test_other_tasks_serialize_operation_results(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def current_job(_: str) -> Any:
        yield

    monkeypatch.setattr(
        background_tasks,
        "assign_email_templates",
        lambda **_: TemplateAssignmentResult(processed=4, skipped=1, templates_created=2),
    )
    monkeypatch.setattr(background_tasks, "current_job_guard", current_job)
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
    }
    assert background_tasks.extract_transactions_task.run() == {
        "pending": 8,
        "created": 4,
        "skipped": 1,
        "failed_templates": 1,
        "failed_emails": 2,
    }


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
