"""Request and response schemas for the HTTP API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from ..parser_configuration import FieldParserSet


class ResolvedTransactionFields(BaseModel):
    amount: str | None = None
    currency_code: str | None = None
    payee: str | None = None
    description: str | None = None
    transaction_date: str | None = None
    account_hint: str | None = None
    is_credit: str | None = None


class IndexedParameterResponse(BaseModel):
    index: int
    mask_name: str
    value: str | None


class TemplateFieldParsersResponse(BaseModel):
    template_id: int
    text: str
    transaction_extraction_status: Literal["pending", "succeeded", "failed"]
    transaction_extraction_error: str | None
    example_email_id: int | None
    parameters: list[IndexedParameterResponse]
    parsers: FieldParserSet
    preview: ResolvedTransactionFields | None


class EmailRepresentationResponse(BaseModel):
    template_text: str
    resolved_fields: ResolvedTransactionFields


class EmailDetailRepresentationResponse(BaseModel):
    template_text: str
    extracted_parameters: list[IndexedParameterResponse]
    resolved_fields: ResolvedTransactionFields


class EmailSummary(BaseModel):
    id: int
    message_id: str
    received_at: datetime
    sender: str
    subject: str | None
    template_id: int | None
    representation: EmailRepresentationResponse | None


class EmailDetail(BaseModel):
    id: int
    message_id: str
    received_at: datetime
    sender: str
    subject: str | None
    template_id: int | None
    body: str
    representation: EmailDetailRepresentationResponse | None


class TemplateEmailExample(BaseModel):
    id: int
    message_id: str
    received_at: datetime
    sender: str
    subject: str | None
    template_id: int | None
    body: str


class TemplateResponse(BaseModel):
    id: int
    text: str
    email_count: int
    account_id: int | None


class TemplateAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: StrictInt | None


class TemplateDetailResponse(TemplateResponse):
    example: TemplateEmailExample | None


class EmailPage(BaseModel):
    items: list[EmailSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionResponse(BaseModel):
    id: int
    email_id: int
    account_id: int | None
    amount: Decimal | None
    currency_code: str | None
    payee: str | None
    description: str | None
    transaction_date: date | None
    account_hint: str | None
    is_credit: bool | None
    representation: EmailRepresentationResponse | None


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AccountCreate(BaseModel):
    name: str


class AccountUpdate(BaseModel):
    name: str


class AccountResponse(BaseModel):
    id: int
    name: str


class AccountPage(BaseModel):
    items: list[AccountResponse]
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


class TemplateAssignmentResponse(BaseModel):
    processed: int
    skipped: int
    templates_created: int


class TransactionExtractionResponse(BaseModel):
    pending: int
    created: int
    skipped: int
    failed_templates: int
    failed_emails: int
