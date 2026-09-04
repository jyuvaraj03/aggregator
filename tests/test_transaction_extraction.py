from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from playhouse.migrations import Runner

from aggregator.api.schemas import ConstantFieldParser, FieldParserSet, MissingFieldParser
from aggregator.database import DATABASE_PATH, PROJECT_ROOT, close_database, database
from aggregator.field_parsers import replace_field_parsers
from aggregator.models import (
    Email,
    FieldParser,
    FieldParserRule,
    Template,
    Transaction,
    TransactionExtractionStatus,
    TransactionFieldName,
)
from aggregator.transaction_extraction import (
    TransactionExtractionResult,
    _amount,
    _boolean,
    _transaction_date,
    extract_transactions,
)


@pytest.fixture(autouse=True)
def file_database(tmp_path: Path) -> Generator[None]:
    close_database()
    database.init(str(tmp_path / "transactions.sqlite3"))  # pyright: ignore[reportUnknownMemberType]
    database.connect()
    try:
        Runner(database, directory=str(PROJECT_ROOT / "migrations")).up()
        yield
    finally:
        close_database()
        database.init(str(DATABASE_PATH))  # pyright: ignore[reportUnknownMemberType]


def _email(index: int, template: Template | None = None) -> Email:
    return Email.create(
        message_id=f"message-{index}",
        received_at=datetime(2026, 9, 1, index, tzinfo=UTC),
        sender="merchant@example.com",
        subject="Receipt",
        body_text="receipt",
        body_html="<p>receipt</p>",
        headers={},
        template=template,
    )


def _configure(template: Template, **constants: str) -> None:
    for field_name in TransactionFieldName:
        constant = constants.get(field_name.value)
        FieldParser.create(
            template=template,
            field_name=field_name,
            rule=(FieldParserRule.CONSTANT if constant is not None else FieldParserRule.MISSING),
            constant_value=constant,
        )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234567.89", Decimal("1234567.89")),
        ("1,234,567.89", Decimal("1234567.89")),
        ("12,34,567.89", Decimal("1234567.89")),
        ("-1,23,456", Decimal("-123456")),
        (" +12.50 ", Decimal("12.50")),
    ],
)
def test_amount_conversion_accepts_supported_grouping(raw: str, expected: Decimal) -> None:
    assert _amount(raw) == expected


@pytest.mark.parametrize("raw", ["1,23,45", "123,4567", "$12.50", "INR 20", "NaN", "inf"])
def test_amount_conversion_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError, match="invalid amount"):
        _amount(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "Aug 23, 2026",
        "23 Aug, 2026",
        "23 Aug 2026",
        "2026-08-23",
        "2026/08/23",
        "08/23/2026",
        "23 Aug 26",
    ],
)
def test_date_conversion_accepts_requested_formats(raw: str) -> None:
    assert _transaction_date(raw) == date(2026, 8, 23)


def test_date_conversion_prefers_day_first_for_ambiguous_dates() -> None:
    assert _transaction_date("08/09/2026") == date(2026, 9, 8)


@pytest.mark.parametrize("raw", ["2026", "August 2026", "not Aug 23, 2026", "31/02/2026"])
def test_date_conversion_rejects_incomplete_or_invalid_dates(raw: str) -> None:
    with pytest.raises(ValueError, match="invalid transaction date"):
        _transaction_date(raw)


@pytest.mark.parametrize("raw", ["true", "TRUE", "True", "tRuE"])
def test_boolean_conversion_accepts_true_case_insensitively(raw: str) -> None:
    assert _boolean(raw) is True


@pytest.mark.parametrize("raw", ["false", "FALSE", "False", "fAlSe"])
def test_boolean_conversion_accepts_false_case_insensitively(raw: str) -> None:
    assert _boolean(raw) is False


def test_extraction_persists_typed_transaction_values() -> None:
    template = Template.create(text="receipt")
    email = _email(1, template)
    _configure(
        template,
        amount="12,34,567.89",
        currency_code="INR",
        payee=" Example Shop ",
        description="Purchase",
        transaction_date="23 Aug, 2026",
        account_hint="1234",
        is_credit="FALSE",
    )

    result = extract_transactions()

    transaction = Transaction.get(Transaction.email == email)
    assert result == TransactionExtractionResult(1, 1, 0, 0, 0)
    assert transaction.amount == Decimal("1234567.89")
    assert isinstance(transaction.amount, Decimal)
    assert transaction.transaction_date == date(2026, 8, 23)
    assert type(transaction.transaction_date) is date
    assert transaction.is_credit is False
    assert type(transaction.is_credit) is bool
    assert transaction.payee == "Example Shop"
    assert Template.get_by_id(template.id).transaction_extraction_status == "succeeded"


def test_extraction_is_template_atomic_and_skips_ineligible_emails() -> None:
    valid = Template.create(text="receipt")
    _configure(valid, amount="1,234.50")
    _email(1, valid)

    invalid = Template.create(text="receipt")
    _configure(invalid, amount="$20")
    invalid_emails = [_email(2, invalid), _email(3, invalid)]

    incomplete = Template.create(text="receipt")
    FieldParser.create(
        template=incomplete,
        field_name=TransactionFieldName.AMOUNT,
        rule=FieldParserRule.CONSTANT,
        constant_value="10",
    )
    _email(4, incomplete)
    _email(5)

    result = extract_transactions()

    assert result == TransactionExtractionResult(5, 1, 2, 1, 2)
    assert Transaction.select().count() == 1
    failed = Template.get_by_id(invalid.id)
    assert failed.transaction_extraction_status == TransactionExtractionStatus.FAILED.value
    assert (
        failed.transaction_extraction_error == f"email {invalid_emails[0].id}: invalid amount '$20'"
    )
    assert all(
        Transaction.get_or_none(Transaction.email == email) is None for email in invalid_emails
    )

    repeated = extract_transactions()
    assert repeated == TransactionExtractionResult(4, 0, 4, 0, 0)


def test_replacing_parsers_clears_a_template_failure_for_retry() -> None:
    template = Template.create(
        text="receipt",
        transaction_extraction_status=TransactionExtractionStatus.FAILED.value,
        transaction_extraction_error="old failure",
    )
    _email(1, template)
    missing = MissingFieldParser(rule="missing")
    replace_field_parsers(
        template,
        FieldParserSet(
            amount=ConstantFieldParser(rule="constant", constant_value="1,000"),
            currency_code=missing,
            payee=missing,
            description=missing,
            transaction_date=missing,
            account_hint=missing,
            is_credit=missing,
        ),
    )

    refreshed = Template.get_by_id(template.id)
    assert refreshed.transaction_extraction_status == TransactionExtractionStatus.PENDING.value
    assert refreshed.transaction_extraction_error is None
    assert extract_transactions().created == 1


def test_new_email_for_succeeded_template_remains_eligible() -> None:
    template = Template.create(text="receipt")
    _configure(template, amount="10")
    _email(1, template)
    assert extract_transactions().created == 1

    _email(2, template)

    assert extract_transactions() == TransactionExtractionResult(1, 1, 0, 0, 0)
    assert Transaction.select().count() == 2
