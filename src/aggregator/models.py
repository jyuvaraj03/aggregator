"""Peewee models for persisted aggregator records."""

# Peewee's model query methods are intentionally dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

import json
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, cast

from bs4 import BeautifulSoup
from peewee import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    ForeignKeyField,
    Model,
    TextField,
)

from .database import database
from .template_mining import template_parameter_count

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


class FieldParserRule(StrEnum):
    EXTRACTED = "extracted"
    CONSTANT = "constant"
    MISSING = "missing"


class TransactionFieldName(StrEnum):
    """The fixed transaction fields exposed by the parser configuration API."""

    AMOUNT = "amount"
    CURRENCY_CODE = "currency_code"
    PAYEE = "payee"
    DESCRIPTION = "description"
    TRANSACTION_DATE = "transaction_date"
    ACCOUNT_HINT = "account_hint"
    IS_CREDIT = "is_credit"


TRANSACTION_FIELD_NAMES = tuple(field.value for field in TransactionFieldName)


class TransactionExtractionStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Template(Model):
    """A Drain3 pattern extracted from one or more email bodies."""

    text = TextField()
    transaction_extraction_status = CharField(default=TransactionExtractionStatus.PENDING.value)
    transaction_extraction_error = TextField(null=True)

    def example_email(self) -> Email | None:
        """Return the earliest email assigned to this template, if any."""
        return self.emails.order_by(Email.received_at.asc(), Email.id.asc()).first()

    class Meta:
        database = database
        table_name = "templates"


class FieldParser(Model):
    """One template-specific rule for resolving a fixed transaction field."""

    template = ForeignKeyField(Template, backref="field_parsers", on_delete="CASCADE")
    field_name = CharField()
    rule = CharField()
    parameter_indices = JSONIntegerListField(default=list)
    constant_value = TextField(null=True)

    def validate(self) -> None:
        """Reject rule payloads that cannot be resolved for this template."""
        try:
            TransactionFieldName(self.field_name)
        except ValueError as error:
            raise ValueError(f"Unsupported transaction field name: {self.field_name!r}") from error

        try:
            rule = FieldParserRule(self.rule)
        except ValueError as error:
            raise ValueError(f"Unsupported field parser rule: {self.rule!r}") from error

        indices = cast(list[int], self.parameter_indices)
        if rule is FieldParserRule.EXTRACTED:
            if not indices:
                raise ValueError("An extracted field parser requires at least one parameter index")
            if len(indices) != len(set(indices)):
                raise ValueError(
                    "An extracted field parser cannot contain duplicate parameter indices"
                )
            if any(index < 0 for index in indices):
                raise ValueError(
                    "An extracted field parser cannot contain negative parameter indices"
                )
            parameter_count = template_parameter_count(self.template.text)
            if any(index >= parameter_count for index in indices):
                raise ValueError(
                    "An extracted field parser references an unavailable parameter index"
                )
            if self.constant_value is not None:
                raise ValueError("An extracted field parser cannot have a constant value")
            return

        if indices:
            raise ValueError(f"A {rule.value} field parser cannot have parameter indices")
        if rule is FieldParserRule.CONSTANT:
            if self.constant_value is None:
                raise ValueError("A constant field parser requires a constant value")
            return
        if self.constant_value is not None:
            raise ValueError("A missing field parser cannot have a constant value")

    def save(self, *args: object, **kwargs: object) -> int:
        self.validate()
        return super().save(*args, **kwargs)  # pyright: ignore[reportArgumentType, reportUnknownMemberType]

    class Meta:
        database = database
        table_name = "field_parsers"
        indexes = ((("template", "field_name"), True),)


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


class Transaction(Model):
    """Typed transaction fields extracted from one email."""

    email = ForeignKeyField(Email, backref="transaction", unique=True, on_delete="CASCADE")
    amount = DecimalTextField(null=True)
    currency_code = TextField(null=True)
    payee = TextField(null=True)
    description = TextField(null=True)
    transaction_date = DateField(null=True)
    account_hint = TextField(null=True)
    is_credit = BooleanField(null=True)

    class Meta:
        database = database
        table_name = "transactions"
