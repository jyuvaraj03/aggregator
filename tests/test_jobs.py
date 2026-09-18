"""Tests for background-job status serialization."""

from __future__ import annotations

import pytest

from aggregator.api import jobs


class _Result:
    def __init__(self, state: str, name: str) -> None:
        self.state = state
        self.name = name
        self.result: object | None = None


def test_superseded_job_has_a_distinct_terminal_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def result(_: str, *, app: object) -> _Result:
        return _Result("SUPERSEDED", "aggregator.template_assignment")

    monkeypatch.setattr(jobs, "AsyncResult", result)

    response = jobs.get_job("old-job")

    assert response.model_dump() == {
        "job_id": "old-job",
        "action": "aggregator.template_assignment",
        "status": "superseded",
        "result": None,
        "error": None,
    }


def test_parser_failure_is_reported_as_its_own_job(monkeypatch: pytest.MonkeyPatch) -> None:
    def result(_: str, *, app: object) -> _Result:
        return _Result("FAILURE", "aggregator.field_parser_generation")

    monkeypatch.setattr(jobs, "AsyncResult", result)

    response = jobs.get_job("parser-job")

    assert response.model_dump() == {
        "job_id": "parser-job",
        "action": "aggregator.field_parser_generation",
        "status": "failed",
        "result": None,
        "error": "Job failed",
    }
