"""Resolve configured email fields into persisted, typed transactions."""

# Peewee and python-dateutil intentionally expose dynamically typed APIs.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dateutil.parser import ParserError, parse
from peewee import JOIN

from .database import database, database_connection
from .email_content import readable_body
from .models import (
    Email,
    Template,
    Transaction,
    TransactionExtractionStatus,
)
from .queries import parser_sets
from .template_representation import represent_email_template

_AMOUNT_PATTERN = re.compile(
    r"[+-]?(?:"
    r"\d+|"
    r"\d{1,3}(?:,\d{3})+|"
    r"\d{1,2}(?:,\d{2})*,\d{3}"
    r")(?:\.\d+)?"
)
# ``dateutil`` fills omitted year/month/day components from ``default``. Parse
# against two defaults whose components all differ: a complete input produces
# the same date twice, while an incomplete input inherits at least one differing
# component and can therefore be rejected instead of silently inventing a date.
_DATE_DEFAULTS = (datetime(2000, 1, 1), datetime(2001, 2, 2))


@dataclass(frozen=True, slots=True)
class TransactionExtractionResult:
    """Counts produced by one transaction-extraction run."""

    pending: int
    created: int
    skipped: int
    failed_templates: int
    failed_emails: int


def _amount(value: str | None) -> Decimal | None:
    if value is None:
        return None
    normalized = value.strip()
    if _AMOUNT_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"invalid amount {value!r}")
    try:
        amount = Decimal(normalized.replace(",", ""))
    except InvalidOperation as error:  # pragma: no cover - guarded by the expression
        raise ValueError(f"invalid amount {value!r}") from error
    if not amount.is_finite():
        raise ValueError(f"invalid amount {value!r}")
    return amount


def _transaction_date(value: str | None) -> date | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"invalid transaction date {value!r}")
    try:
        parsed_with_defaults = (
            parse(normalized, dayfirst=True, fuzzy=False, default=_DATE_DEFAULTS[0]),
            parse(normalized, dayfirst=True, fuzzy=False, default=_DATE_DEFAULTS[1]),
        )
    except (ParserError, OverflowError, ValueError) as error:
        raise ValueError(f"invalid transaction date {value!r}") from error
    parsed_dates = tuple(parsed.date() for parsed in parsed_with_defaults)
    if parsed_dates[0] != parsed_dates[1]:
        raise ValueError(f"invalid transaction date {value!r}")
    return parsed_dates[0]


def _boolean(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"invalid is_credit value {value!r}")


def _text(value: str | None) -> str | None:
    return value.strip() if value is not None else None


def _transaction_values(fields: dict[str, str | None]) -> dict[str, object]:
    return {
        "amount": _amount(fields["amount"]),
        "currency_code": _text(fields["currency_code"]),
        "payee": _text(fields["payee"]),
        "description": _text(fields["description"]),
        "transaction_date": _transaction_date(fields["transaction_date"]),
        "account_hint": _text(fields["account_hint"]),
        "is_credit": _boolean(fields["is_credit"]),
    }


def _pending_emails() -> list[Email]:
    query = (
        Email.select(Email)
        .join(Transaction, JOIN.LEFT_OUTER, on=(Transaction.email == Email.id))
        .where(Transaction.id.is_null())
        .order_by(Email.template, Email.received_at, Email.id)
    )
    return list(query)


def extract_transactions() -> TransactionExtractionResult:
    """Create typed transactions for every eligible, unprocessed email."""
    with database_connection():
        pending_emails = _pending_emails()
        grouped: dict[int, list[Email]] = {}
        skipped = 0
        for email in pending_emails:
            if email.template_id is None:
                skipped += 1
                continue
            grouped.setdefault(int(email.template_id), []).append(email)

        created = 0
        failed_templates = 0
        failed_emails = 0
        for template_id, emails in grouped.items():
            template = Template.get_by_id(template_id)
            if template.account_id is None:
                skipped += len(emails)
                continue
            if template.transaction_extraction_status == TransactionExtractionStatus.FAILED.value:
                skipped += len(emails)
                continue

            values: list[dict[str, object]] = []
            failure: str | None = None
            email = emails[0]
            try:
                parsers = parser_sets({template_id: template}, complete_only=True).get(template_id)
                if parsers is None:
                    skipped += len(emails)
                    continue
                for email in emails:
                    representation = represent_email_template(
                        template.text, readable_body(email.body_html, email.body_text), parsers
                    )
                    values.append(
                        {
                            "email": email,
                            "account": template.account_id,
                            **_transaction_values(representation.resolved_fields),
                        }
                    )
            except (IndexError, ValueError) as error:
                failure = f"email {email.id}: {error}"

            if failure is not None:
                with database.atomic():
                    Template.update(
                        transaction_extraction_status=TransactionExtractionStatus.FAILED.value,
                        transaction_extraction_error=failure,
                    ).where(Template.id == template.id).execute()
                failed_templates += 1
                failed_emails += len(emails)
                continue

            with database.atomic():
                for transaction_values in values:
                    Transaction.create(**transaction_values)
                Template.update(
                    transaction_extraction_status=TransactionExtractionStatus.SUCCEEDED.value,
                    transaction_extraction_error=None,
                ).where(Template.id == template.id).execute()
            created += len(values)

    return TransactionExtractionResult(
        pending=len(pending_emails),
        created=created,
        skipped=skipped,
        failed_templates=failed_templates,
        failed_emails=failed_emails,
    )
