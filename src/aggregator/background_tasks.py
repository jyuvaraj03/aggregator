"""Celery tasks which adapt application operations to JSON job results."""

# Celery does not publish type stubs.
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUntypedFunctionDecorator=false, reportUnknownVariableType=false

from __future__ import annotations

from datetime import date
from typing import NoReturn
from uuid import uuid4

from celery.exceptions import Ignore

from .celery_app import celery_app
from .email_pull import CredentialsError, InvalidInputError
from .email_sync import sync_messages
from .field_parsers import FieldParserGenerationError, generate_and_replace_field_parsers
from .template_assignment import assign_email_templates
from .template_assignment_queue import (
    TemplateAssignmentSupersededError,
    current_job_guard,
    publish_as_latest,
)
from .template_classification import classify_template
from .transaction_extraction import run_transaction_extraction

_PERMANENT_ERRORS = (
    CredentialsError,
    FieldParserGenerationError,
    InvalidInputError,
    ValueError,
)


def _retryable(
    task: object, error: Exception, *, args: tuple[object, ...] | None = None
) -> NoReturn:
    if isinstance(error, _PERMANENT_ERRORS):
        raise error
    countdown = (5, 30)[min(task.request.retries, 1)]
    if args is None:
        raise task.retry(exc=error, countdown=countdown)
    raise task.retry(exc=error, countdown=countdown, args=args)


@celery_app.task(bind=True, name="aggregator.email_sync", max_retries=2)
def sync_email_task(
    self: object, from_date: str, completed_sync: dict[str, int] | None = None
) -> dict[str, object]:
    try:
        if completed_sync is None:
            result = sync_messages(date.fromisoformat(from_date))
            completed_sync = {
                "pulled": result.pulled,
                "inserted": result.inserted,
                "already_stored": result.already_stored,
            }
        assignment_job = queue_email_template_assignment()
        return {
            **completed_sync,
            "template_assignment_job_id": assignment_job.id,
        }
    except Exception as error:
        retry_args: tuple[object, ...] = (from_date,)
        if completed_sync is not None:
            retry_args = (from_date, completed_sync)
        _retryable(self, error, args=retry_args)


def queue_email_template_assignment() -> object:
    """Queue a template-assignment job which supersedes its predecessors."""
    job_id = str(uuid4())
    return publish_as_latest(
        job_id,
        lambda: assign_email_templates_task.apply_async(args=(job_id,), task_id=job_id),
    )


def _mark_superseded(task: object) -> NoReturn:
    task.update_state(state="SUPERSEDED")
    raise Ignore()


@celery_app.task(bind=True, name="aggregator.template_assignment", max_retries=2)
def assign_email_templates_task(
    self: object,
    job_id: str,
    completed_assignment: dict[str, object] | None = None,
    template_classification_jobs: list[dict[str, object]] | None = None,
    outstanding_template_ids: list[int] | None = None,
) -> dict[str, object]:
    retry_args: tuple[object, ...] = (job_id,)
    try:
        if completed_assignment is None:
            with current_job_guard(job_id):
                pass
            result = assign_email_templates(commit_guard=lambda: current_job_guard(job_id))
            completed_assignment = {
                "processed": result.processed,
                "skipped": result.skipped,
                "templates_created": result.templates_created,
                "created_template_ids": list(result.created_template_ids),
            }
            template_classification_jobs = []
            outstanding_template_ids = list(result.created_template_ids)

        completed_jobs = list(template_classification_jobs or [])
        outstanding_ids = list(outstanding_template_ids or [])
        while outstanding_ids:
            template_id = outstanding_ids[0]
            retry_args = (job_id, completed_assignment, completed_jobs, outstanding_ids)
            classification_job = classify_template_task.delay(template_id)
            completed_jobs.append({"template_id": template_id, "job_id": classification_job.id})
            outstanding_ids.pop(0)

        return {
            **completed_assignment,
            "template_classification_jobs": completed_jobs,
        }
    except TemplateAssignmentSupersededError:
        _mark_superseded(self)
    except Exception as error:
        _retryable(self, error, args=retry_args)


@celery_app.task(bind=True, name="aggregator.template_classification", max_retries=2)
def classify_template_task(
    self: object,
    template_id: int,
    completed_classification: dict[str, object] | None = None,
) -> dict[str, object]:
    retry_args: tuple[object, ...] = (template_id,)
    try:
        if completed_classification is None:
            result = classify_template(template_id)
            completed_classification = {
                "template_id": result.template_id,
                "is_transaction_alert": result.is_transaction_alert,
            }

        parser_generation_job_id: str | None = None
        if completed_classification["is_transaction_alert"] is True:
            retry_args = (template_id, completed_classification)
            parser_job = generate_field_parsers_task.delay(template_id)
            parser_generation_job_id = parser_job.id

        return {
            **completed_classification,
            "parser_generation_job_id": parser_generation_job_id,
        }
    except Exception as error:
        _retryable(self, error, args=retry_args)


@celery_app.task(bind=True, name="aggregator.field_parser_generation", max_retries=2)
def generate_field_parsers_task(self: object, template_id: int) -> dict[str, object]:
    try:
        snapshot = generate_and_replace_field_parsers(template_id)
        return {
            "template_id": snapshot.template_id,
            "text": snapshot.text,
            "transaction_extraction_status": snapshot.transaction_extraction_status,
            "transaction_extraction_error": snapshot.transaction_extraction_error,
            "field_parser_status": snapshot.field_parser_status,
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


@celery_app.task(bind=True, name="aggregator.transaction_extraction", max_retries=2)
def extract_transactions_task(self: object) -> dict[str, int]:
    try:
        result = run_transaction_extraction()
        return {
            "pending": result.pending,
            "created": result.created,
            "skipped": result.skipped,
            "failed_templates": result.failed_templates,
            "failed_emails": result.failed_emails,
        }
    except Exception as error:
        _retryable(self, error)
