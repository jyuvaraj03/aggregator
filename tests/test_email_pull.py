from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from datetime import UTC, date, datetime

import pytest

from aggregator import email_pull


class FakeResponse:
    def __init__(self, status: int, body: dict[str, object]) -> None:
        self.status_code = status
        self.content = json.dumps(body).encode()


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Mapping[str, str]]] = []
        self.closed = False

    def get(self, url: str, *, params: Mapping[str, str], timeout: int) -> FakeResponse:
        assert timeout == 30
        self.calls.append((url, params))
        plain = base64.urlsafe_b64encode(b"receipt text").decode().rstrip("=")
        html = base64.urlsafe_b64encode(b"<p>receipt html</p>").decode().rstrip("=")
        if params.get("pageToken") == "next":
            return FakeResponse(200, {"messages": [{"id": "two"}]})
        if url == email_pull.GMAIL_MESSAGES_URL:
            return FakeResponse(200, {"messages": [{"id": "one"}], "nextPageToken": "next"})
        if url.endswith("/one"):
            return FakeResponse(
                200,
                {
                    "id": "one",
                    "historyId": "history",
                    "internalDate": "1704067200000",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "merchant@example.com"},
                            {"name": "Subject", "value": "Receipt"},
                            {"name": "mEsSaGe-Id", "value": "  <One@Example.COM>  "},
                        ],
                        "parts": [
                            {"mimeType": "text/plain", "body": {"data": plain}},
                            {
                                "mimeType": "multipart/alternative",
                                "parts": [{"mimeType": "text/html", "body": {"data": html}}],
                            },
                        ],
                    },
                },
            )
        return FakeResponse(
            200,
            {
                "id": "two",
                "internalDate": "1704153600000",
                "payload": {"headers": [{"name": "Message-ID", "value": "<two@example.com>"}]},
            },
        )

    def close(self) -> None:
        self.closed = True


def test_pull_messages_without_label_config_paginates_and_normalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    monkeypatch.delenv("GMAIL_LABEL", raising=False)
    monkeypatch.setattr(email_pull, "_authorized_session", lambda: session)
    messages = email_pull.pull_messages(date(2024, 1, 1))

    assert [message.message_id for message in messages] == [
        "<One@Example.COM>",
        "<two@example.com>",
    ]
    assert messages[0].received_at == datetime(2024, 1, 1, tzinfo=UTC)
    assert messages[0].sender == "merchant@example.com"
    assert messages[0].subject == "Receipt"
    assert messages[0].body == "receipt html"
    assert messages[1].body == ""
    assert session.calls[0][1]["q"] == (
        "after:2024/01/01 -category:promotions -category:social -category:forums"
    )
    assert session.closed


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [{"name": "Message-ID", "value": ""}],
        [{"name": "message-id", "value": "   \t"}],
    ],
)
def test_normalize_message_rejects_missing_or_blank_rfc_message_id(
    monkeypatch: pytest.MonkeyPatch,
    headers: list[dict[str, str]],
) -> None:
    class MalformedMessageSession(FakeSession):
        def get(self, url: str, *, params: Mapping[str, str], timeout: int) -> FakeResponse:
            if url == email_pull.GMAIL_MESSAGES_URL:
                return FakeResponse(200, {"messages": [{"id": "gmail-resource-id"}]})
            return FakeResponse(
                200,
                {
                    "id": "gmail-resource-id",
                    "internalDate": "1704067200000",
                    "payload": {"headers": headers},
                },
            )

    session = MalformedMessageSession()
    monkeypatch.setattr(email_pull, "_authorized_session", lambda: session)

    with pytest.raises(email_pull.MalformedMessageError, match="Message-ID"):
        email_pull.pull_messages(date(2024, 1, 1))

    assert session.closed
