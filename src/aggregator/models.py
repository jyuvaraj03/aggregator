"""Peewee models for persisted aggregator records."""

# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from peewee import CharField, DateTimeField, ForeignKeyField, Model, TextField

from .database import database

if TYPE_CHECKING:
    from .template_representation import TemplateRepresentation


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


class Template(Model):
    """A Drain3 pattern extracted from one or more email bodies."""

    text = TextField()

    def example_email(self) -> Email | None:
        """Return the earliest email assigned to this template, if any."""
        return self.emails.order_by(Email.received_at.asc(), Email.id.asc()).first()

    class Meta:
        database = database
        table_name = "templates"


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
    template = ForeignKeyField(Template, null=True, backref="emails", on_delete="SET NULL")

    def readable_body(self) -> str:
        soup = BeautifulSoup(self.body_html or "", "html.parser")
        return " ".join(soup.get_text("\n", strip=True).split())

    def representation(self) -> TemplateRepresentation | None:
        """Return this email's template and values, if it has been assigned."""
        if self.template_id is None:
            return None

        # Delaying this import keeps the ORM model and representation helper
        # independent at import time.
        from .template_representation import represent_email_template

        return represent_email_template(self)

    class Meta:
        database = database
        table_name = "emails"
