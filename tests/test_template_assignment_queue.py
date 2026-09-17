"""Tests for latest-wins template-assignment queue coordination."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from aggregator import template_assignment_queue

_LATEST_JOB_KEY = "aggregator:template-assignment:latest-job"


def _redis(previous_job_id: str | None) -> Mock:
    client = Mock()
    client.get.return_value = previous_job_id
    lock = client.lock.return_value
    lock.acquire.return_value = True
    return client


def test_publish_as_latest_sets_marker_before_publishing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _redis("old-job")
    monkeypatch.setattr(template_assignment_queue, "redis_client", client)

    def publish() -> str:
        client.set.assert_called_once_with(_LATEST_JOB_KEY, "new-job")
        return "queued"

    assert template_assignment_queue.publish_as_latest("new-job", publish) == "queued"
    client.lock.return_value.release.assert_called_once_with()


@pytest.mark.parametrize("previous_job_id", [None, "old-job"])
def test_publish_failure_restores_previous_marker(
    monkeypatch: pytest.MonkeyPatch, previous_job_id: str | None
) -> None:
    client = _redis(previous_job_id)
    monkeypatch.setattr(template_assignment_queue, "redis_client", client)

    def fail() -> None:
        raise RuntimeError("broker unavailable")

    with pytest.raises(RuntimeError, match="broker unavailable"):
        template_assignment_queue.publish_as_latest("new-job", fail)

    if previous_job_id is None:
        client.delete.assert_called_once_with(_LATEST_JOB_KEY)
    else:
        assert client.set.call_args_list[-1].args == (
            _LATEST_JOB_KEY,
            previous_job_id,
        )


def test_current_job_guard_rejects_a_stale_job(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _redis("new-job")
    monkeypatch.setattr(template_assignment_queue, "redis_client", client)

    with pytest.raises(template_assignment_queue.TemplateAssignmentSupersededError):
        with template_assignment_queue.current_job_guard("old-job"):
            pytest.fail("stale job entered guarded operation")
