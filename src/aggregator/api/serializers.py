"""Pure conversions from prepared application results to HTTP schemas."""

from __future__ import annotations

from ..read_models import EmailRecord, ParserSnapshot, TemplateRecord, TransactionRecord
from ..template_representation import TemplateRepresentation
from .parameter_serialization import indexed_parameter_responses
from .schemas import (
    EmailDetail,
    EmailDetailRepresentationResponse,
    EmailRepresentationResponse,
    EmailSummary,
    ResolvedTransactionFields,
    TemplateEmailExample,
    TemplateFieldParsersResponse,
    TemplateResponse,
    TransactionResponse,
)


def email_representation(
    representation: TemplateRepresentation | None,
) -> EmailRepresentationResponse | None:
    if representation is None:
        return None
    return EmailRepresentationResponse(
        template_text=representation.template_text,
        resolved_fields=ResolvedTransactionFields.model_validate(representation.resolved_fields),
    )


def email_summary(email: EmailRecord) -> EmailSummary:
    return EmailSummary(
        id=email.id,
        message_id=email.message_id,
        received_at=email.received_at,
        sender=email.sender,
        subject=email.subject,
        template_id=email.template_id,
        representation=email_representation(email.representation),
    )


def email_detail(email: EmailRecord) -> EmailDetail:
    representation = email.representation
    detail_representation = (
        EmailDetailRepresentationResponse(
            template_text=representation.template_text,
            extracted_parameters=indexed_parameter_responses(
                (parameter.mask_name, parameter.value)
                for parameter in representation.extracted_parameters
            ),
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
        body=email.body,
        representation=detail_representation,
    )


def template_email_example(email: EmailRecord) -> TemplateEmailExample:
    """Serialize a template example without exposing email representations."""
    return TemplateEmailExample(
        id=email.id,
        message_id=email.message_id,
        received_at=email.received_at,
        sender=email.sender,
        subject=email.subject,
        template_id=email.template_id,
        body=email.body,
    )


def template_response(template: TemplateRecord) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        text=template.text,
        email_count=template.email_count,
        account_id=template.account_id,
    )


def transaction_response(transaction: TransactionRecord) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        email_id=transaction.email_id,
        account_id=transaction.account_id,
        amount=transaction.amount,
        currency_code=transaction.currency_code,
        payee=transaction.payee,
        description=transaction.description,
        transaction_date=transaction.transaction_date,
        account_hint=transaction.account_hint,
        is_credit=transaction.is_credit,
        representation=email_representation(transaction.representation),
    )


def parser_snapshot_response(snapshot: ParserSnapshot) -> TemplateFieldParsersResponse:
    return TemplateFieldParsersResponse(
        template_id=snapshot.template_id,
        text=snapshot.text,
        transaction_extraction_status=snapshot.transaction_extraction_status,
        transaction_extraction_error=snapshot.transaction_extraction_error,
        example_email_id=snapshot.example_email_id,
        parameters=indexed_parameter_responses(snapshot.parameters),
        parsers=snapshot.parsers,
        preview=(
            ResolvedTransactionFields.model_validate(snapshot.preview)
            if snapshot.preview is not None
            else None
        ),
    )
