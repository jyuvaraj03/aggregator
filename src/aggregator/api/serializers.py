"""Explicit, safe conversions from ORM models to API schemas."""

# Peewee model primary-key descriptors are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from ..models import Email, Template
from .schemas import EmailDetail, EmailSummary, TemplateResponse


def email_summary(email: Email) -> EmailSummary:
    return EmailSummary(
        id=email.id,
        message_id=email.message_id,
        received_at=email.received_at,
        sender=email.sender,
        subject=email.subject,
        template_id=email.template_id,
    )


def email_detail(email: Email) -> EmailDetail:
    summary = email_summary(email)
    body = email.readable_body() or (email.body_text or "")
    return EmailDetail(**summary.model_dump(), body=body)


def template_response(template: Template) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        text=template.text,
        email_count=int(getattr(template, "email_count", 0)),
    )
