"""Request and response schemas for the HTTP API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class EmailSummary(BaseModel):
    id: int
    message_id: str
    received_at: datetime
    sender: str
    subject: str | None
    template_id: int | None


class EmailDetail(EmailSummary):
    body: str


class TemplateResponse(BaseModel):
    id: int
    text: str
    email_count: int


class EmailPage(BaseModel):
    items: list[EmailSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class TemplatePage(BaseModel):
    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EmailSyncRequest(BaseModel):
    label: str = Field(min_length=1)
    from_date: date


class SyncResponse(BaseModel):
    pulled: int
    inserted: int
    already_stored: int


class MiningResponse(BaseModel):
    processed: int
    skipped: int
    templates_created: int
