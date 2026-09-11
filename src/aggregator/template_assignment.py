"""Persistence operation for assigning mined patterns to untagged emails."""

# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from dataclasses import dataclass

from .database import database, database_connection
from .email_content import readable_body
from .models import Email, Template
from .template_mining import MinedPattern, MiningRecord, bulk_mine_templates


@dataclass(frozen=True, slots=True)
class TemplateAssignmentResult:
    """Counts produced while assigning mined patterns to untagged emails."""

    processed: int
    skipped: int
    templates_created: int


def assign_email_templates() -> TemplateAssignmentResult:
    """Assign mined templates to emails that do not yet have one."""
    with database_connection():
        emails = list(
            Email.select().where(Email.template.is_null()).order_by(Email.received_at, Email.id)
        )
        mining_records = (
            MiningRecord(
                record_id=email.id,
                text=readable_body(email.body_html, email.body_text),
            )
            for email in emails
        )
        existing_templates_texts = (
            template.text for template in Template.select().order_by(Template.id)
        )
        result = bulk_mine_templates(
            mining_records,
            existing_templates_texts,
        )
        templates_created = _store_and_assign(result.patterns)

    return TemplateAssignmentResult(
        processed=result.processed,
        skipped=len(result.skipped_record_ids),
        templates_created=templates_created,
    )


def _store_and_assign(patterns: tuple[MinedPattern, ...]) -> int:
    """Persist all template creations and bulk assignments in one transaction."""
    templates_created = 0
    with database.atomic():
        for pattern in patterns:
            template, created = Template.get_or_create(text=pattern.text)
            templates_created += int(created)
            Email.update(template=template).where(Email.id.in_(pattern.record_ids)).execute()
    return templates_created
