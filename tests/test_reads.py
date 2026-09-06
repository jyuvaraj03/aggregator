from __future__ import annotations

# Peewee models and migration/test utilities have dynamically typed interfaces.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from playhouse.migrations import Runner
from playhouse.test_utils import count_queries

from aggregator import field_parsers, queries, reads, template_representation
from aggregator.api import serializers
from aggregator.database import PROJECT_ROOT, close_database, database, database_connection
from aggregator.field_parsers import (
    FieldParserGenerationError,
    field_parser_snapshot,
    generate_and_replace_field_parsers,
    replace_field_parsers,
)
from aggregator.models import Email, FieldParser, Template, Transaction
from aggregator.parser_configuration import (
    TRANSACTION_FIELD_NAMES,
    ConstantFieldParser,
    ExtractedFieldParser,
    FieldParserSet,
)
from aggregator.queries import TemplateNotFoundError
from aggregator.template_assignment import assign_email_templates
from aggregator.transaction_extraction import extract_transactions


@pytest.fixture(autouse=True)
def isolated_database(tmp_path: Path) -> Generator[None]:
    close_database()
    original_path = database.database
    database.init(str(tmp_path / "reads.sqlite3"))
    with database_connection():
        Runner(database, directory=str(PROJECT_ROOT / "migrations")).up()
    try:
        yield
    finally:
        close_database()
        database.init(original_path)


def _email(
    index: int,
    template: Template | None = None,
    *,
    html: str | None = "<p>Paid 10</p>",
    plain: str | None = None,
) -> Email:
    return Email.create(
        message_id=f"email-{index}",
        received_at=datetime(2026, 9, 1, tzinfo=UTC),
        sender="merchant@example.com",
        body_html=html,
        body_text=plain,
        headers={},
        template=template,
    )


def _parsers() -> FieldParserSet:
    return FieldParserSet.model_validate(
        {
            **{name: {"rule": "missing"} for name in TRANSACTION_FIELD_NAMES},
            "amount": {"rule": "extracted", "parameter_indices": [0]},
        }
    )


def test_serializers_use_only_detached_prepared_values(monkeypatch: pytest.MonkeyPatch) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        email = _email(1, template)
        Transaction.create(email=email, amount=Decimal("10"))
    snapshot = replace_field_parsers(template.id, _parsers())
    email_record = reads.email_by_id(email.id)
    email_page = reads.email_page(1)
    transaction_page = reads.transaction_page(1)
    template_record = reads.template_by_id(template.id)
    template_page = reads.template_page(1)
    assert database.is_closed()
    assert email_record is not None
    assert template_record is not None
    assert template_record.example is not None

    def unexpected_work(*args: object, **kwargs: object) -> None:
        pytest.fail("Serialization attempted database access or parsing")

    monkeypatch.setattr(database, "execute_sql", unexpected_work)
    monkeypatch.setattr(template_representation, "get_extracted_parameters", unexpected_work)
    monkeypatch.setattr(template_representation, "resolve_fields", unexpected_work)
    monkeypatch.setattr(reads, "readable_body", unexpected_work)
    monkeypatch.setattr(field_parsers, "readable_body", unexpected_work)

    assert serializers.email_detail(email_record).body == "Paid 10"
    assert serializers.email_summary(email_page.items[0]).representation is not None
    assert serializers.transaction_response(transaction_page.items[0]).amount == Decimal("10")
    assert serializers.template_response(template_page.items[0]).email_count == 1
    assert serializers.template_email_example(template_record.example).body == "Paid 10"
    assert serializers.parser_snapshot_response(snapshot).preview is not None
    assert database.is_closed()


@pytest.mark.parametrize("operation", [reads.email_page, reads.transaction_page])
def test_page_query_count_is_bounded(operation: Callable[[int], object]) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        email = _email(0, template)
        Transaction.create(email=email)
        replace_field_parsers(template.id, _parsers())
        with count_queries(only_select=True) as small:
            operation(1)

        for index in range(1, 20):
            if index % 2:
                template = Template.create(text="Paid <NUMBER>")
                replace_field_parsers(template.id, _parsers())
            email = _email(index, template)
            Transaction.create(email=email)
        with count_queries(only_select=True) as large:
            operation(1)

    assert small.count == large.count
    assert large.count <= 4


@pytest.mark.parametrize(
    ("html", "plain", "expected"),
    [
        (None, "Paid 10", "10"),
        ("<div> </div>", "Paid 10", "10"),
        ("<p>Paid 20</p>", "Paid 10", "20"),
    ],
)
def test_assignment_preview_and_extraction_share_body_selection(
    html: str | None, plain: str, expected: str
) -> None:
    with database_connection():
        for index in range(3):
            _email(index, html=html, plain=plain)
        _email(3, html=None, plain=None)
    assignment = assign_email_templates()
    assert assignment.processed == 3
    assert assignment.skipped == 1
    template = reads.template_page(1).items[0]
    snapshot = replace_field_parsers(template.id, _parsers())
    assert snapshot.preview is not None
    assert snapshot.preview["amount"] == expected
    result = extract_transactions()
    assert result.created == 3
    assert result.skipped == 1
    for transaction in reads.transaction_page(1).items:
        assert transaction.amount == Decimal(expected)
        assert transaction.representation is not None
        assert transaction.representation.resolved_fields == snapshot.preview
    example = reads.template_by_id(template.id)
    assert example is not None and example.example is not None
    assert example.example.body == f"Paid {expected}"
    assert database.is_closed()


def test_replacement_rolls_back_when_preview_fails() -> None:
    with database_connection():
        template = Template.create(
            text="Paid <NUMBER>",
            transaction_extraction_status="failed",
            transaction_extraction_error="original failure",
        )
        _email(1, template, html="<p>Unrelated message</p>")
        FieldParser.create(
            template=template,
            field_name="amount",
            rule="constant",
            constant_value="10",
        )

    with pytest.raises(ValueError, match="unavailable"):
        replace_field_parsers(template.id, _parsers())
    assert database.is_closed()
    snapshot = field_parser_snapshot(template.id)
    assert snapshot.parsers.amount == ConstantFieldParser(rule="constant", constant_value="10")
    assert snapshot.transaction_extraction_status == "failed"
    assert snapshot.transaction_extraction_error == "original failure"


def test_replacement_rolls_back_when_storage_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
    original = replace_field_parsers(template.id, _parsers())

    def fail_save(*args: object, **kwargs: object) -> None:
        raise RuntimeError("save failed")

    with monkeypatch.context() as context:
        context.setattr(FieldParser, "save", fail_save)
        with pytest.raises(RuntimeError, match="save failed"):
            replace_field_parsers(
                template.id,
                FieldParserSet(payee=ConstantFieldParser(rule="constant", constant_value="Shop")),
            )
    assert database.is_closed()
    assert field_parser_snapshot(template.id) == original


def test_generation_uses_earliest_email_after_releasing_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with database_connection():
        template = Template.create(
            text="Paid <CURRENCY_CODE><NUMBER>",
            transaction_extraction_status="failed",
            transaction_extraction_error="old failure",
        )
        later = _email(2, template, html="<p>Paid $20</p>")
        later.received_at = datetime(2026, 9, 2, tzinfo=UTC)
        later.save()
        earlier = _email(1, template, html="<p>Paid Rs.10</p>")
        earlier.received_at = datetime(2026, 9, 1, tzinfo=UTC)
        earlier.save()
        FieldParser.create(
            template=template,
            field_name="payee",
            rule="constant",
            constant_value="Old Shop",
        )

    generated = FieldParserSet.model_validate(
        {
            **{name: {"rule": "missing"} for name in TRANSACTION_FIELD_NAMES},
            "amount": {"rule": "extracted", "parameter_indices": [1]},
            "currency_code": {"rule": "extracted", "parameter_indices": [0]},
        }
    )

    def generate(template_text: str, parameter_example: object) -> FieldParserSet:
        assert database.is_closed()
        assert template_text == "Paid <CURRENCY_CODE><NUMBER>"
        assert parameter_example == [
            {"index": 0, "mask_name": "CURRENCY_CODE", "value": "Rs."},
            {"index": 1, "mask_name": "NUMBER", "value": "10"},
        ]
        return generated

    monkeypatch.setattr(field_parsers.parser_generation, "generate_field_parsers", generate)

    snapshot = generate_and_replace_field_parsers(template.id)

    assert snapshot.example_email_id == earlier.id
    assert snapshot.parsers == generated
    assert snapshot.preview is not None
    assert snapshot.preview["amount"] == "10"
    assert snapshot.preview["currency_code"] == "Rs."
    assert snapshot.preview["payee"] is None
    assert snapshot.transaction_extraction_status == "pending"
    assert snapshot.transaction_extraction_error is None
    assert database.is_closed()


def test_generation_failure_preserves_existing_parsers(monkeypatch: pytest.MonkeyPatch) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        _email(1, template)
    original = replace_field_parsers(template.id, _parsers())

    def fail_generation(*args: object) -> FieldParserSet:
        raise ConnectionError("provider unavailable")

    monkeypatch.setattr(
        field_parsers.parser_generation,
        "generate_field_parsers",
        fail_generation,
    )

    with pytest.raises(FieldParserGenerationError, match="Field parser generation failed"):
        generate_and_replace_field_parsers(template.id)

    assert field_parser_snapshot(template.id) == original


def test_missing_template_does_not_invoke_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_generation(*args: object) -> FieldParserSet:
        pytest.fail("Generation should not run")

    monkeypatch.setattr(
        field_parsers.parser_generation, "generate_field_parsers", unexpected_generation
    )
    with pytest.raises(TemplateNotFoundError, match="Template not found"):
        generate_and_replace_field_parsers(999)
    assert database.is_closed()


def test_read_failure_closes_operation_owned_connection() -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        email = _email(1, template)
        FieldParser.insert(
            template=template, field_name="amount", rule="extracted", parameter_indices=[2]
        ).execute()
    with pytest.raises(ValueError, match="unavailable"):
        reads.email_by_id(email.id)
    assert database.is_closed()


def test_extraction_skips_incomplete_configuration_before_validation() -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        _email(1, template)
        FieldParser.insert(
            template=template, field_name="amount", rule="extracted", parameter_indices=[2]
        ).execute()
    result = extract_transactions()
    assert result.created == 0
    assert result.skipped == 1
    assert result.failed_templates == 0
    with database_connection():
        assert Template.get_by_id(template.id).transaction_extraction_status == "pending"


def test_extraction_records_invalid_complete_configuration_as_failure() -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        email = _email(1, template)
    replace_field_parsers(template.id, _parsers())
    with database_connection():
        FieldParser.update(parameter_indices=[2]).where(
            (FieldParser.template == template.id) & (FieldParser.field_name == "amount")
        ).execute()
    result = extract_transactions()
    assert result.created == 0
    assert result.failed_templates == 1
    assert result.failed_emails == 1
    with database_connection():
        failed = Template.get_by_id(template.id)
        assert failed.transaction_extraction_status == "failed"
        assert failed.transaction_extraction_error is not None
        assert failed.transaction_extraction_error.startswith(f"email {email.id}:")
    assert database.is_closed()


def test_operations_preserve_caller_owned_connection() -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        _email(1, template)
        replace_field_parsers(template.id, _parsers())
        reads.email_page(1)
        field_parser_snapshot(template.id)
        assert not database.is_closed()
        with pytest.raises(ValueError, match="unavailable"):
            replace_field_parsers(
                template.id,
                FieldParserSet(
                    amount=ExtractedFieldParser(rule="extracted", parameter_indices=[2])
                ),
            )
        assert not database.is_closed()
    assert database.is_closed()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: field_parser_snapshot(999),
        lambda: replace_field_parsers(999, FieldParserSet()),
        lambda: reads.email_page(1, queries.EmailTemplateFilter(999)),
    ],
)
def test_missing_template_closes_operation_owned_connection(
    operation: Callable[[], object],
) -> None:
    with pytest.raises(TemplateNotFoundError, match="Template not found"):
        operation()
    assert database.is_closed()


def test_extraction_loads_parser_configuration_once_per_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aggregator import transaction_extraction

    with database_connection():
        template = Template.create(text="Paid <NUMBER>")
        for index in range(4):
            _email(index, template)
    replace_field_parsers(template.id, _parsers())
    original = transaction_extraction.parser_sets
    calls = 0

    def tracked(
        templates: dict[int, Template], *, complete_only: bool = False
    ) -> dict[int, FieldParserSet]:
        nonlocal calls
        calls += 1
        return original(templates, complete_only=complete_only)

    monkeypatch.setattr(transaction_extraction, "parser_sets", tracked)
    assert extract_transactions().created == 4
    assert calls == 1
