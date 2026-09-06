"""Detached application results, independent of HTTP and persistence."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from .parser_configuration import FieldParserSet
from .template_representation import TemplateRepresentation


@dataclass(frozen=True, slots=True)
class Page[Item]:
    items: list[Item]
    total: int


@dataclass(frozen=True, slots=True)
class AccountRecord:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class EmailRecord:
    id: int
    message_id: str
    received_at: datetime
    sender: str
    subject: str | None
    template_id: int | None
    body: str
    representation: TemplateRepresentation | None = None


@dataclass(frozen=True, slots=True)
class TemplateRecord:
    id: int
    text: str
    email_count: int
    example: EmailRecord | None = None


@dataclass(frozen=True, slots=True)
class TransactionRecord:
    id: int
    email_id: int
    amount: Decimal | None
    currency_code: str | None
    payee: str | None
    description: str | None
    transaction_date: date | None
    account_hint: str | None
    is_credit: bool | None
    representation: TemplateRepresentation | None


@dataclass(frozen=True, slots=True)
class ParserSnapshot:
    template_id: int
    text: str
    transaction_extraction_status: Literal["pending", "succeeded", "failed"]
    transaction_extraction_error: str | None
    example_email_id: int | None
    parameters: tuple[tuple[str, str | None], ...]
    parsers: FieldParserSet
    preview: dict[str, str | None] | None
