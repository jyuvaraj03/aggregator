from __future__ import annotations

# Drain3, Peewee, and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from peewee import IntegrityError
from playhouse.migrations import Runner

from aggregator.database import (
    DATABASE_PATH,
    PROJECT_ROOT,
    close_database,
    connect_database,
    database,
)
from aggregator.email_content import readable_body
from aggregator.models import Email, FieldParser, Template
from aggregator.parser_configuration import FieldParserRule, TransactionFieldName
from aggregator.reads import email_by_id
from aggregator.template_assignment import (
    TemplateAssignmentResult,
    assign_email_templates,
)
from aggregator.template_mining import (
    MASKING_INSTRUCTIONS,
    MinedPattern,
    MiningRecord,
    MiningResult,
    bulk_mine_templates,
    get_extracted_parameters,
)


def test_bulk_mine_templates_returns_no_patterns_for_empty_input() -> None:
    assert bulk_mine_templates([]) == MiningResult(0, (), ())


def test_bulk_mine_templates_skips_empty_records_and_preserves_assignment_order() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord("blank", "  "),
            MiningRecord("first", "Order #100 confirmed for $7.20"),
            MiningRecord("second", "Order #101 confirmed for $8.10"),
            MiningRecord("third", "Order #102 confirmed for $9.00"),
        ]
    )

    assert result == MiningResult(
        processed=3,
        skipped_record_ids=("blank",),
        patterns=(
            MinedPattern(
                "Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>",
                ("first", "second", "third"),
            ),
        ),
    )


def test_bulk_mine_templates_masks_dates_currency_numbers_and_times() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord(1, "Payment 100 at 09:30 AM on 2026-09-01: Rs. 7.20"),
            MiningRecord(2, "Payment 101 at 21:30:45 on 09/02/2026: Rs 18.00"),
            MiningRecord(3, "Payment 102 at 21:30:45.123 UTC+05:30 on 2026.09.03: Rs1,250.50"),
        ]
    )

    assert result.patterns == (
        MinedPattern("Payment <NUMBER> at <TIME> on <DATE>: <CURRENCY_CODE><NUMBER>", (1, 2, 3)),
    )


def test_bulk_mine_templates_masks_iso_currency_codes_as_atomic_money() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord(1, "Card used for INR 1,051.73 at MICROSOFT INDIA CYBS SI"),
            MiningRecord(2, "Card used for MYR 1,050.00 at MICROSOFT INDIA CYBS SI"),
            MiningRecord(3, "Card used for NZD 99.00 at MICROSOFT INDIA CYBS SI"),
        ]
    )

    assert result.patterns == (
        MinedPattern(
            "Card used for <CURRENCY_CODE><NUMBER> at MICROSOFT INDIA CYBS SI",
            (1, 2, 3),
        ),
    )


def test_atomic_money_does_not_shift_masks_when_following_text_has_different_length() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord(1, "Card used for INR 1.00. Info: ONE TWO THREE FOUR"),
            MiningRecord(2, "Card used for INR 2.00. Info: FIVE SIX SEVEN EIGHT"),
            MiningRecord(3, "Card used for INR 3.00. Info: NINE TEN ELEVEN TWELVE"),
            MiningRecord(4, "Card used for MYR 4.00. Info: ONE TWO THREE"),
            MiningRecord(5, "Card used for MYR 5.00. Info: FOUR FIVE SIX"),
            MiningRecord(6, "Card used for MYR 6.00. Info: SEVEN EIGHT NINE"),
        ]
    )

    assert result.patterns == (
        MinedPattern("Card used for <CURRENCY_CODE><NUMBER>. Info: <*> <*> <*> <*>", (1, 2, 3)),
        MinedPattern("Card used for <CURRENCY_CODE><NUMBER>. Info: <*> <*> <*>", (4, 5, 6)),
    )


def test_bulk_mine_templates_masks_a_ten_digit_number() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord(1, "OTP 7308080808 generated"),
            MiningRecord(2, "OTP 7308080808 generated"),
            MiningRecord(3, "OTP 7308080808 generated"),
        ]
    )

    assert result.patterns == (MinedPattern("OTP <NUMBER> generated", (1, 2, 3)),)


def test_bulk_mine_templates_includes_single_record_clusters() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord(1, "Payment #100 received"),
            MiningRecord(2, "Payment #101 received"),
            MiningRecord(3, "Password reset requested"),
        ]
    )

    assert result.processed == 3
    assert result.patterns == (
        MinedPattern("Payment #<NUMBER> received", (1, 2)),
        MinedPattern("Password reset requested", (3,)),
    )


def test_bulk_mine_templates_picks_existing_templates_before_mining_new_ones() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord("existing", "Order #100 confirmed"),
            MiningRecord("new-1", "Payment #100 received"),
            MiningRecord("new-2", "Payment #101 received"),
            MiningRecord("new-3", "Payment #102 received"),
        ],
        ["Order #<NUMBER> confirmed", "An unused existing template"],
    )

    assert result == MiningResult(
        processed=4,
        skipped_record_ids=(),
        patterns=(
            MinedPattern("Order #<NUMBER> confirmed", ("existing",)),
            MinedPattern("Payment #<NUMBER> received", ("new-1", "new-2", "new-3")),
        ),
    )


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-03",
        "2026/9/3",
        "2026.09.3",
        "03-09-2026",
        "3/9/26",
        "Aug 23, 2026",
        "aug. 23rd 2026",
        "September 1st, 26",
        "23 Aug 2026",
        "23rd August, 2026",
    ],
)
def test_date_masking_regex_matches_supported_date_formats(value: str) -> None:
    assert MASKING_INSTRUCTIONS[1].regex.fullmatch(value)


@pytest.mark.parametrize(
    "value",
    ["order2026-09-03", "2026-09-03receipt", "2026-9", "Foo 23, 2026", "August 23"],
)
def test_date_masking_regex_rejects_invalid_or_embedded_dates(value: str) -> None:
    assert MASKING_INSTRUCTIONS[1].regex.search(value) is None


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "007",
        "42",
        "+42",
        "-42",
        "1.0",
        "123.456",
        "1,234",
        "12,345,678",
        "1,23,456",
        "12,34,567",
        "1,23,45,678",
        "1,234.56",
        "12,34,567.89",
        "+1,234.56",
        "-12,345,678.90",
    ],
)
def test_number_masking_regex_matches_supported_number_formats(value: str) -> None:
    assert MASKING_INSTRUCTIONS[4].regex.fullmatch(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "+",
        "-",
        ".5",
        "+.5",
        "-.5",
        "5.",
        "1.2.3",
        "1,23",
        "123,45,678",
        "1,,234",
        "1,2345",
        "1,234.",
        "1,234.5.6",
        "123,",
        "1_000",
        "1e3",
        "NaN",
        "Infinity",
    ],
)
def test_number_masking_regex_rejects_unsupported_number_formats(value: str) -> None:
    assert MASKING_INSTRUCTIONS[4].regex.fullmatch(value) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Order #42 confirmed", ["42"]),
        ("Balances: -7, +8.25, and 1,234.50.", ["-7", "+8.25", "1,234.50"]),
        ("($1,250.50) or ₹0", ["1,250.50", "0"]),
        ("[007]; {12,345,678}; ₹12,34,567.89", ["007", "12,345,678", "12,34,567.89"]),
    ],
)
def test_number_masking_regex_finds_numbers_between_common_delimiters(
    text: str, expected: list[str]
) -> None:
    assert MASKING_INSTRUCTIONS[4].regex.findall(text) == expected


def test_parameter_extraction_supports_amount_immediately_after_rs_dot() -> None:
    parameters = get_extracted_parameters(
        MiningRecord("payment", "Payment Rs.700.00"),
        "Payment <CURRENCY_CODE><NUMBER>",
    )

    assert [(parameter.value, parameter.mask_name) for parameter in parameters] == [
        ("Rs.", "CURRENCY_CODE"),
        ("700.00", "NUMBER"),
    ]


def test_parameter_extraction_supports_an_iso_currency_code() -> None:
    parameters = get_extracted_parameters(
        MiningRecord("payment", "Payment MYR 700.00"),
        "Payment <CURRENCY_CODE><NUMBER>",
    )

    assert [(parameter.value, parameter.mask_name) for parameter in parameters] == [
        ("MYR", "CURRENCY_CODE"),
        ("700.00", "NUMBER"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "item42",
        "42items",
        "version1.2",
        "1.2release",
        "a1,234",
        "1,234b",
    ],
)
def test_number_masking_regex_does_not_match_numbers_embedded_in_words_or_dotted_tokens(
    text: str,
) -> None:
    assert MASKING_INSTRUCTIONS[4].regex.search(text) is None


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


def _email(message_id: str, body_html: str, *, template: Template | None = None) -> Email:
    return Email.create(
        message_id=message_id,
        received_at=datetime(2026, 9, 1, tzinfo=UTC) + timedelta(minutes=Email.select().count()),
        sender="merchant@example.com",
        body=readable_body(body_html, None),
        template=template,
    )


def test_email_representation_returns_template_and_ordered_parameters() -> None:
    template = Template.create(text="Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>")
    email = _email("order", "<p>Order #42 confirmed for $7.20</p>", template=template)

    record = email_by_id(email.id)
    assert record is not None
    representation = record.representation

    assert representation is not None
    assert representation.template_text == template.text
    parameters = [
        (parameter.value, parameter.mask_name) for parameter in representation.extracted_parameters
    ]
    assert parameters == [
        ("42", "NUMBER"),
        ("$", "CURRENCY_CODE"),
        ("7.20", "NUMBER"),
    ]


def test_email_representation_resolves_extracted_constant_and_missing_fields() -> None:
    template = Template.create(text="Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>")
    email = _email("order", "<p>Order #42 confirmed for $7.20</p>", template=template)
    FieldParser.create(
        template=template,
        field_name=TransactionFieldName.AMOUNT,
        rule=FieldParserRule.EXTRACTED,
        parameter_indices=[1, 2],
    )
    FieldParser.create(
        template=template,
        field_name=TransactionFieldName.DESCRIPTION,
        rule=FieldParserRule.CONSTANT,
        constant_value="confirmed",
    )
    FieldParser.create(
        template=template,
        field_name=TransactionFieldName.PAYEE,
        rule=FieldParserRule.MISSING,
    )

    record = email_by_id(email.id)
    assert record is not None
    representation = record.representation

    assert representation is not None
    assert representation.resolved_fields == {
        "amount": "$ 7.20",
        "currency_code": None,
        "payee": None,
        "description": "confirmed",
        "transaction_date": None,
        "account_hint": None,
        "is_credit": None,
    }


def test_email_representation_has_no_resolved_fields_without_parsers() -> None:
    template = Template.create(text="Order #<NUMBER> confirmed")
    email = _email("order", "<p>Order #42 confirmed</p>", template=template)

    record = email_by_id(email.id)
    assert record is not None
    representation = record.representation

    assert representation is not None
    assert representation.resolved_fields == {
        "amount": None,
        "currency_code": None,
        "payee": None,
        "description": None,
        "transaction_date": None,
        "account_hint": None,
        "is_credit": None,
    }


@pytest.mark.parametrize(
    ("rule", "indices", "constant_value", "message"),
    [
        (FieldParserRule.EXTRACTED, [], None, "requires at least one"),
        (FieldParserRule.EXTRACTED, [0, 0], None, "duplicate"),
        (FieldParserRule.EXTRACTED, [-1], None, "negative"),
        (FieldParserRule.EXTRACTED, [1], None, "unavailable"),
        (FieldParserRule.EXTRACTED, [0], "value", "cannot have a constant"),
        (FieldParserRule.CONSTANT, [0], "value", "cannot have parameter"),
        (FieldParserRule.CONSTANT, [], None, "requires a constant"),
        (FieldParserRule.MISSING, [0], None, "cannot have parameter"),
        (FieldParserRule.MISSING, [], "value", "cannot have a constant"),
        ("unknown", [], None, "Unsupported"),
    ],
)
def test_field_parser_rejects_invalid_rule_configuration(
    rule: FieldParserRule | str, indices: list[int], constant_value: str | None, message: str
) -> None:
    template = Template.create(text="Order #<NUMBER> confirmed")

    with pytest.raises(ValueError, match=message):
        FieldParser.create(
            template=template,
            field_name=TransactionFieldName.AMOUNT,
            rule=rule,
            parameter_indices=indices,
            constant_value=constant_value,
        )


def test_field_parser_rejects_unknown_field_name() -> None:
    template = Template.create(text="Order #<NUMBER> confirmed")

    with pytest.raises(ValueError, match="Unsupported transaction field name"):
        FieldParser.create(
            template=template,
            field_name="order_number",
            rule=FieldParserRule.MISSING,
        )


def test_field_parser_uniqueness_and_template_cascade() -> None:
    template = Template.create(text="Order #<NUMBER> confirmed")
    FieldParser.create(
        template=template,
        field_name=TransactionFieldName.AMOUNT,
        rule=FieldParserRule.EXTRACTED,
        parameter_indices=[0],
    )

    with pytest.raises(IntegrityError):
        FieldParser.create(
            template=template,
            field_name=TransactionFieldName.AMOUNT,
            rule=FieldParserRule.MISSING,
        )

    template.delete_instance()

    assert FieldParser.select().count() == 0


def test_representation_defensively_revalidates_stale_parser_indices() -> None:
    template = Template.create(text="Order #<NUMBER> confirmed")
    FieldParser.insert(
        template=template,
        field_name=TransactionFieldName.AMOUNT,
        rule=FieldParserRule.EXTRACTED,
        parameter_indices=[1],
        constant_value=None,
    ).execute()
    email = _email("order", "<p>Order #42 confirmed</p>", template=template)

    with pytest.raises(ValueError, match="unavailable"):
        email_by_id(email.id)


def test_unassigned_email_has_no_representation() -> None:
    email = _email("untagged", "<p>Order #42 confirmed</p>")
    record = email_by_id(email.id)
    assert record is not None
    assert record.representation is None


def test_assignment_loads_untagged_html_emails_and_assigns_template() -> None:
    tagged = Template.create(text="already tagged")
    _email("tagged", "<p>Order #999 confirmed</p>", template=tagged)
    emails = [_email(str(index), f"<h1>Order</h1><p>#{index} confirmed</p>") for index in range(3)]
    _email("empty", "<script>secret()</script><div> </div>")

    result = assign_email_templates()

    template = Template.get(Template.text == "Order #<NUMBER> confirmed")
    assert result == TemplateAssignmentResult(
        processed=3,
        skipped=1,
        templates_created=1,
        created_template_ids=(template.id,),
    )
    assert [Email.get_by_id(email.id).template_id for email in emails] == [template.id] * 3
    assert Email.get_by_id(1).template_id == tagged.id


def test_assignment_reuses_existing_template_without_counting_it_as_new() -> None:
    existing = Template.create(text="Order #<NUMBER> confirmed")
    email = _email("order", "<p>Order #42 confirmed</p>")

    result = assign_email_templates()

    assert result == TemplateAssignmentResult(
        processed=1,
        skipped=0,
        templates_created=0,
        created_template_ids=(),
    )
    assert Email.get_by_id(email.id).template_id == existing.id


def test_assignment_guard_prevents_persistence_after_mining() -> None:
    email = _email("order", "<p>Order #42 confirmed</p>")

    @contextmanager
    def superseded() -> Generator[None]:
        raise RuntimeError("superseded")
        yield

    with pytest.raises(RuntimeError, match="superseded"):
        assign_email_templates(commit_guard=superseded)

    assert Template.select().count() == 0
    assert Email.get_by_id(email.id).template_id is None


def test_assignment_rolls_back_when_template_creation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emails = [
        *[_email(f"order-{index}", f"<p>Order #{index} confirmed</p>") for index in range(3)],
        *[_email(f"reset-{index}", f"<p>Password reset #{index}</p>") for index in range(3)],
    ]
    original_create = Template.create
    calls = 0

    def fail_second_create(**values: object) -> Template:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("template creation failed")
        return original_create(**values)

    monkeypatch.setattr(Template, "create", fail_second_create)
    with pytest.raises(RuntimeError, match="template creation failed"):
        assign_email_templates()

    assert Template.select().count() == 0
    assert [Email.get_by_id(email.id).template_id for email in emails] == [None] * 6


def test_assignment_rolls_back_when_assignment_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    emails = [_email(str(index), f"<p>Order #{index} confirmed</p>") for index in range(3)]

    def fail_assignment() -> int:
        raise RuntimeError("assignment failed")

    monkeypatch.setattr("peewee.ModelUpdate.execute", lambda _: fail_assignment())
    with pytest.raises(RuntimeError, match="assignment failed"):
        assign_email_templates()

    assert Template.select().count() == 0
    assert [Email.get_by_id(email.id).template_id for email in emails] == [None] * 3
