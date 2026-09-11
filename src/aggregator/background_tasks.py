"""Celery tasks which adapt application operations to JSON job results."""

# Celery does not publish type stubs.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUntypedFunctionDecorator=false, reportUnknownVariableType=false

from __future__ import annotations

from datetime import date

from .celery_app import celery_app
from .email_pull import ConfigurationError, CredentialsError, InvalidInputError
from .email_sync import sync_messages
from .field_parsers import FieldParserGenerationError, generate_and_replace_field_parsers
from .template_assignment import assign_email_templates
from .transaction_extraction import extract_transactions

_PERMANENT_ERRORS = (
    ConfigurationError,
    CredentialsError,
    FieldParserGenerationError,
    InvalidInputError,
    ValueError,
)


def _retryable(task: object, error: Exception) -> None:
    if isinstance(error, _PERMANENT_ERRORS):
        raise error
    raise task.retry(exc=error, countdown=(5, 30)[min(task.request.retries, 1)])


@celery_app.task(bind=True, name="aggregator.email_sync", max_retries=2)
def sync_email_task(self: object, from_date: str) -> dict[str, int]:
    try:
        result = sync_messages(date.fromisoformat(from_date))
        return {
            "pulled": result.pulled,
            "inserted": result.inserted,
            "already_stored": result.already_stored,
        }
    except Exception as error:
        _retryable(self, error)
        raise AssertionError("unreachable") from error


@celery_app.task(bind=True, name="aggregator.template_assignment", max_retries=2)
def assign_email_templates_task(self: object) -> dict[str, int]:
    try:
        result = assign_email_templates()
        return {
            "processed": result.processed,
            "skipped": result.skipped,
            "templates_created": result.templates_created,
        }
    except Exception as error:
        _retryable(self, error)
        raise AssertionError("unreachable") from error


@celery_app.task(bind=True, name="aggregator.field_parser_generation", max_retries=2)
def generate_field_parsers_task(self: object, template_id: int) -> dict[str, object]:
    try:
        snapshot = generate_and_replace_field_parsers(template_id)
        return {
            "template_id": snapshot.template_id,
            "text": snapshot.text,
            "transaction_extraction_status": snapshot.transaction_extraction_status,
            "transaction_extraction_error": snapshot.transaction_extraction_error,
            "example_email_id": snapshot.example_email_id,
            "parameters": [
                {"index": index, "mask_name": mask, "value": value}
                for index, (mask, value) in enumerate(snapshot.parameters)
            ],
            "parsers": snapshot.parsers.model_dump(mode="json"),
            "preview": snapshot.preview,
        }
    except Exception as error:
        _retryable(self, error)
        raise AssertionError("unreachable") from error


@celery_app.task(bind=True, name="aggregator.transaction_extraction", max_retries=2)
def extract_transactions_task(self: object) -> dict[str, int]:
    try:
        result = extract_transactions()
        return {
            "pending": result.pending,
            "created": result.created,
            "skipped": result.skipped,
            "failed_templates": result.failed_templates,
            "failed_emails": result.failed_emails,
        }
    except Exception as error:
        _retryable(self, error)
        raise AssertionError("unreachable") from error
