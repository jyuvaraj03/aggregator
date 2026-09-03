"""Synchronous import and template-mining routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..email_sync import sync_messages
from ..template_mining import mine_untagged_templates
from .schemas import EmailSyncRequest, MiningResponse, SyncResponse

router = APIRouter(tags=["actions"])


@router.post("/email-sync", response_model=SyncResponse)
def sync_email(request: EmailSyncRequest) -> SyncResponse:
    result = sync_messages(request.label, request.from_date)
    return SyncResponse(
        pulled=result.pulled,
        inserted=result.inserted,
        already_stored=result.already_stored,
    )


@router.post("/email-template-mining", response_model=MiningResponse)
def mine_email_templates() -> MiningResponse:
    result = mine_untagged_templates()
    return MiningResponse(
        processed=result.processed,
        skipped=result.skipped,
        templates_created=result.templates_created,
    )
