# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest
from playhouse.migrations import Runner

from aggregator import email_sync
from aggregator.database import (
    DATABASE_PATH,
    PROJECT_ROOT,
    close_database,
    connect_database,
    database,
)
from aggregator.email_pull import EmailMessage


@pytest.fixture(autouse=True)
def in_memory_database() -> Generator[None]:
    close_database()
    database.init(":memory:")  # pyright: ignore[reportUnknownMemberType]
    connect_database()
    try:
        Runner(database, directory=str(PROJECT_ROOT / "migrations")).up()
        yield
    finally:
        close_database()
        database.init(str(DATABASE_PATH))  # pyright: ignore[reportUnknownMemberType]


def _message(message_id: str = "message-1") -> EmailMessage:
    return EmailMessage(
        message_id=message_id,
        history_id="history-1",
        received_at=datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC),
        sender="merchant@example.com",
        subject="Receipt",
        body_text="Plain receipt",
        body_html="<p>HTML receipt</p>",
        headers={
            "from": "merchant@example.com",
            "subject": "Receipt",
            "authentication-results": "spf=pass",
        },
        authentication_status="spf=pass",
    )


def test_sync_stores_all_normalized_email_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _message()
    monkeypatch.setattr(email_sync, "pull_messages", lambda _label, _date: [message])

    result = email_sync.sync_messages("Transactions", date(2024, 1, 1))

    stored = email_sync.Email.get()
    assert result == email_sync.SyncResult(pulled=1, inserted=1, already_stored=0)
    assert stored.message_id == message.message_id
    assert stored.history_id == message.history_id
    assert stored.received_at == message.received_at
    assert stored.sender == message.sender
    assert stored.subject == message.subject
    assert stored.body_text == message.body_text
    assert stored.body_html == message.body_html
    assert stored.headers == dict(message.headers)
    assert stored.authentication_status == message.authentication_status


def test_sync_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    message = _message()
    monkeypatch.setattr(email_sync, "pull_messages", lambda _label, _date: [message])

    email_sync.sync_messages("Transactions", date(2024, 1, 1))
    result = email_sync.sync_messages("Transactions", date(2024, 1, 1))

    assert email_sync.Email.select().count() == 1
    assert result == email_sync.SyncResult(pulled=1, inserted=0, already_stored=1)


def test_sync_persists_multiple_messages_and_counts_batch_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = [_message("message-1"), _message("message-2"), _message("message-1")]
    monkeypatch.setattr(email_sync, "pull_messages", lambda _label, _date: messages)

    result = email_sync.sync_messages("Transactions", date(2024, 1, 1))

    assert email_sync.Email.select().count() == 2
    assert result == email_sync.SyncResult(pulled=3, inserted=2, already_stored=1)


def test_sync_rolls_back_the_entire_batch_when_a_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = [_message("message-1"), _message("message-2")]
    monkeypatch.setattr(email_sync, "pull_messages", lambda _label, _date: messages)
    original_create = email_sync.Email.create
    calls = 0

    def fail_second_create(**values: object) -> email_sync.Email:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("database write failed")
        return original_create(**values)

    monkeypatch.setattr(email_sync.Email, "create", fail_second_create)

    with pytest.raises(RuntimeError, match="database write failed"):
        email_sync.sync_messages("Transactions", date(2024, 1, 1))

    assert email_sync.Email.select().count() == 0
