"""Read labelled Gmail messages using Google Application Default Credentials.

This module intentionally only retrieves and normalizes messages. Callers own any
persistence, deduplication, or downstream processing.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote

import google.auth
from dotenv import load_dotenv
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import AuthorizedSession
from requests.exceptions import RequestException

GMAIL_MESSAGES_URL = "https://www.googleapis.com/gmail/v1/users/me/messages"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DOTENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class EmailPullError(Exception):
    """Base exception for Gmail pulling failures."""


class InvalidInputError(EmailPullError):
    """Raised when a public function argument is invalid."""


class ConfigurationError(EmailPullError):
    """Raised when required local Gmail configuration is missing."""


class CredentialsError(EmailPullError):
    """Raised when Application Default Credentials cannot be used."""


class GmailRequestError(EmailPullError):
    """Raised when a Gmail API request fails."""


class MalformedMessageError(EmailPullError):
    """Raised when Gmail returns a message that cannot be normalized."""


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """A normalized Gmail message, kept entirely in memory."""

    message_id: str
    history_id: str | None
    received_at: datetime
    sender: str
    subject: str | None
    body_text: str | None
    body_html: str | None
    headers: Mapping[str, str]
    authentication_status: str | None


def pull_messages(from_date: date | datetime) -> list[EmailMessage]:
    """Fetch configured-label Gmail messages received on or after ``from_date``."""
    label = _gmail_label()

    session = _authorized_session()
    try:
        message_ids = _fetch_message_ids(label, from_date, session)
        return [
            _normalize_message(_fetch_message(message_id, session)) for message_id in message_ids
        ]
    finally:
        session.close()


def _gmail_label() -> str:
    """Return the required Gmail label from the repository's local environment."""
    load_dotenv(dotenv_path=DOTENV_PATH)
    label = os.environ.get("GMAIL_LABEL", "").strip()
    if not label:
        raise ConfigurationError("GMAIL_LABEL must be configured with a non-empty Gmail label")
    return label


def _authorized_session() -> AuthorizedSession:
    try:
        credentials, _ = cast(
            tuple[Credentials, str | None],
            google.auth.default(scopes=[GMAIL_READONLY_SCOPE]),  # pyright: ignore[reportUnknownMemberType]
        )
        return AuthorizedSession(credentials)
    except DefaultCredentialsError as error:
        raise CredentialsError("Google Application Default Credentials are unavailable") from error


def _fetch_message_ids(
    label: str, from_date: date | datetime, session: AuthorizedSession
) -> list[str]:
    ids: list[str] = []
    page_token: str | None = None
    escaped_label = label.replace('"', '\\"')
    query = f'label:"{escaped_label}" after:{_format_date(from_date)}'

    while True:
        params: dict[str, str] = {"q": query}
        if page_token is not None:
            params["pageToken"] = page_token
        response = _request_json(session, GMAIL_MESSAGES_URL, params=params)
        raw_messages = response.get("messages", [])
        if not isinstance(raw_messages, list):
            raise MalformedMessageError("message listing has a non-list messages field")
        messages = cast(list[object], raw_messages)
        for item in messages:
            message = _as_object(item)
            if message is not None and isinstance(message.get("id"), str):
                ids.append(cast(str, message["id"]))

        next_page = response.get("nextPageToken")
        if not isinstance(next_page, str) or not next_page:
            return ids
        page_token = next_page


def _fetch_message(message_id: str, session: AuthorizedSession) -> dict[str, object]:
    return _request_json(
        session,
        f"{GMAIL_MESSAGES_URL}/{quote(message_id, safe='')}",
        params={"format": "full"},
    )


def _normalize_message(message: dict[str, object]) -> EmailMessage:
    gmail_message_id = message.get("id")
    payload = _as_object(message.get("payload"))
    internal_date = message.get("internalDate")
    if (
        not isinstance(gmail_message_id, str)
        or payload is None
        or not isinstance(internal_date, str)
    ):
        raise MalformedMessageError("message is missing id, payload, or internalDate")
    try:
        received_at = datetime.fromtimestamp(int(internal_date) / 1000, tz=UTC)
    except (OverflowError, ValueError) as error:
        raise MalformedMessageError("message internalDate is invalid") from error

    headers = _headers(payload)
    message_id = headers.get("message-id", "").strip()
    if not message_id:
        raise MalformedMessageError("message is missing a non-empty Message-ID header")
    body_text, body_html = _message_bodies(payload)
    history_id = message.get("historyId")
    return EmailMessage(
        message_id=message_id,
        history_id=history_id if isinstance(history_id, str) else None,
        received_at=received_at,
        sender=headers.get("from", ""),
        subject=headers.get("subject"),
        body_text=body_text,
        body_html=body_html,
        headers=headers,
        authentication_status=headers.get("authentication-results"),
    )


def _headers(payload: dict[str, object]) -> dict[str, str]:
    raw_headers = payload.get("headers", [])
    if not isinstance(raw_headers, list):
        raise MalformedMessageError("message headers are invalid")
    header_items = cast(list[object], raw_headers)
    return {
        name.lower(): value
        for header in header_items
        if (header_object := _as_object(header)) is not None
        and isinstance((name := header_object.get("name")), str)
        and isinstance((value := header_object.get("value")), str)
    }


def _message_bodies(payload: dict[str, object]) -> tuple[str | None, str | None]:
    text: str | None = None
    html: str | None = None
    for part in _payload_parts(payload):
        mime_type = part.get("mimeType")
        body = _decode_body(part)
        if mime_type == "text/plain" and text is None and body is not None:
            text = body
        elif mime_type == "text/html" and html is None and body is not None:
            html = body
    return text, html


def _payload_parts(payload: dict[str, object]) -> list[dict[str, object]]:
    parts = [payload]
    children = payload.get("parts")
    if isinstance(children, list):
        for child in cast(list[object], children):
            child_payload = _as_object(child)
            if child_payload is not None:
                parts.extend(_payload_parts(child_payload))
    return parts


def _decode_body(part: dict[str, object]) -> str | None:
    body = part.get("body")
    body_object = _as_object(body)
    if body_object is None or not isinstance((data := body_object.get("data")), str):
        return None
    try:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="replace")
    except ValueError:
        return None


def _format_date(value: date | datetime) -> str:
    date_value = value.date() if isinstance(value, datetime) else value
    return date_value.strftime("%Y/%m/%d")


def _request_json(
    session: AuthorizedSession,
    url: str,
    *,
    params: Mapping[str, str],
) -> dict[str, object]:
    try:
        response = session.get(url, params=params, timeout=30)
    except (RequestException, RefreshError) as error:
        raise GmailRequestError(f"Gmail request failed: {error}") from error

    if not 200 <= response.status_code < 300:
        raise GmailRequestError(
            f"Gmail returned HTTP {response.status_code}: {_error_body(response.content)}"
        )
    try:
        parsed: Any = json.loads(response.content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GmailRequestError("Gmail response was not valid JSON") from error
    response = _as_object(parsed)
    if response is None:
        raise GmailRequestError("Gmail response must be a JSON object")
    return response


def _error_body(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def _as_object(value: object) -> dict[str, object] | None:
    return cast(dict[str, object], value) if isinstance(value, dict) else None
