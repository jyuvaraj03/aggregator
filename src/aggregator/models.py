"""Peewee models for persisted aggregator records."""

# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, cast

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    ForeignKeyField,
    Model,
    TextField,
)

from .database import database
from .parser_configuration import (
    validate_field_name,
    validate_parameter_bounds,
    validate_parser_rule,
)
from .template_syntax import template_parameter_count


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


class JSONIntegerListField(TextField):
    """Store an ordered list of integer values as JSON in SQLite."""

    def db_value(self, value: object) -> str:
        if not isinstance(value, (list, tuple)) or any(type(item) is not int for item in value):
            raise TypeError("Expected a list of integers")
        return json.dumps(list(value))

    def python_value(self, value: object) -> list[int]:
        if isinstance(value, str):
            decoded = json.loads(value)
        else:
            decoded = value
        if isinstance(decoded, list) and all(type(item) is int for item in decoded):
            return decoded
        raise ValueError("Expected a JSON list of integers")


class DecimalTextField(TextField):
    """Persist decimal values losslessly while exposing ``Decimal`` in Python."""

    def db_value(self, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, Decimal):
            raise TypeError("Expected a Decimal value")
        return str(value)

    def python_value(self, value: object) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))


class TransactionExtractionStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Account(Model):
    """An independently managed financial account."""

    id = AutoField()
    name = TextField(unique=True)

    class Meta:
        database = database
        table_name = "accounts"


class Template(Model):
    """A Drain3 pattern extracted from one or more email bodies."""

    id = AutoField()
    text = TextField()
    transaction_extraction_status = CharField(default=TransactionExtractionStatus.PENDING.value)
    transaction_extraction_error = TextField(null=True)

    class Meta:
        database = database
        table_name = "templates"


class FieldParser(Model):
    """One template-specific rule for resolving a fixed transaction field."""

    id = AutoField()
    template = ForeignKeyField(Template, backref="field_parsers", on_delete="CASCADE")
    field_name = CharField()
    rule = CharField()
    parameter_indices = JSONIntegerListField(default=list)
    constant_value = TextField(null=True)

    def validate(self) -> None:
        """Reject rule payloads that cannot be resolved for this template."""
        validate_field_name(self.field_name)
        indices = cast(list[int], self.parameter_indices)
        validate_parser_rule(self.rule, indices, self.constant_value)
        validate_parameter_bounds(indices, template_parameter_count(self.template.text))

    def save(self, *args: object, **kwargs: object) -> int:
        self.validate()
        return super().save(*args, **kwargs)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]

    class Meta:
        database = database
        table_name = "field_parsers"
        indexes = ((("template", "field_name"), True),)


class Email(Model):
    """An immutable snapshot of a Gmail message imported by the synchronizer."""

    id = AutoField()
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

    if TYPE_CHECKING:
        # Peewee creates this raw foreign-key accessor dynamically.
        template_id: int | None

    class Meta:
        database = database
        table_name = "emails"


class Transaction(Model):
    """Typed transaction fields extracted from one email."""

    id = AutoField()
    email = ForeignKeyField(Email, backref="transaction", unique=True, on_delete="CASCADE")
    amount = DecimalTextField(null=True)
    currency_code = TextField(null=True)
    payee = TextField(null=True)
    description = TextField(null=True)
    transaction_date = DateField(null=True)
    account_hint = TextField(null=True)
    is_credit = BooleanField(null=True)

    if TYPE_CHECKING:
        email_id: int

    class Meta:
        database = database
        table_name = "transactions"
