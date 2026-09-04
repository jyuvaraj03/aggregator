"""Explicit, safe conversions from ORM models to API schemas."""

# Peewee model primary-key descriptors are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from decimal import Decimal
from typing import cast

from ..models import Email, Template, Transaction
from .schemas import (
    EmailDetail,
    EmailDetailRepresentationResponse,
    EmailRepresentationResponse,
    EmailSummary,
    ExtractedParameterResponse,
    ResolvedTransactionFields,
    TemplateEmailExample,
    TemplateResponse,
    TransactionResponse,
)


def email_representation(email: Email) -> EmailRepresentationResponse | None:
    representation = email.representation()
    if representation is None:
        return None
    return EmailRepresentationResponse(
        template_text=representation.template_text,
        resolved_fields=ResolvedTransactionFields.model_validate(representation.resolved_fields),
    )


def email_summary(email: Email) -> EmailSummary:
    return EmailSummary(
        id=email.id,
        message_id=email.message_id,
        received_at=email.received_at,
        sender=email.sender,
        subject=email.subject,
        template_id=email.template_id,
        representation=email_representation(email),
    )


def email_detail(email: Email) -> EmailDetail:
    body = email.readable_body() or (email.body_text or "")
    representation = email.representation()
    detail_representation = (
        EmailDetailRepresentationResponse(
            template_text=representation.template_text,
            extracted_parameters=[
                ExtractedParameterResponse(value=parameter.value, mask_name=parameter.mask_name)
                for parameter in representation.extracted_parameters
            ],
            resolved_fields=ResolvedTransactionFields.model_validate(
                representation.resolved_fields
            ),
        )
        if representation is not None
        else None
    )
    return EmailDetail(
        id=email.id,
        message_id=email.message_id,
        received_at=email.received_at,
        sender=email.sender,
        subject=email.subject,
        template_id=email.template_id,
        body=body,
        representation=detail_representation,
    )


def template_email_example(email: Email) -> TemplateEmailExample:
    """Serialize a template example without exposing email representations."""
    body = email.readable_body() or (email.body_text or "")
    return TemplateEmailExample(
        id=email.id,
        message_id=email.message_id,
        received_at=email.received_at,
        sender=email.sender,
        subject=email.subject,
        template_id=email.template_id,
        body=body,
    )


def template_response(template: Template) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        text=template.text,
        email_count=int(getattr(template, "email_count", 0)),
    )


def transaction_response(transaction: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        email_id=transaction.email_id,
        amount=cast(Decimal | None, transaction.amount),
        currency_code=transaction.currency_code,
        payee=transaction.payee,
        description=transaction.description,
        transaction_date=transaction.transaction_date,
        account_hint=transaction.account_hint,
        is_credit=transaction.is_credit,
        representation=email_representation(transaction.email),
    )
