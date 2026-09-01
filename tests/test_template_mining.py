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
    third = _email("three", "<p>Order #102 confirmed for $9.00</p>")

    result = mine_templates([first, second, third])

    first = Email.get_by_id(first.id)
    second = Email.get_by_id(second.id)
    third = Email.get_by_id(third.id)
    template = Template.get()
    assert result == TemplateMiningResult(processed=3, skipped=0, templates_created=1)
    assert template.text == "Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>"
    assert first.template_id == template.id
    assert second.template_id == template.id
    assert third.template_id == template.id


def test_mine_templates_uses_readable_html_and_skips_empty_bodies() -> None:
    receipt = _email("receipt", "<h1>Receipt</h1><p>Total 5</p>")
    empty = _email("empty", "<div> </div>")

    result = mine_templates([receipt, empty])

    assert result == TemplateMiningResult(processed=1, skipped=1, templates_created=0)
    assert Template.select().count() == 0
    assert Email.get_by_id(receipt.id).template_id is None
    assert Email.get_by_id(empty.id).template_id is None


def test_mine_templates_masks_dates_currency_and_numbers() -> None:
    emails = [
        _email("one", "<p>Invoice 100 issued on 2026-09-01: total Rs. 7.20</p>"),
        _email("two", "<p>Invoice 101 issued on 09/02/2026: total Rs 18.00</p>"),
        _email("three", "<p>Invoice 102 issued on 2026.09.03: total Rs1,250.50</p>"),
    ]

    result = mine_templates(emails)

    assert result == TemplateMiningResult(processed=3, skipped=0, templates_created=1)
    assert (
        Template.get().text
        == "Invoice <NUMBER> issued on <DATE>: total <CURRENCY_CODE><NUMBER>"
    )


def test_mine_templates_does_not_mask_words_containing_currency_code_letters() -> None:
    emails = [
        _email(f"plumber-{index}", "<p>Our plumbers. are ready</p>")
        for index in range(3)
    ]

    result = mine_templates(emails)

    assert result == TemplateMiningResult(processed=3, skipped=0, templates_created=1)
    assert Template.get().text == "Our plumbers. are ready"


def test_mine_templates_leaves_clusters_smaller_than_three_untagged() -> None:
    first = _email("one", "<p>Payment #100 received</p>")
    second = _email("two", "<p>Payment #101 received</p>")
    third = _email("three", "<p>Password reset requested</p>")

    result = mine_templates([first, second, third])

    assert result == TemplateMiningResult(processed=3, skipped=0, templates_created=0)
    assert Template.select().count() == 0
    assert Email.get_by_id(first.id).template_id is None
    assert Email.get_by_id(second.id).template_id is None
    assert Email.get_by_id(third.id).template_id is None


def test_mine_templates_tags_only_eligible_clusters() -> None:
    eligible = [
        _email("order-one", "<p>Order #100 confirmed</p>"),
        _email("order-two", "<p>Order #101 confirmed</p>"),
        _email("order-three", "<p>Order #102 confirmed</p>"),
    ]
    ineligible = [
        _email("reset-one", "<p>Password reset for A</p>"),
        _email("reset-two", "<p>Password reset for B</p>"),
    ]

    result = mine_templates([*eligible, *ineligible])

    assert result == TemplateMiningResult(processed=5, skipped=0, templates_created=1)
    template = Template.get()
    assert [Email.get_by_id(email.id).template_id for email in eligible] == [template.id] * 3
    assert [Email.get_by_id(email.id).template_id for email in ineligible] == [None] * 2


def test_mine_templates_rolls_back_template_writes_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emails = [
        _email("payment-one", "<p>Payment #100 received</p>"),
        _email("payment-two", "<p>Payment #101 received</p>"),
        _email("payment-three", "<p>Payment #102 received</p>"),
        _email("reset-one", "<p>Password reset for A</p>"),
        _email("reset-two", "<p>Password reset for B</p>"),
        _email("reset-three", "<p>Password reset for C</p>"),
    ]
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
        mine_templates(emails)

    assert Template.select().count() == 0
    assert [Email.get_by_id(email.id).template_id for email in emails] == [None] * len(emails)
