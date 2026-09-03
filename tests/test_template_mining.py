from __future__ import annotations

# Drain3, Peewee, and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

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


def test_bulk_mine_templates_masks_a_ten_digit_number() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord(1, "OTP 7308080808 generated"),
            MiningRecord(2, "OTP 7308080808 generated"),
            MiningRecord(3, "OTP 7308080808 generated"),
        ]
    )

    assert result.patterns == (MinedPattern("OTP <NUMBER> generated", (1, 2, 3)),)


def test_bulk_mine_templates_excludes_clusters_below_minimum_size() -> None:
    result = bulk_mine_templates(
        [
            MiningRecord(1, "Payment #100 received"),
            MiningRecord(2, "Payment #101 received"),
            MiningRecord(3, "Password reset requested"),
        ]
    )

    assert result.processed == 3
    assert result.patterns == ()


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
    assert MASKING_INSTRUCTIONS[0].regex.fullmatch(value)


@pytest.mark.parametrize(
    "value",
    ["order2026-09-03", "2026-09-03receipt", "2026-9", "Foo 23, 2026", "August 23"],
)
def test_date_masking_regex_rejects_invalid_or_embedded_dates(value: str) -> None:
    assert MASKING_INSTRUCTIONS[0].regex.search(value) is None


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
    assert MASKING_INSTRUCTIONS[3].regex.fullmatch(value)


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
    assert MASKING_INSTRUCTIONS[3].regex.fullmatch(value) is None


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
    assert MASKING_INSTRUCTIONS[3].regex.findall(text) == expected


def test_parameter_extraction_supports_amount_immediately_after_rs_dot() -> None:
    parameters = get_extracted_parameters(
        MiningRecord("payment", "Payment Rs.700.00"),
        "Payment <CURRENCY_CODE><NUMBER>",
    )

    assert [(parameter.value, parameter.mask_name) for parameter in parameters] == [
        ("Rs.", "CURRENCY_CODE"),
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
    assert MASKING_INSTRUCTIONS[3].regex.search(text) is None


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
        body_html=body_html,
        headers={},
        template=template,
    )


def test_email_representation_returns_template_and_ordered_parameters() -> None:
    template = Template.create(
        text="Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>"
    )
    email = _email("order", "<p>Order #42 confirmed for $7.20</p>", template=template)

    representation = email.representation()

    assert representation is not None
    assert representation.template_text == template.text
    parameters = [
        (parameter.value, parameter.mask_name)
        for parameter in representation.extracted_parameters
    ]
    assert parameters == [
        ("42", "NUMBER"),
        ("$", "CURRENCY_CODE"),
        ("7.20", "NUMBER"),
    ]


def test_unassigned_email_has_no_representation() -> None:
    assert _email("untagged", "<p>Order #42 confirmed</p>").representation() is None


def test_assignment_loads_untagged_html_emails_and_assigns_template() -> None:
    tagged = Template.create(text="already tagged")
    _email("tagged", "<p>Order #999 confirmed</p>", template=tagged)
    emails = [_email(str(index), f"<h1>Order</h1><p>#{index} confirmed</p>") for index in range(3)]
    _email("empty", "<script>secret()</script><div> </div>")

    result = assign_email_templates()

    template = Template.get(Template.text == "Order #<NUMBER> confirmed")
    assert result == TemplateAssignmentResult(processed=3, skipped=1, templates_created=1)
    assert [Email.get_by_id(email.id).template_id for email in emails] == [template.id] * 3
    assert Email.get_by_id(1).template_id == tagged.id


def test_assignment_reuses_existing_template_without_counting_it_as_new() -> None:
    existing = Template.create(text="Order #<NUMBER> confirmed")
    emails = [_email(str(index), f"<p>Order #{index} confirmed</p>") for index in range(3)]

    result = assign_email_templates()

    assert result == TemplateAssignmentResult(processed=3, skipped=0, templates_created=0)
    assert [Email.get_by_id(email.id).template_id for email in emails] == [existing.id] * 3


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
