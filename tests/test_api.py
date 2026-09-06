from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownMemberType=false
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from playhouse.migrations import Runner

from aggregator import field_parsers
from aggregator.api import actions
from aggregator.api.app import app
from aggregator.api.parameter_serialization import indexed_parameter_responses
from aggregator.database import DATABASE_PATH, PROJECT_ROOT, close_database, database
from aggregator.email_pull import CredentialsError, GmailRequestError
from aggregator.email_sync import SyncResult
from aggregator.models import Email, FieldParser, Template, Transaction
from aggregator.parser_configuration import TRANSACTION_FIELD_NAMES, FieldParserSet
from aggregator.template_assignment import TemplateAssignmentResult
from aggregator.transaction_extraction import TransactionExtractionResult


@pytest.fixture(autouse=True)
def file_database(tmp_path: Path) -> Generator[None]:
    close_database()
    database.init(str(tmp_path / "api.sqlite3"))  # pyright: ignore[reportUnknownMemberType]
    database.connect()
    try:
        Runner(database, directory=str(PROJECT_ROOT / "migrations")).up()
        yield
    finally:
        close_database()
        database.init(str(DATABASE_PATH))  # pyright: ignore[reportUnknownMemberType]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_indexed_parameter_responses() -> None:
    assert indexed_parameter_responses([]) == []
    assert [
        parameter.model_dump()
        for parameter in indexed_parameter_responses([("NUMBER", "42"), ("CURRENCY_CODE", None)])
    ] == [
        {"index": 0, "mask_name": "NUMBER", "value": "42"},
        {"index": 1, "mask_name": "CURRENCY_CODE", "value": None},
    ]


def _email(index: int, *, template: Template | None = None) -> Email:
    return Email.create(
        message_id=f"message-{index}",
        received_at=datetime(2026, 9, 1, tzinfo=UTC) + timedelta(minutes=index),
        sender="sender@example.com",
        subject=f"Subject {index}",
        body_text="plain fallback",
        body_html="<h1>Hello</h1><script>secret()</script><p>World</p>",
        headers={"authorization": "secret"},
        authentication_status="sensitive",
        template=template,
    )


def test_email_pagination_and_safe_detail(client: TestClient) -> None:
    template = Template.create(text="receipt")
    for index in range(51):
        _email(index, template=template if index == 0 else None)

    response = client.get("/emails?page=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 51
    assert payload["page_size"] == 50
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 50
    assert payload["items"][0]["message_id"] == "message-50"
    assert set(payload["items"][0]) == {
        "id",
        "message_id",
        "received_at",
        "sender",
        "subject",
        "template_id",
        "representation",
    }
    assert payload["items"][0]["representation"] is None
    assert client.get("/emails?page=0").status_code == 422

    detail = client.get("/emails/1")
    assert detail.status_code == 200
    assert detail.json()["body"] == "Hello World"
    assert "headers" not in detail.json()
    assert "authentication_status" not in detail.json()
    assert client.get("/emails/999").status_code == 404


def test_email_template_filtering(client: TestClient) -> None:
    first = Template.create(text="first")
    second = Template.create(text="second")
    _email(1, template=first)
    _email(2, template=second)
    _email(3, template=first)
    _email(4)
    _email(5)

    filtered = client.get(f"/emails?template_id={first.id}")
    assert filtered.status_code == 200
    assert filtered.json() == {
        "items": [
            {
                "id": 3,
                "message_id": "message-3",
                "received_at": "2026-09-01T00:03:00Z",
                "sender": "sender@example.com",
                "subject": "Subject 3",
                "template_id": first.id,
                "representation": {
                    "template_text": "first",
                    "resolved_fields": dict.fromkeys(TRANSACTION_FIELD_NAMES),
                },
            },
            {
                "id": 1,
                "message_id": "message-1",
                "received_at": "2026-09-01T00:01:00Z",
                "sender": "sender@example.com",
                "subject": "Subject 1",
                "template_id": first.id,
                "representation": {
                    "template_text": "first",
                    "resolved_fields": dict.fromkeys(TRANSACTION_FIELD_NAMES),
                },
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 50,
        "total_pages": 1,
    }

    untagged = client.get("/emails?template_id=null")
    assert untagged.status_code == 200
    assert [item["message_id"] for item in untagged.json()["items"]] == [
        "message-5",
        "message-4",
    ]
    assert untagged.json()["total"] == 2
    assert all(item["representation"] is None for item in untagged.json()["items"])

    all_emails = client.get("/emails")
    assert all_emails.status_code == 200
    assert all_emails.json()["total"] == 5
    missing_template = client.get("/emails?template_id=999")
    assert missing_template.status_code == 404
    assert missing_template.json() == {"detail": "Template not found"}
    assert client.get("/emails?template_id=invalid").status_code == 422


def test_template_counts_and_missing_resource(client: TestClient) -> None:
    first = Template.create(text="first")
    second = Template.create(text="second")
    _email(1, template=first)
    _email(2, template=first)

    response = client.get("/templates")

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"] == [
        {"id": second.id, "text": "second", "email_count": 0},
        {"id": first.id, "text": "first", "email_count": 2},
    ]
    assert client.get("/templates/999").status_code == 404


def test_template_detail_includes_earliest_email_as_example(client: TestClient) -> None:
    template = Template.create(text="receipt")
    _email(2, template=template)
    _email(1, template=template)
    empty_template = Template.create(text="empty")

    response = client.get(f"/templates/{template.id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": template.id,
        "text": "receipt",
        "email_count": 2,
        "example": {
            "id": 2,
            "message_id": "message-1",
            "received_at": "2026-09-01T00:01:00Z",
            "sender": "sender@example.com",
            "subject": "Subject 1",
            "template_id": template.id,
            "body": "Hello World",
        },
    }
    assert client.get(f"/templates/{empty_template.id}").json()["example"] is None


def test_email_representation_shapes_for_index_and_detail(client: TestClient) -> None:
    template = Template.create(text="Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>")
    email = _email(1, template=template)
    email.body_html = "<p>Order #42 confirmed for $7.20</p>"
    email.save()

    detail_expected = {
        "template_text": "Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>",
        "extracted_parameters": [
            {"index": 0, "value": "42", "mask_name": "NUMBER"},
            {"index": 1, "value": "$", "mask_name": "CURRENCY_CODE"},
            {"index": 2, "value": "7.20", "mask_name": "NUMBER"},
        ],
    }

    index_item = client.get("/emails").json()["items"][0]
    detail = client.get(f"/emails/{email.id}")

    assert detail.status_code == 200
    assert index_item["representation"] == {
        "template_text": detail_expected["template_text"],
        "resolved_fields": dict.fromkeys(TRANSACTION_FIELD_NAMES),
    }
    assert detail.json()["representation"] == {
        **detail_expected,
        "resolved_fields": dict.fromkeys(TRANSACTION_FIELD_NAMES),
    }


def test_fixed_transaction_fields_require_no_catalog_table(client: TestClient) -> None:
    del client
    table_names = database.get_tables()
    assert "fields" not in table_names
    assert "field_parsers" in table_names


def test_field_parser_snapshot_and_atomic_replacement(client: TestClient) -> None:
    template = Template.create(text="Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>")
    email = _email(1, template=template)
    email.body_html = "<p>Order #42 confirmed for $7.20</p>"
    email.save()

    replacement = {
        "amount": {"rule": "extracted", "parameter_indices": [1, 2]},
        "currency_code": {"rule": "extracted", "parameter_indices": [1]},
        "payee": {"rule": "constant", "constant_value": "Example Shop"},
        "description": {"rule": "constant", "constant_value": "confirmed"},
        "transaction_date": {"rule": "missing"},
        "account_hint": {"rule": "missing"},
        "is_credit": {"rule": "extracted", "parameter_indices": [0]},
    }
    response = client.put(f"/templates/{template.id}/field-parsers", json=replacement)

    assert response.status_code == 200
    payload = response.json()
    assert payload["template_id"] == template.id
    assert payload["text"] == template.text
    assert payload["example_email_id"] == email.id
    assert payload["parameters"] == [
        {"index": 0, "mask_name": "NUMBER", "value": "42"},
        {"index": 1, "mask_name": "CURRENCY_CODE", "value": "$"},
        {"index": 2, "mask_name": "NUMBER", "value": "7.20"},
    ]
    assert payload["parsers"] == {**dict.fromkeys(TRANSACTION_FIELD_NAMES), **replacement}
    assert payload["preview"] == {
        "amount": "$ 7.20",
        "currency_code": "$",
        "payee": "Example Shop",
        "description": "confirmed",
        "transaction_date": None,
        "account_hint": None,
        "is_credit": "42",
    }

    invalid = client.put(
        f"/templates/{template.id}/field-parsers",
        json={"amount": {"rule": "extracted", "parameter_indices": [3]}},
    )
    assert invalid.status_code == 422
    assert client.get(f"/templates/{template.id}/field-parsers").json()["parsers"] == {
        **dict.fromkeys(TRANSACTION_FIELD_NAMES),
        **replacement,
    }

    cleared = client.put(f"/templates/{template.id}/field-parsers", json={})
    assert cleared.status_code == 200
    assert cleared.json()["parsers"] == dict.fromkeys(TRANSACTION_FIELD_NAMES)
    assert FieldParser.select().where(FieldParser.template == template).count() == 0


def test_field_parser_snapshot_without_example_and_request_validation(client: TestClient) -> None:
    template = Template.create(text="Paid <CURRENCY_CODE><NUMBER> on <DATE>")

    response = client.get(f"/templates/{template.id}/field-parsers")

    assert response.status_code == 200
    assert response.json()["parameters"] == [
        {"index": 0, "mask_name": "CURRENCY_CODE", "value": None},
        {"index": 1, "mask_name": "NUMBER", "value": None},
        {"index": 2, "mask_name": "DATE", "value": None},
    ]
    assert response.json()["preview"] is None
    assert client.get("/templates/999/field-parsers").status_code == 404
    assert client.put("/templates/999/field-parsers", json={}).status_code == 404

    malformed_payloads: list[dict[str, object]] = [
        {"unknown": {"rule": "missing"}},
        {"amount": {"rule": "missing", "constant_value": "extra"}},
        {"amount": {"rule": "constant"}},
        {"amount": {"rule": "extracted", "parameter_indices": []}},
        {"amount": {"rule": "extracted", "parameter_indices": [0, 0]}},
        {"amount": {"rule": "extracted", "parameter_indices": [-1]}},
        {"amount": {"rule": "extracted", "parameter_indices": [True]}},
    ]
    for payload in malformed_payloads:
        assert (
            client.put(f"/templates/{template.id}/field-parsers", json=payload).status_code == 422
        )


def test_generate_field_parsers_endpoint_replaces_and_previews(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = Template.create(
        text="Paid <CURRENCY_CODE><NUMBER>",
        transaction_extraction_status="failed",
        transaction_extraction_error="old failure",
    )
    email = _email(1, template=template)
    email.body_html = "<p>Paid $19</p>"
    email.save()
    FieldParser.create(
        template=template,
        field_name="payee",
        rule="constant",
        constant_value="Old Shop",
    )
    generated = FieldParserSet.model_validate(
        {
            "amount": {"rule": "extracted", "parameter_indices": [1]},
            "currency_code": {"rule": "extracted", "parameter_indices": [0]},
        }
    )

    def generate(*args: object) -> FieldParserSet:
        return generated

    monkeypatch.setattr(
        field_parsers.parser_generation,
        "generate_field_parsers",
        generate,
    )

    response = client.post(f"/templates/{template.id}/field-parsers/generate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["parsers"] == {
        **dict.fromkeys(TRANSACTION_FIELD_NAMES),
        "amount": {"rule": "extracted", "parameter_indices": [1]},
        "currency_code": {"rule": "extracted", "parameter_indices": [0]},
    }
    assert payload["preview"]["amount"] == "19"
    assert payload["preview"]["currency_code"] == "$"
    assert payload["transaction_extraction_status"] == "pending"
    assert payload["transaction_extraction_error"] is None


def test_generate_field_parsers_endpoint_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = Template.create(text="Paid <NUMBER>")
    _email(1, template=template)
    FieldParser.create(
        template=template,
        field_name="payee",
        rule="constant",
        constant_value="Old Shop",
    )
    calls = 0

    def fail_generation(*args: object) -> FieldParserSet:
        nonlocal calls
        calls += 1
        raise ConnectionError("provider unavailable")

    monkeypatch.setattr(field_parsers.parser_generation, "generate_field_parsers", fail_generation)

    failed = client.post(f"/templates/{template.id}/field-parsers/generate")
    missing = client.post("/templates/999/field-parsers/generate")

    assert failed.status_code == 502
    assert failed.json() == {"detail": "Field parser generation failed"}
    assert client.get(f"/templates/{template.id}/field-parsers").json()["parsers"]["payee"] == {
        "rule": "constant",
        "constant_value": "Old Shop",
    }
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Template not found"}
    assert calls == 1


def test_resolved_fields_are_consistent_for_index_and_detail(client: TestClient) -> None:
    template = Template.create(text="Paid <NUMBER>")
    email = _email(1, template=template)
    email.body_html = "<p>Paid 19</p>"
    email.save()
    response = client.put(
        f"/templates/{template.id}/field-parsers",
        json={
            "amount": {"rule": "extracted", "parameter_indices": [0]},
            "payee": {"rule": "constant", "constant_value": "Example Shop"},
        },
    )
    assert response.status_code == 200

    list_representation = client.get("/emails").json()["items"][0]["representation"]
    detail_representation = client.get(f"/emails/{email.id}").json()["representation"]

    expected = {
        **dict.fromkeys(TRANSACTION_FIELD_NAMES),
        "amount": "19",
        "payee": "Example Shop",
    }
    assert "extracted_parameters" not in list_representation
    assert list_representation["resolved_fields"] == expected
    assert detail_representation["resolved_fields"] == expected


def test_transaction_pagination_fields_and_email_representation(client: TestClient) -> None:
    template = Template.create(text="Paid <NUMBER>")
    represented_email = _email(0, template=template)
    represented_email.body_html = "<p>Paid 19</p>"
    represented_email.save()
    parser_response = client.put(
        f"/templates/{template.id}/field-parsers",
        json={
            "amount": {"rule": "extracted", "parameter_indices": [0]},
            "payee": {"rule": "constant", "constant_value": "Example Shop"},
        },
    )
    assert parser_response.status_code == 200
    represented_transaction = Transaction.create(
        email=represented_email,
        amount=Decimal("19.00"),
        currency_code="USD",
        payee="Example Shop",
        description="Purchase",
        transaction_date=date(2026, 9, 1),
        account_hint="1234",
        is_credit=False,
    )
    for index in range(1, 51):
        Transaction.create(email=_email(index))

    first_page = client.get("/transactions?page=1")

    assert first_page.status_code == 200
    payload = first_page.json()
    assert payload["total"] == 51
    assert payload["page"] == 1
    assert payload["page_size"] == 50
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 50
    assert payload["items"][0]["email_id"] == 51
    assert payload["items"][0]["representation"] is None
    assert set(payload["items"][0]) == {
        "id",
        "email_id",
        "amount",
        "currency_code",
        "payee",
        "description",
        "transaction_date",
        "account_hint",
        "is_credit",
        "representation",
    }

    second_page = client.get("/transactions?page=2")

    assert second_page.status_code == 200
    assert second_page.json() == {
        "items": [
            {
                "id": represented_transaction.id,
                "email_id": represented_email.id,
                "amount": "19.00",
                "currency_code": "USD",
                "payee": "Example Shop",
                "description": "Purchase",
                "transaction_date": "2026-09-01",
                "account_hint": "1234",
                "is_credit": False,
                "representation": {
                    "template_text": "Paid <NUMBER>",
                    "resolved_fields": {
                        **dict.fromkeys(TRANSACTION_FIELD_NAMES),
                        "amount": "19",
                        "payee": "Example Shop",
                    },
                },
            }
        ],
        "total": 51,
        "page": 2,
        "page_size": 50,
        "total_pages": 2,
    }
    assert "extracted_parameters" not in second_page.json()["items"][0]["representation"]
    assert client.get("/transactions?page=0").status_code == 422


def test_actions_validate_delegate_and_map_gmail_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def sync(label: str, from_date: object) -> SyncResult:
        captured.update(label=label, from_date=from_date)
        return SyncResult(pulled=3, inserted=2, already_stored=1)

    monkeypatch.setattr(actions, "sync_messages", sync)
    monkeypatch.setattr(
        actions,
        "assign_email_templates",
        lambda: TemplateAssignmentResult(processed=4, skipped=1, templates_created=1),
    )
    monkeypatch.setattr(
        actions,
        "extract_transactions",
        lambda: TransactionExtractionResult(
            pending=8,
            created=4,
            skipped=1,
            failed_templates=1,
            failed_emails=3,
        ),
    )

    sync_response = client.post(
        "/email-sync", json={"label": "Receipts", "from_date": "2026-09-01"}
    )
    assert sync_response.json() == {
        "pulled": 3,
        "inserted": 2,
        "already_stored": 1,
    }
    assert captured["label"] == "Receipts"
    assert client.post("/email-sync", json={"label": "Receipts"}).status_code == 422
    assert client.post("/email-template-assignment").json() == {
        "processed": 4,
        "skipped": 1,
        "templates_created": 1,
    }
    assert client.post("/transaction-extraction").json() == {
        "pending": 8,
        "created": 4,
        "skipped": 1,
        "failed_templates": 1,
        "failed_emails": 3,
    }

    def unavailable(_: str, __: object) -> SyncResult:
        raise CredentialsError("credentials unavailable")

    monkeypatch.setattr(actions, "sync_messages", unavailable)
    unavailable_response = client.post(
        "/email-sync", json={"label": "Receipts", "from_date": "2026-09-01"}
    )
    assert unavailable_response.status_code == 503

    def upstream(_: str, __: object) -> SyncResult:
        raise GmailRequestError("upstream unavailable")

    monkeypatch.setattr(actions, "sync_messages", upstream)
    upstream_response = client.post(
        "/email-sync", json={"label": "Receipts", "from_date": "2026-09-01"}
    )
    assert upstream_response.status_code == 502
