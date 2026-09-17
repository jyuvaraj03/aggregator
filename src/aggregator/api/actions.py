"""Synchronous import and template-mining routes."""

# Celery task proxies are untyped.
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from ..background_tasks import (
    extract_transactions_task,
    queue_email_template_assignment,
    sync_email_task,
)
from .schemas import (
    BackgroundJobResponse,
    EmailSyncRequest,
)

router = APIRouter(tags=["actions"])


def _submitted(task: object, response: Response) -> BackgroundJobResponse:
    try:
        job = task.delay()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Background queue is unavailable") from error
    status_url = f"/jobs/{job.id}"
    response.status_code = status.HTTP_202_ACCEPTED
    response.headers["Location"] = status_url
    return BackgroundJobResponse(job_id=job.id, status_url=status_url)


@router.post(
    "/email-sync", response_model=BackgroundJobResponse, status_code=status.HTTP_202_ACCEPTED
)
def sync_email(request: EmailSyncRequest, response: Response) -> BackgroundJobResponse:
    try:
        job = sync_email_task.delay(request.from_date.isoformat())
    except Exception as error:
        raise HTTPException(status_code=503, detail="Background queue is unavailable") from error
    status_url = f"/jobs/{job.id}"
    response.headers["Location"] = status_url
    return BackgroundJobResponse(job_id=job.id, status_url=status_url)


@router.post(
    "/email-template-assignment",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def assign_email_templates_action(response: Response) -> BackgroundJobResponse:
    try:
        job = queue_email_template_assignment()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Background queue is unavailable") from error
    status_url = f"/jobs/{job.id}"
    response.headers["Location"] = status_url
    return BackgroundJobResponse(job_id=job.id, status_url=status_url)


@router.post(
    "/transaction-extraction",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def extract_transactions_action(response: Response) -> BackgroundJobResponse:
    return _submitted(extract_transactions_task, response)
