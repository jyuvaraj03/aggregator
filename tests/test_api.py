from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from playhouse.migrations import Runner

from aggregator import field_parsers
from aggregator.api import actions
from aggregator.api import field_parsers as field_parser_routes
from aggregator.api.app import app
from aggregator.api.parameter_serialization import indexed_parameter_responses
from aggregator.database import DATABASE_PATH, PROJECT_ROOT, close_database, database
from aggregator.models import Account, Email, FieldParser, Template, Transaction
from aggregator.parser_configuration import TRANSACTION_FIELD_NAMES, FieldParserSet


class _QueuedJob:
    def __init__(self, job_id: str = "job-123") -> None:
        self.id = job_id


@pytest.fixture(autouse=True)
def queue_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(actions.sync_email_task, "delay", lambda *_: _QueuedJob("sync-job"))
    monkeypatch.setattr(
        actions.extract_transactions_task, "delay", lambda: _QueuedJob("extraction-job")
    )
    monkeypatch.setattr(
        field_parser_routes.generate_field_parsers_task,
        "delay",
        lambda _: _QueuedJob("generation-job"),
    )


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


def test_account_creation_trims_name_and_rejects_invalid_names(client: TestClient) -> None:
    response = client.post("/accounts", json={"name": "  Checking  "})

    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Checking"}
    assert Account.get_by_id(1).name == "Checking"
    assert client.post("/accounts", json={"name": " \t\n "}).status_code == 422
    assert client.post("/accounts", json={}).status_code == 422


def test_account_uniqueness_is_exact_case_and_conflicts_return_409(client: TestClient) -> None:
    assert client.post("/accounts", json={"name": "Savings"}).status_code == 201

    duplicate = client.post("/accounts", json={"name": " Savings "})
    distinct_case = client.post("/accounts", json={"name": "savings"})

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Account name already exists"}
    assert distinct_case.status_code == 201
    assert distinct_case.json()["name"] == "savings"


def test_account_detail_pagination_and_invalid_page(client: TestClient) -> None:
    for index in range(51):
        Account.create(name=f"Account {index}")

    first_page = client.get("/accounts?page=1")

    assert first_page.status_code == 200
    payload = first_page.json()
    assert payload["total"] == 51
    assert payload["page"] == 1
    assert payload["page_size"] == 50
    assert payload["total_pages"] == 2
    assert len(payload["items"]) == 50
    assert payload["items"][0] == {"id": 51, "name": "Account 50"}
    assert client.get("/accounts?page=2").json()["items"] == [{"id": 1, "name": "Account 0"}]
    assert client.get("/accounts?page=0").status_code == 422
    assert client.get("/accounts?page=invalid").status_code == 422
    assert client.get("/accounts/1").json() == {"id": 1, "name": "Account 0"}
    assert client.get("/accounts/999").status_code == 404


def test_account_rename_and_missing_update(client: TestClient) -> None:
    first = Account.create(name="First")
    Account.create(name="Second")

    renamed = client.patch(f"/accounts/{first.id}", json={"name": "  Primary  "})

    assert renamed.status_code == 200
    assert renamed.json() == {"id": first.id, "name": "Primary"}
    assert client.patch(f"/accounts/{first.id}", json={"name": "Primary"}).status_code == 200
    assert client.patch(f"/accounts/{first.id}", json={"name": "Second"}).status_code == 409
    assert client.patch(f"/accounts/{first.id}", json={"name": "  "}).status_code == 422
    assert client.patch("/accounts/999", json={"name": "Missing"}).status_code == 404


def test_account_delete_returns_empty_204_and_missing_resource(client: TestClient) -> None:
    account = Account.create(name="Disposable")

    response = client.delete(f"/accounts/{account.id}")

    assert response.status_code == 204
    assert response.content == b""
    assert Account.get_or_none(Account.id == account.id) is None
    assert client.delete(f"/accounts/{account.id}").status_code == 404


def _email(index: int, *, template: Template | None = None) -> Email:
    return Email.create(
        message_id=f"message-{index}",
        received_at=datetime(2026, 9, 1, tzinfo=UTC) + timedelta(minutes=index),
        sender="sender@example.com",
        subject=f"Subject {index}",
        body="Hello World",
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
        {
            "id": second.id,
            "text": "second",
            "is_transaction_alert": None,
            "email_count": 0,
            "account_id": None,
            "field_parser_status": None,
        },
        {
            "id": first.id,
            "text": "first",
            "is_transaction_alert": None,
            "email_count": 2,
            "account_id": None,
            "field_parser_status": None,
        },
    ]
    assert client.get("/templates/999").status_code == 404


@pytest.mark.parametrize(
    "classifications",
    [
        None,
        ("transaction_alert",),
        ("unclassified",),
        ("not_transaction_alert",),
        ("transaction_alert", "unclassified"),
        ("transaction_alert", "not_transaction_alert"),
        ("unclassified", "not_transaction_alert"),
        ("transaction_alert", "unclassified", "not_transaction_alert"),
    ],
    ids=[
        "omitted",
        "transaction-alert",
        "unclassified",
        "not-transaction-alert",
        "alerts-and-unclassified",
        "classified",
        "not-alert-or-unclassified",
        "all-values",
    ],
)
def test_template_classification_filters_totals_ordering_and_pagination(
    client: TestClient, classifications: tuple[str, ...] | None
) -> None:
    values = {
        "transaction_alert": True,
        "unclassified": None,
        "not_transaction_alert": False,
    }
    template_ids: dict[bool | None, list[int]] = {True: [], None: [], False: []}
    for classification in (True, None, False):
        for index in range(26):
            template = Template.create(
                text=f"{classification}-{index}", is_transaction_alert=classification
            )
            template_ids[classification].append(template.id)

    expected_values = (
        set(template_ids)
        if classifications is None
        else {values[value] for value in classifications}
    )
    expected_ids = sorted(
        (template_id for value in expected_values for template_id in template_ids[value]),
        reverse=True,
    )
    params = (
        []
        if classifications is None
        else [("classification", classification) for classification in classifications]
    )

    first_page = client.get("/templates", params=[*params, ("page", "1")])

    assert first_page.status_code == 200
    assert first_page.json()["total"] == len(expected_ids)
    assert first_page.json()["total_pages"] == (len(expected_ids) + 49) // 50
    assert [item["id"] for item in first_page.json()["items"]] == expected_ids[:50]
    assert {item["is_transaction_alert"] for item in first_page.json()["items"]}.issubset(
        expected_values
    )

    if len(expected_ids) > 50:
        second_page = client.get("/templates", params=[*params, ("page", "2")])
        assert second_page.status_code == 200
        assert second_page.json()["total"] == len(expected_ids)
        assert [item["id"] for item in second_page.json()["items"]] == expected_ids[50:]


@pytest.mark.parametrize("classification", ["transaction", "true", ""])
def test_template_classification_filter_rejects_invalid_values(
    client: TestClient, classification: str
) -> None:
    assert client.get("/templates", params={"classification": classification}).status_code == 422


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
        "is_transaction_alert": None,
        "email_count": 2,
        "account_id": None,
        "field_parser_status": None,
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


def test_template_account_assignment_reassignment_and_unassignment(client: TestClient) -> None:
    first_account = Account.create(name="Checking")
    second_account = Account.create(name="Savings")
    selected = Template.create(text="selected")
    untouched = Template.create(text="untouched")
    selected_transactions = [
        Transaction.create(email=_email(index, template=selected)) for index in range(2)
    ]
    untouched_transaction = Transaction.create(email=_email(3, template=untouched))

    assigned = client.put(
        f"/templates/{selected.id}/account", json={"account_id": first_account.id}
    )

    assert assigned.status_code == 200
    assert assigned.json() == {
        "id": selected.id,
        "text": "selected",
        "is_transaction_alert": None,
        "email_count": 2,
        "account_id": first_account.id,
        "field_parser_status": None,
    }
    assert Template.get_by_id(selected.id).account_id == first_account.id
    assert {
        Transaction.get_by_id(transaction.id).account_id for transaction in selected_transactions
    } == {first_account.id}
    assert Template.get_by_id(untouched.id).account_id is None
    assert Transaction.get_by_id(untouched_transaction.id).account_id is None

    assert (
        client.put(
            f"/templates/{selected.id}/account", json={"account_id": first_account.id}
        ).status_code
        == 200
    )
    reassigned = client.put(
        f"/templates/{selected.id}/account", json={"account_id": second_account.id}
    )
    assert reassigned.json()["account_id"] == second_account.id
    assert {
        Transaction.get_by_id(transaction.id).account_id for transaction in selected_transactions
    } == {second_account.id}

    unassigned = client.put(f"/templates/{selected.id}/account", json={"account_id": None})
    assert unassigned.status_code == 200
    assert unassigned.json()["account_id"] is None
    assert all(
        Transaction.get_by_id(transaction.id).account_id is None
        for transaction in selected_transactions
    )


def test_template_account_assignment_validates_before_updating(client: TestClient) -> None:
    account = Account.create(name="Checking")
    template = Template.create(text="receipt", account=account)
    transaction = Transaction.create(email=_email(1, template=template), account=account)

    missing_account = client.put(f"/templates/{template.id}/account", json={"account_id": 999})
    missing_template = client.put("/templates/999/account", json={"account_id": account.id})

    assert missing_account.status_code == 404
    assert missing_account.json() == {"detail": "Account not found"}
    assert missing_template.status_code == 404
    assert missing_template.json() == {"detail": "Template not found"}
    assert Template.get_by_id(template.id).account_id == account.id
    assert Transaction.get_by_id(transaction.id).account_id == account.id
    for payload in ({}, {"account_id": "1"}, {"account_id": True}, {"extra": None}):
        assert client.put(f"/templates/{template.id}/account", json=payload).status_code == 422


def test_account_deletion_cascades_transactions_and_preserves_templates(
    client: TestClient,
) -> None:
    deleted_account = Account.create(name="Deleted")
    other_account = Account.create(name="Other")
    deleted_template = Template.create(text="receipt", account=deleted_account)
    other_template = Template.create(text="other", account=other_account)
    deleted_email = _email(1, template=deleted_template)
    other_email = _email(2, template=other_template)
    deleted_transaction = Transaction.create(email=deleted_email, account=deleted_account)
    other_transaction = Transaction.create(email=other_email, account=other_account)

    response = client.delete(f"/accounts/{deleted_account.id}")

    assert response.status_code == 204
    assert Template.get_by_id(deleted_template.id).account_id is None
    assert Template.get_by_id(other_template.id).account_id == other_account.id
    assert Transaction.get_or_none(Transaction.id == deleted_transaction.id) is None
    assert Transaction.get_by_id(other_transaction.id).account_id == other_account.id

    parser_response = client.put(
        f"/templates/{deleted_template.id}/field-parsers",
        json={
            **{name: {"rule": "missing"} for name in TRANSACTION_FIELD_NAMES},
            "amount": {"rule": "constant", "constant_value": "10"},
        },
    )
    assert parser_response.status_code == 200
    assert client.post("/transaction-extraction").status_code == 202
    client.put(f"/templates/{deleted_template.id}/account", json={"account_id": other_account.id})
    assert client.post("/transaction-extraction").status_code == 202
    assert Transaction.get_or_none(Transaction.email == deleted_email) is None


def test_email_representation_shapes_for_index_and_detail(client: TestClient) -> None:
    template = Template.create(text="Order #<NUMBER> confirmed for <CURRENCY_CODE><NUMBER>")
    email = _email(1, template=template)
    email.body = "Order #42 confirmed for $7.20"
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
    email.body = "Order #42 confirmed for $7.20"
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


def test_field_parser_approval_and_status_lifecycle(client: TestClient) -> None:
    template = Template.create(
        text="Paid <NUMBER>",
        is_transaction_alert=True,
        transaction_extraction_status="failed",
        transaction_extraction_error="old failure",
    )
    email = _email(1, template=template)
    email.body = "Paid 19"
    email.save()
    parsers = {
        **{name: {"rule": "missing"} for name in TRANSACTION_FIELD_NAMES},
        "amount": {"rule": "extracted", "parameter_indices": [0]},
    }

    assert client.get(f"/templates/{template.id}").json()["field_parser_status"] == (
        "needs_generation"
    )
    saved = client.put(f"/templates/{template.id}/field-parsers", json=parsers)

    assert saved.status_code == 200
    assert saved.json()["field_parser_status"] == "needs_review"
    assert client.get("/templates").json()["items"][0]["field_parser_status"] == "needs_review"

    approved = client.post(f"/templates/{template.id}/field-parsers/approve")

    assert approved.status_code == 200
    assert approved.json()["field_parser_status"] == "approved"
    refreshed = Template.get_by_id(template.id)
    assert refreshed.field_parsers_approved is True
    assert refreshed.transaction_extraction_status == "pending"
    assert refreshed.transaction_extraction_error is None
    assert client.get(f"/templates/{template.id}").json()["field_parser_status"] == "approved"

    resaved = client.put(f"/templates/{template.id}/field-parsers", json=parsers)
    assert resaved.json()["field_parser_status"] == "needs_review"
    assert Template.get_by_id(template.id).field_parsers_approved is False


def test_field_parser_approval_rejects_ineligible_drafts(client: TestClient) -> None:
    non_alert = Template.create(text="Paid <NUMBER>", is_transaction_alert=False)
    incomplete = Template.create(text="Paid <NUMBER>", is_transaction_alert=True)
    _email(1, template=incomplete)
    no_example = Template.create(text="Receipt", is_transaction_alert=True)
    invalid = Template.create(text="Paid <*>", is_transaction_alert=True)
    invalid_email = _email(2, template=invalid)
    invalid_email.body = "Paid $20"
    invalid_email.save()
    complete_missing = {name: {"rule": "missing"} for name in TRANSACTION_FIELD_NAMES}
    assert (
        client.put(f"/templates/{no_example.id}/field-parsers", json=complete_missing).status_code
        == 200
    )
    assert (
        client.put(
            f"/templates/{invalid.id}/field-parsers",
            json={
                **complete_missing,
                "amount": {"rule": "extracted", "parameter_indices": [0]},
            },
        ).status_code
        == 200
    )

    not_alert_response = client.post(f"/templates/{non_alert.id}/field-parsers/approve")
    incomplete_response = client.post(f"/templates/{incomplete.id}/field-parsers/approve")
    no_example_response = client.post(f"/templates/{no_example.id}/field-parsers/approve")
    invalid_response = client.post(f"/templates/{invalid.id}/field-parsers/approve")

    assert not_alert_response.status_code == 409
    assert incomplete_response.status_code == 409
    assert no_example_response.status_code == 409
    assert invalid_response.status_code == 422
    assert "invalid amount" in invalid_response.json()["detail"]
    assert client.post("/templates/999/field-parsers/approve").status_code == 404


def test_generate_field_parsers_endpoint_replaces_and_previews(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = Template.create(
        text="Paid <CURRENCY_CODE><NUMBER>",
        is_transaction_alert=True,
        transaction_extraction_status="failed",
        transaction_extraction_error="old failure",
    )
    email = _email(1, template=template)
    email.body = "Paid $19"
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

    assert response.status_code == 202
    assert response.headers["location"] == "/jobs/generation-job"
    assert response.json() == {"job_id": "generation-job", "status_url": "/jobs/generation-job"}
    assert FieldParser.get(FieldParser.template == template).constant_value == "Old Shop"


def test_generate_field_parsers_endpoint_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = Template.create(text="Paid <NUMBER>", is_transaction_alert=True)
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

    assert failed.status_code == 202
    assert client.get(f"/templates/{template.id}/field-parsers").json()["parsers"]["payee"] == {
        "rule": "constant",
        "constant_value": "Old Shop",
    }
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Template not found"}
    assert calls == 0


@pytest.mark.parametrize("classification", [False, None])
def test_generate_field_parsers_endpoint_rejects_ineligible_templates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    classification: bool | None,
) -> None:
    template = Template.create(text="Paid <NUMBER>", is_transaction_alert=classification)
    queued = False

    def queue(_: int) -> _QueuedJob:
        nonlocal queued
        queued = True
        return _QueuedJob()

    monkeypatch.setattr(field_parser_routes.generate_field_parsers_task, "delay", queue)

    response = client.post(f"/templates/{template.id}/field-parsers/generate")

    assert response.status_code == 409
    assert response.json() == {"detail": "Template is not classified as a transaction alert"}
    assert queued is False


def test_resolved_fields_are_consistent_for_index_and_detail(client: TestClient) -> None:
    template = Template.create(text="Paid <NUMBER>")
    email = _email(1, template=template)
    email.body = "Paid 19"
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
    represented_email.body = "Paid 19"
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
        "account_id",
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
                "account_id": None,
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


def test_actions_enqueue_background_jobs(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def sync(from_date: str) -> _QueuedJob:
        captured.update(from_date=from_date)
        return _QueuedJob("submitted-sync")

    monkeypatch.setattr(actions.sync_email_task, "delay", sync)

    sync_response = client.post("/email-sync", json={"from_date": "2026-09-01"})
    assert sync_response.status_code == 202
    assert sync_response.headers["location"] == "/jobs/submitted-sync"
    assert sync_response.json() == {
        "job_id": "submitted-sync",
        "status_url": "/jobs/submitted-sync",
    }
    assert captured["from_date"] == "2026-09-01"
    assert client.post("/email-sync", json={}).status_code == 422
    sync_schema = app.openapi()["components"]["schemas"]["EmailSyncRequest"]
    assert "label" not in sync_schema["properties"]
    assert set(sync_schema["required"]) == {"from_date"}
    assert client.post("/email-template-assignment").status_code == 404
    assert client.post("/transaction-extraction").json()["job_id"] == "extraction-job"

    def unavailable(*_: object) -> _QueuedJob:
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(actions.sync_email_task, "delay", unavailable)
    unavailable_response = client.post("/email-sync", json={"from_date": "2026-09-01"})
    assert unavailable_response.status_code == 503
