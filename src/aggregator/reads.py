"""Application read operations that prepare results before releasing their connection."""

from collections.abc import Collection
from dataclasses import replace
from decimal import Decimal
from typing import cast

from . import queries
from .database import database_connection
from .models import Email, Template
from .parser_configuration import field_parser_status
from .read_models import EmailRecord, Page, TemplateRecord, TransactionRecord
from .template_representation import represent_email_template


def _email_record(email: Email) -> EmailRecord:
    return EmailRecord(
        id=email.id,
        message_id=email.message_id,
        received_at=email.received_at,
        sender=email.sender,
        subject=email.subject,
        template_id=email.template_id,
        body=email.body,
    )


def _represented_emails(emails: list[Email]) -> dict[int, EmailRecord]:
    records = {record.id: record for record in map(_email_record, emails)}
    template_ids = {
        record.template_id for record in records.values() if record.template_id is not None
    }
    templates = queries.templates_by_ids(template_ids)
    parsers = queries.parser_sets(templates)
    for email_id, record in records.items():
        if record.template_id is not None:
            template = templates[record.template_id]
            records[email_id] = replace(
                record,
                representation=represent_email_template(
                    template.text, record.body, parsers[record.template_id]
                ),
            )
    return records


def email_page(
    page: int, template_filter: queries.EmailTemplateFilter | None = None
) -> Page[EmailRecord]:
    with database_connection():
        if template_filter is not None and template_filter.template_id is not None:
            queries.require_template(template_filter.template_id)
        result = queries.email_page(page, template_filter)
        records = _represented_emails(result.items)
        return Page(list(records.values()), result.total)


def email_by_id(email_id: int) -> EmailRecord | None:
    with database_connection():
        email = queries.email_by_id(email_id)
        return _represented_emails([email])[email_id] if email is not None else None


def transaction_page(page: int) -> Page[TransactionRecord]:
    with database_connection():
        result = queries.transaction_page(page)
        records = _represented_emails([transaction.email for transaction in result.items])
        return Page(
            [
                TransactionRecord(
                    id=transaction.id,
                    email_id=transaction.email_id,
                    account_id=transaction.account_id,
                    amount=cast(Decimal | None, transaction.amount),
                    currency_code=transaction.currency_code,
                    payee=transaction.payee,
                    description=transaction.description,
                    transaction_date=transaction.transaction_date,
                    account_hint=transaction.account_hint,
                    is_credit=transaction.is_credit,
                    representation=records[transaction.email_id].representation,
                )
                for transaction in result.items
            ],
            result.total,
        )


def _template_record(template: Template) -> TemplateRecord:
    return TemplateRecord(
        id=template.id,
        text=template.text,
        is_transaction_alert=template.is_transaction_alert,
        email_count=int(vars(template)["email_count"]),
        account_id=template.account_id,
        field_parser_status=field_parser_status(
            is_transaction_alert=template.is_transaction_alert,
            approved=bool(template.field_parsers_approved),
            configured_count=int(vars(template)["field_parser_count"]),
        ),
    )


def template_page(
    page: int, classifications: Collection[bool | None] | None = None
) -> Page[TemplateRecord]:
    with database_connection():
        result = queries.template_page(page, classifications)
        return Page([_template_record(template) for template in result.items], result.total)


def template_by_id(template_id: int) -> TemplateRecord | None:
    with database_connection():
        template = queries.template_by_id(template_id)
        if template is None:
            return None
        example = queries.example_email(template_id)
        return replace(
            _template_record(template),
            example=_email_record(example) if example is not None else None,
        )
