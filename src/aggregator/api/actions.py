"""Synchronous import and template-mining routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..email_sync import sync_messages
from ..template_assignment import assign_email_templates
from .schemas import EmailSyncRequest, SyncResponse, TemplateAssignmentResponse

router = APIRouter(tags=["actions"])


@router.post("/email-sync", response_model=SyncResponse)
def sync_email(request: EmailSyncRequest) -> SyncResponse:
    result = sync_messages(request.label, request.from_date)
    return SyncResponse(
        pulled=result.pulled,
        inserted=result.inserted,
        already_stored=result.already_stored,
    )


@router.post("/email-template-assignment", response_model=TemplateAssignmentResponse)
def assign_email_templates_action() -> TemplateAssignmentResponse:
    result = assign_email_templates()
    return TemplateAssignmentResponse(
        processed=result.processed,
        skipped=result.skipped,
        templates_created=result.templates_created,
    )
