"""Tests for background-job status serialization."""

from __future__ import annotations

import pytest

from aggregator.api import jobs


class _Result:
    state = "SUPERSEDED"
    name = "aggregator.template_assignment"


def test_superseded_job_has_a_distinct_terminal_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def result(_: str, *, app: object) -> _Result:
        return _Result()

    monkeypatch.setattr(jobs, "AsyncResult", result)

    response = jobs.get_job("old-job")

    assert response.model_dump() == {
        "job_id": "old-job",
        "action": "aggregator.template_assignment",
        "status": "superseded",
        "result": None,
        "error": None,
    }
