"""Coordinate latest-wins template-assignment jobs through Redis."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import cast

from redis import Redis

from .celery_app import REDIS_URL

_LATEST_JOB_KEY = "aggregator:template-assignment:latest-job"
_COORDINATION_LOCK_KEY = "aggregator:template-assignment:coordination-lock"
_LOCK_TIMEOUT_SECONDS = 35 * 60
_LOCK_BLOCKING_TIMEOUT_SECONDS = 5


class TemplateAssignmentQueueUnavailableError(RuntimeError):
    """The latest-job marker could not be coordinated safely."""


class TemplateAssignmentSupersededError(RuntimeError):
    """A newer template-assignment job displaced this job."""


redis_client: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
    REDIS_URL, decode_responses=True
)


@contextmanager
def _coordination_lock() -> Generator[None]:
    lock = redis_client.lock(
        _COORDINATION_LOCK_KEY,
        timeout=_LOCK_TIMEOUT_SECONDS,
        blocking_timeout=_LOCK_BLOCKING_TIMEOUT_SECONDS,
    )
    if not lock.acquire():
        raise TemplateAssignmentQueueUnavailableError(
            "Template-assignment queue coordination timed out"
        )
    try:
        yield
    finally:
        lock.release()


def publish_as_latest[Result](job_id: str, publish: Callable[[], Result]) -> Result:
    """Publish a job while atomically replacing the latest-job marker."""
    with _coordination_lock():
        previous_job_id = cast(str | None, redis_client.get(_LATEST_JOB_KEY))
        redis_client.set(_LATEST_JOB_KEY, job_id)
        try:
            return publish()
        except Exception:
            if previous_job_id is None:
                redis_client.delete(_LATEST_JOB_KEY)
            else:
                redis_client.set(_LATEST_JOB_KEY, previous_job_id)
            raise


@contextmanager
def current_job_guard(job_id: str) -> Generator[None]:
    """Hold coordination through a current-job check and guarded operation."""
    with _coordination_lock():
        latest_job_id = cast(str | None, redis_client.get(_LATEST_JOB_KEY))
        if latest_job_id != job_id:
            raise TemplateAssignmentSupersededError(job_id)
        yield
