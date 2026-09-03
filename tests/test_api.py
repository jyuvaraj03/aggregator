from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownMemberType=false
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from playhouse.migrations import Runner

from aggregator.api import actions
from aggregator.api.app import app
from aggregator.database import DATABASE_PATH, PROJECT_ROOT, close_database, database
from aggregator.email_pull import CredentialsError, GmailRequestError
from aggregator.email_sync import SyncResult
from aggregator.models import Email, Template
from aggregator.template_mining import TemplateMiningResult


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
    }
    assert client.get("/emails?page=0").status_code == 422

    detail = client.get("/emails/1")
    assert detail.status_code == 200
    assert detail.json()["body"] == "Hello\nWorld"
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
            },
            {
                "id": 1,
                "message_id": "message-1",
                "received_at": "2026-09-01T00:01:00Z",
                "sender": "sender@example.com",
                "subject": "Subject 1",
                "template_id": first.id,
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
        "mine_untagged_templates",
        lambda: TemplateMiningResult(processed=4, skipped=1, templates_created=1),
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
    assert client.post("/email-template-mining").json() == {
        "processed": 4,
        "skipped": 1,
        "templates_created": 1,
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
