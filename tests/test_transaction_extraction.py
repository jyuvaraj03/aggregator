from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from playhouse.migrations import Runner

from aggregator.database import DATABASE_PATH, PROJECT_ROOT, close_database, database
from aggregator.field_parsers import approve_field_parsers, replace_field_parsers
from aggregator.models import (
    Account,
    Email,
    FieldParser,
    Template,
    Transaction,
    TransactionExtractionStatus,
)
from aggregator.parser_configuration import (
    ConstantFieldParser,
    FieldParserRule,
    FieldParserSet,
    MissingFieldParser,
    TransactionFieldName,
)
from aggregator.template_representation import TemplateRepresentation
from aggregator.transaction_extraction import (
    ExtractedTransaction,
    TransactionExtractionResult,
    _amount,
    _boolean,
    _transaction_date,
    extract_transaction,
    run_transaction_extraction,
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
        body="receipt",
        template=template,
    )


def _configure(template: Template, **constants: str) -> None:
    account = Account.get_or_none(Account.name == "Checking")
    if account is None:
        account = Account.create(name="Checking")
    template.account = account
    template.is_transaction_alert = True
    template.field_parsers_approved = True
    template.save()
    for field_name in TransactionFieldName:
        constant = constants.get(field_name.value)
        FieldParser.create(
            template=template,
            field_name=field_name,
            rule=(FieldParserRule.CONSTANT if constant is not None else FieldParserRule.MISSING),
            constant_value=constant,
        )


def _representation(**fields: str | None) -> TemplateRepresentation:
    resolved_fields: dict[str, str | None] = dict.fromkeys(
        field.value for field in TransactionFieldName
    )
    resolved_fields.update(fields)
    return TemplateRepresentation("receipt", (), resolved_fields)


def test_extract_transaction_returns_typed_fields_without_persistence() -> None:
    representation = _representation(
        amount=" 12,34,567.89 ",
        currency_code=" INR ",
        payee=" Example Shop ",
        description=" Purchase ",
        transaction_date="23 Aug, 2026",
        account_hint=" 1234 ",
        is_credit="FALSE",
    )

    assert extract_transaction(representation) == ExtractedTransaction(
        amount=Decimal("1234567.89"),
        currency_code="INR",
        payee="Example Shop",
        description="Purchase",
        transaction_date=date(2026, 8, 23),
        account_hint="1234",
        is_credit=False,
    )
    assert Transaction.select().count() == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("amount", "$12.50", "invalid amount"),
        ("transaction_date", "August 2026", "invalid transaction date"),
        ("is_credit", "yes", "invalid is_credit"),
    ],
)
def test_extract_transaction_rejects_invalid_fields(field: str, value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        extract_transaction(_representation(**{field: value}))


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

    result = run_transaction_extraction()

    transaction = Transaction.get(Transaction.email == email)
    assert result == TransactionExtractionResult(1, 1, 0, 0, 0)
    assert transaction.amount == Decimal("1234567.89")
    assert isinstance(transaction.amount, Decimal)
    assert transaction.transaction_date == date(2026, 8, 23)
    assert type(transaction.transaction_date) is date
    assert transaction.is_credit is False
    assert type(transaction.is_credit) is bool
    assert transaction.payee == "Example Shop"
    assert transaction.account_id == template.account_id
    assert transaction.account_hint == "1234"
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

    result = run_transaction_extraction()

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

    repeated = run_transaction_extraction()
    assert repeated == TransactionExtractionResult(4, 0, 4, 0, 0)


def test_replacing_parsers_clears_a_template_failure_for_retry() -> None:
    account = Account.create(name="Checking")
    template = Template.create(
        text="receipt",
        account=account,
        is_transaction_alert=True,
        transaction_extraction_status=TransactionExtractionStatus.FAILED.value,
        transaction_extraction_error="old failure",
    )
    _email(1, template)
    missing = MissingFieldParser(rule="missing")
    replace_field_parsers(
        template.id,
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
    assert refreshed.field_parsers_approved is False
    approve_field_parsers(template.id)
    assert run_transaction_extraction().created == 1


def test_new_email_for_succeeded_template_remains_eligible() -> None:
    template = Template.create(text="receipt")
    _configure(template, amount="10")
    _email(1, template)
    assert run_transaction_extraction().created == 1

    _email(2, template)

    assert run_transaction_extraction() == TransactionExtractionResult(1, 1, 0, 0, 0)
    assert Transaction.select().count() == 2


def test_extraction_skips_complete_but_unapproved_parser() -> None:
    account = Account.create(name="Checking")
    template = Template.create(text="receipt", account=account, is_transaction_alert=True)
    _email(1, template)
    missing = MissingFieldParser(rule="missing")
    replace_field_parsers(
        template.id,
        FieldParserSet(
            amount=ConstantFieldParser(rule="constant", constant_value="10"),
            currency_code=missing,
            payee=missing,
            description=missing,
            transaction_date=missing,
            account_hint=missing,
            is_credit=missing,
        ),
    )

    assert run_transaction_extraction() == TransactionExtractionResult(1, 0, 1, 0, 0)
    assert Transaction.select().count() == 0


def test_extraction_skips_unassigned_template_before_parser_or_representation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aggregator import transaction_extraction

    template = Template.create(text="receipt")
    email = _email(1, template)

    def unexpected(*args: object, **kwargs: object) -> object:
        pytest.fail("Unassigned templates must not load parsers or representations")

    monkeypatch.setattr(transaction_extraction, "parser_sets", unexpected)
    monkeypatch.setattr(transaction_extraction, "represent_email_template", unexpected)

    assert run_transaction_extraction() == TransactionExtractionResult(1, 0, 1, 0, 0)
    assert Transaction.select().count() == 0
    refreshed = Template.get_by_id(template.id)
    assert refreshed.transaction_extraction_status == TransactionExtractionStatus.PENDING.value
    assert refreshed.transaction_extraction_error is None
    assert Email.get_by_id(email.id).id == email.id
