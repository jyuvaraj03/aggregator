"""Peewee models for persisted aggregator records."""

# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json

from bs4 import BeautifulSoup
from peewee import CharField, DateTimeField, Model, TextField

from .database import database


class JSONTextField(TextField):
    """Store JSON in SQLite while exposing it as a dictionary in Python."""

    def db_value(self, value: object) -> str:
        return json.dumps(value)

    def python_value(self, value: object) -> dict[str, str]:
        if isinstance(value, str):
            decoded = json.loads(value)
            if isinstance(decoded, dict):
                return {str(key): str(item) for key, item in decoded.items()}
        return {}


class Email(Model):
    """An immutable snapshot of a Gmail message imported by the synchronizer."""

    message_id = CharField(unique=True)
    history_id = CharField(null=True)
    received_at = DateTimeField()
    sender = TextField()
    subject = TextField(null=True)
    body_text = TextField(null=True)
    body_html = TextField(null=True)
    headers = JSONTextField()
    authentication_status = TextField(null=True)

    def readable_body(self) -> str:
        soup = BeautifulSoup(self.body_html or "", "html.parser")
        return soup.get_text("\n", strip=True)

    class Meta:
        database = database
        table_name = "emails"
