"""Durable parser generation sessions and review operations."""

# Peewee and LangGraph expose dynamic APIs.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, cast
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver  # pyright: ignore[reportMissingTypeStubs]
from langgraph.types import Command  # pyright: ignore[reportMissingTypeStubs]
from redis import Redis

from . import queries
from .celery_app import REDIS_URL
from .database import database, database_connection
from .field_parsers import (
    FieldParserGenerationError,
    TemplateNotTransactionAlertError,
    approve_field_parsers,
    field_parser_snapshot,
    replace_field_parsers,
    require_field_parsers_approvable,
)
from .models import ParserGenerationSession, Template
from .parser_configuration import FieldParserSet
from .parser_generation import ParserGenerationError
from .parser_generation._inputs import GenerationInput
from .parser_generation._review_graph import build_review_graph, initial_state
from .read_models import ParserSnapshot
from .template_representation import represent_email_template

redis_client: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
    REDIS_URL, decode_responses=True
)


class ParserSessionConflictError(RuntimeError):
    """A parser operation overlaps another job or targets a changed draft."""


class ParserSessionSupersededError(ParserSessionConflictError):
    """A newer parser operation displaced this session."""


@contextmanager
def template_lock(template_id: int) -> Generator[None]:
    lock = redis_client.lock(
        f"aggregator:parser-generation:template:{template_id}",
        timeout=35 * 60,
        blocking_timeout=0,
    )
    if not lock.acquire(blocking=False):
        raise ParserSessionConflictError("Another parser operation is in progress")
    try:
        yield
    finally:
        lock.release()


@contextmanager
def _checkpointer() -> Generator[SqliteSaver]:
    # Resolve the live Peewee path: tests and AGGREGATOR_DATABASE_PATH can rebind it.
    connection = sqlite3.connect(
        str(database.database), timeout=5, check_same_thread=False, isolation_level=None
    )
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        saver = SqliteSaver(connection)
        saver.setup()
        yield saver
    finally:
        connection.close()


def _latest_session(template_id: int) -> ParserGenerationSession | None:
    return (
        ParserGenerationSession.select()
        .where(ParserGenerationSession.template == template_id)
        .order_by(ParserGenerationSession.id.desc())
        .first()
    )


def current_session(template_id: int) -> ParserGenerationSession | None:
    with database_connection():
        session = _latest_session(template_id)
        if session is None or session.status == "superseded":
            return None
        return session


def _fingerprint(parsers: FieldParserSet) -> str:
    payload = parsers.model_dump_json(exclude_none=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _saved_parsers(template: Template) -> FieldParserSet:
    return queries.parser_sets({template.id: template})[template.id]


def _assert_saved_draft(session: ParserGenerationSession, template: Template) -> None:
    if session.template_text != template.text:
        raise ParserSessionSupersededError("Template text changed during parser review")
    if session.published_fingerprint != _fingerprint(_saved_parsers(template)):
        raise ParserSessionSupersededError("The saved parser draft changed during review")


def _snapshot_examples(template: Template) -> list[list[dict[str, object]]]:
    example = queries.example_email(template.id)
    if example is None:
        raise FieldParserGenerationError("Template has no associated email")
    try:
        representation = represent_email_template(template.text, example.body, FieldParserSet())
        parameters: list[dict[str, object]] = [
            {"index": index, "mask_name": parameter.mask_name, "value": parameter.value}
            for index, parameter in enumerate(representation.extracted_parameters)
        ]
        validated = GenerationInput.model_validate(
            {"template_text": template.text, "parameter_examples": [parameters]}
        )
    except ValueError as error:
        raise FieldParserGenerationError("The example email does not match the template") from error
    return [
        [parameter.model_dump() for parameter in group] for group in validated.parameter_examples
    ]


def queue_generation(
    template_id: int,
    feedback: str | None,
    submit: Callable[[int, int, str, str | None], Any],
) -> Any:
    """Reserve a session and job under the shared template lock."""
    feedback = feedback.strip() if feedback else None
    with template_lock(template_id), database_connection():
        # This decision commits independently, even if the new example is invalid or
        # the queue is unavailable. A changed template invalidates the old checkpoint.
        with database.atomic("IMMEDIATE"):
            template = queries.require_template(template_id)
            previous = _latest_session(template_id)
            if previous is not None and previous.template_text != template.text:
                previous.status = "superseded"
                previous.active_job_id = None
                previous.save(
                    only=[ParserGenerationSession.status, ParserGenerationSession.active_job_id]
                )
        with database.atomic():
            template = queries.require_template(template_id)
            if template.is_transaction_alert is not True:
                raise TemplateNotTransactionAlertError(
                    "Template is not classified as a transaction alert"
                )
            previous = _latest_session(template_id)
            if previous is not None and previous.active_job_id is not None:
                raise ParserSessionConflictError("Parser generation is already queued")
            resume = (
                bool(feedback) and previous is not None and previous.status == "awaiting_review"
            )
            if resume:
                session = cast(ParserGenerationSession, previous)
                _assert_saved_draft(session, template)
            else:
                if previous is not None and previous.status != "superseded":
                    previous.status = "superseded"
                    previous.save(only=[ParserGenerationSession.status])
                session = ParserGenerationSession.create(
                    template=template,
                    thread_id=str(uuid4()),
                    status="queued",
                    current_round=1,
                    active_job_id=None,
                    published_fingerprint=None,
                    template_text=template.text,
                    examples_json=json.dumps(_snapshot_examples(template)),
                )
            job_id = str(uuid4())
            session.active_job_id = job_id
            session.status = "queued"
            session.save(
                only=[ParserGenerationSession.active_job_id, ParserGenerationSession.status]
            )
            return submit(template_id, session.id, job_id, feedback)


def _publish(session_id: int, round_number: int, parsers: FieldParserSet) -> None:
    with database_connection(), database.atomic("IMMEDIATE"):
        session = ParserGenerationSession.get_by_id(session_id)
        template = queries.require_template(session.template_id)
        if session.status == "superseded" or session.active_job_id is None:
            raise ParserSessionSupersededError("Parser generation session was superseded")
        if session.template_text != template.text:
            raise ParserSessionSupersededError("Template text changed during generation")
        fingerprint = _fingerprint(parsers)
        if session.current_round == round_number and session.published_fingerprint == fingerprint:
            _assert_saved_draft(session, template)
            return
        if session.published_fingerprint is not None and round_number <= session.current_round:
            raise ParserSessionConflictError("The parser round was already published")
        replace_field_parsers(template.id, parsers)
        session.current_round = round_number
        session.published_fingerprint = fingerprint
        session.status = "awaiting_review"
        session.save(
            only=[
                ParserGenerationSession.current_round,
                ParserGenerationSession.published_fingerprint,
                ParserGenerationSession.status,
            ]
        )


def _approve(session_id: int, round_number: int, parsers: FieldParserSet) -> None:
    with database_connection(), database.atomic("IMMEDIATE"):
        session = ParserGenerationSession.get_by_id(session_id)
        template = queries.require_template(session.template_id)
        if session.status == "approved" and session.published_fingerprint == _fingerprint(parsers):
            return
        if session.status != "awaiting_review" or session.current_round != round_number:
            raise ParserSessionConflictError("Parser review session is no longer current")
        _assert_saved_draft(session, template)
        if session.published_fingerprint != _fingerprint(parsers):
            raise ParserSessionConflictError("The reviewed parser differs from the saved draft")
        approve_field_parsers(template.id)
        session.status = "approved"
        session.save(only=[ParserGenerationSession.status])


def run_generation_job(
    template_id: int, session_id: int, job_id: str, feedback: str | None
) -> ParserSnapshot:
    """Run or replay a generation job through its persisted checkpoint."""
    with template_lock(template_id):
        with database_connection():
            session = ParserGenerationSession.get_by_id(session_id)
            if session.template_id != template_id or session.status == "superseded":
                raise ParserSessionSupersededError("Parser generation session was superseded")
            if session.active_job_id is None and session.status == "awaiting_review":
                return field_parser_snapshot(template_id)
            if session.active_job_id != job_id:
                raise ParserSessionSupersededError("Parser generation job was superseded")
            if session.status == "queued":
                session.status = "running"
                session.save(only=[ParserGenerationSession.status])
            examples = json.loads(session.examples_json)
            template_text = str(session.template_text)
            seed = _saved_parsers(queries.require_template(template_id)) if feedback else None
            thread_id = str(session.thread_id)
            # Queueing resets the status; publication marks this job's draft ready.
            # A retry after publication must not submit the same feedback again.
            draft_published = session.status == "awaiting_review"
        with _checkpointer() as saver:
            from dotenv import load_dotenv

            from .celery_app import DOTENV_PATH

            load_dotenv(dotenv_path=DOTENV_PATH)
            graph = build_review_graph(saver, _publish, _approve)
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = graph.get_state(config)
            if checkpoint.values:
                values = checkpoint.values
                if values.get("status") == "awaiting_review" and checkpoint.next:
                    if feedback is not None and not draft_published:
                        graph.invoke(Command(resume={"feedback": feedback}), config)
                elif checkpoint.next:
                    graph.invoke(None, config)
            else:
                graph.invoke(
                    initial_state(
                        session_id, template_text, examples, feedback=feedback or "", seed=seed
                    ),
                    config,
                )
            state = graph.get_state(config).values
            if state.get("status") == "failed":
                mark_job_failed(session_id, job_id)
                error = state.get("validation_errors", ["invalid parser"])
                raise ParserGenerationError(f"Parser generation failed after 3 attempts: {error}")
            if state.get("status") != "awaiting_review":
                raise FieldParserGenerationError(
                    f"Parser generation stopped in {state.get('status')}"
                )
        with database_connection():
            session = ParserGenerationSession.get_by_id(session_id)
            if session.active_job_id == job_id:
                session.active_job_id = None
                session.save(only=[ParserGenerationSession.active_job_id])
        return field_parser_snapshot(template_id)


def mark_job_failed(session_id: int, job_id: str) -> None:
    with database_connection():
        session = ParserGenerationSession.get_by_id(session_id)
        if session.active_job_id == job_id:
            session.active_job_id = None
            session.status = "failed"
            session.save(
                only=[ParserGenerationSession.active_job_id, ParserGenerationSession.status]
            )


def supersede_job(session_id: int, job_id: str) -> None:
    with database_connection():
        session = ParserGenerationSession.get_by_id(session_id)
        if session.active_job_id == job_id:
            session.active_job_id = None
            session.status = "superseded"
            session.save(
                only=[ParserGenerationSession.active_job_id, ParserGenerationSession.status]
            )


def replace_manual(template_id: int, parsers: FieldParserSet) -> ParserSnapshot:
    with template_lock(template_id), database_connection(), database.atomic():
        session = _latest_session(template_id)
        if session is not None:
            if session.active_job_id is not None:
                raise ParserSessionConflictError("Parser generation is in progress")
            session.status = "superseded"
            session.save(only=[ParserGenerationSession.status])
        return replace_field_parsers(template_id, parsers)


def approve_review(template_id: int) -> ParserSnapshot:
    with template_lock(template_id):
        with database_connection():
            session = current_session(template_id)
            if session is not None and session.active_job_id is not None:
                raise ParserSessionConflictError("Parser generation is in progress")
            if session is None or session.status != "awaiting_review":
                return approve_field_parsers(template_id)
            template = queries.require_template(template_id)
            _assert_saved_draft(session, template)
            require_field_parsers_approvable(template_id)
            thread_id = str(session.thread_id)
        with _checkpointer() as saver:
            graph = build_review_graph(saver, _publish, _approve)
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = graph.get_state(config)
            if checkpoint.next and "human_review" in checkpoint.next:
                graph.invoke(Command(resume={"action": "approve"}), config)
            elif checkpoint.next:
                graph.invoke(None, config)
            elif checkpoint.values.get("status") != "approved":
                raise ParserSessionConflictError("Parser review checkpoint is unavailable")
        return field_parser_snapshot(template_id)
