"""Persist normalized Gmail messages in the shared SQLite database."""

# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime

from peewee import CharField, DateTimeField, Model, TextField

from .database import database, database_connection
from .email_pull import EmailMessage, pull_messages


class JSONTextField(TextField):
    """Store JSON in SQLite while exposing it as a dictionary in Python."""

    def db_value(self, value: object) -> str:
        return json.dumps(value)

    def python_value(self, value: object) -> dict[str, str]:
        if isinstance(value, str):
            decoded = json.loads(value)
            if isinstance(decoded, dict):
                return {str(key): str(item) for key, item in decoded.items()}
        return {}


class Email(Model):
    """An immutable snapshot of a Gmail message imported by the synchronizer."""

    message_id = CharField(unique=True)
    history_id = CharField(null=True)
    received_at = DateTimeField()
    sender = TextField()
    subject = TextField(null=True)
    body_text = TextField(null=True)
    body_html = TextField(null=True)
    headers = JSONTextField()
    authentication_status = TextField(null=True)

    class Meta:
        database = database
        table_name = "emails"


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Counts from one Gmail-to-SQLite synchronization."""

    pulled: int
    inserted: int
    already_stored: int


def sync_messages(label: str, from_date: date | datetime) -> SyncResult:
    """Pull and persist Gmail messages, leaving existing snapshots untouched.

    The complete batch is written in one transaction.  A message ID found either
    in the database or earlier in this batch is counted as already stored.
    """
    messages = pull_messages(label, from_date)

    with database_connection():
        database.create_tables([Email], safe=True)
        with database.atomic():
            stored_ids = _existing_message_ids(messages)
            inserted = 0
            already_stored = 0
            for message in messages:
                if message.message_id in stored_ids:
                    already_stored += 1
                    continue
                Email.create(**_email_values(message))
                stored_ids.add(message.message_id)
                inserted += 1

    return SyncResult(
        pulled=len(messages), inserted=inserted, already_stored=already_stored
    )


def _existing_message_ids(messages: list[EmailMessage]) -> set[str]:
    message_ids = {message.message_id for message in messages}
    if not message_ids:
        return set()
    return {
        email.message_id
        for email in Email.select(Email.message_id).where(Email.message_id.in_(message_ids))
    }


def _email_values(message: EmailMessage) -> dict[str, object]:
    return {
        "message_id": message.message_id,
        "history_id": message.history_id,
        "received_at": message.received_at,
        "sender": message.sender,
        "subject": message.subject,
        "body_text": message.body_text,
        "body_html": message.body_html,
        "headers": dict(message.headers),
        "authentication_status": message.authentication_status,
    }
