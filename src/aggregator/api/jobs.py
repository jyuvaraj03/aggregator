"""Read Celery task state without exposing Celery internals to API clients."""

# Celery does not publish type stubs.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Literal, cast

from celery.result import AsyncResult
from fastapi import APIRouter

from ..celery_app import celery_app
from .schemas import BackgroundJobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

_STATUSES = {
    "PENDING": "queued",
    "STARTED": "running",
    "RETRY": "retrying",
    "SUCCESS": "succeeded",
    "FAILURE": "failed",
}


@router.get("/{job_id}", response_model=BackgroundJobStatusResponse)
def get_job(job_id: str) -> BackgroundJobStatusResponse:
    result = AsyncResult(job_id, app=celery_app)
    status = cast(
        Literal["queued", "running", "retrying", "succeeded", "failed"],
        _STATUSES.get(result.state, "failed"),
    )
    action = result.name or "unknown"
    if status == "succeeded":
        payload = result.result
        payload = payload if isinstance(payload, dict) else None
        return BackgroundJobStatusResponse(
            job_id=job_id, action=action, status=status, result=payload
        )
    if status == "failed":
        return BackgroundJobStatusResponse(
            job_id=job_id, action=action, status=status, error="Job failed"
        )
    return BackgroundJobStatusResponse(job_id=job_id, action=action, status=status)
