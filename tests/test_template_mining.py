# Drain3 and Peewee's model query methods are intentionally dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from playhouse.migrations import Runner

from aggregator.database import (
    DATABASE_PATH,
    PROJECT_ROOT,
    close_database,
    connect_database,
    database,
)
from aggregator.models import Email, Template
from aggregator.template_mining import TemplateMiningResult, mine_templates


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


def _email(message_id: str, body_html: str) -> Email:
    return Email.create(
        message_id=message_id,
        received_at=datetime(2026, 9, 1, tzinfo=UTC),
        sender="merchant@example.com",
        body_html=body_html,
        headers={},
    )


def test_mine_templates_persists_final_pattern_and_tags_matching_emails() -> None:
    first = _email("one", "<p>Order #100 confirmed for $7.20</p>")
    second = _email("two", "<p>Order #101 confirmed for $8.10</p>")

    result = mine_templates([first, second])

    first = Email.get_by_id(first.id)
    second = Email.get_by_id(second.id)
    template = Template.get()
    assert result == TemplateMiningResult(processed=2, skipped=0, templates_created=1)
    assert template.text == "Order <*> confirmed for <*>"
    assert first.template_id == template.id
    assert second.template_id == template.id


def test_mine_templates_uses_readable_html_and_skips_empty_bodies() -> None:
    receipt = _email("receipt", "<h1>Receipt</h1><p>Total 5</p>")
    empty = _email("empty", "<div> </div>")

    result = mine_templates([receipt, empty])

    template = Template.get()
    assert result == TemplateMiningResult(processed=1, skipped=1, templates_created=1)
    assert template.text == "Receipt Total 5"
    assert Email.get_by_id(receipt.id).template_id == template.id
    assert Email.get_by_id(empty.id).template_id is None


def test_mine_templates_creates_separate_templates_for_distinct_bodies() -> None:
    first = _email("one", "<p>Payment received</p>")
    second = _email("two", "<p>Password reset requested</p>")

    mine_templates([first, second])

    assert Template.select().count() == 2
    assert Email.get_by_id(first.id).template_id != Email.get_by_id(second.id).template_id


def test_mine_templates_rolls_back_template_writes_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _email("one", "<p>Payment received</p>")
    second = _email("two", "<p>Password reset requested</p>")
    original_create = Template.create
    calls = 0

    def fail_second_create(**values: object) -> Template:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("template write failed")
        return original_create(**values)

    monkeypatch.setattr(Template, "create", fail_second_create)

    with pytest.raises(RuntimeError, match="template write failed"):
        mine_templates([first, second])

    assert Template.select().count() == 0
    assert Email.get_by_id(first.id).template_id is None
    assert Email.get_by_id(second.id).template_id is None
