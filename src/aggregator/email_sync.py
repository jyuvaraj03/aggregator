"""Persist normalized Gmail messages in the shared SQLite database."""

# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportUnknownMemberType=false
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .database import database, database_connection
from .email_pull import EmailMessage, pull_messages
from .models import Email


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Counts from one Gmail-to-SQLite synchronization."""

    pulled: int
    inserted: int
    already_stored: int


def sync_messages(from_date: date | datetime) -> SyncResult:
    """Pull and persist Gmail messages, leaving existing snapshots untouched.

    The complete batch is written in one transaction.  A message ID found either
    in the database or earlier in this batch is counted as already stored.
    """
    messages = pull_messages(from_date)

    with database_connection():
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

    return SyncResult(pulled=len(messages), inserted=inserted, already_stored=already_stored)


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
        "received_at": message.received_at,
        "sender": message.sender,
        "subject": message.subject,
        "body": message.body,
    }
