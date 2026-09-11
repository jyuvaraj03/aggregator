"""Tests for Celery task adapters without requiring a Redis server."""

# Celery task proxies are untyped.
# pyright: reportFunctionMemberAccess=false

from datetime import date

import pytest

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
    monkeypatch.setattr(
        background_tasks,
        "assign_email_templates",
        lambda: TemplateAssignmentResult(processed=4, skipped=1, templates_created=2),
    )
    monkeypatch.setattr(
        background_tasks,
        "extract_transactions",
        lambda: TransactionExtractionResult(
            pending=8, created=4, skipped=1, failed_templates=1, failed_emails=2
        ),
    )

    assert background_tasks.assign_email_templates_task.run() == {
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
