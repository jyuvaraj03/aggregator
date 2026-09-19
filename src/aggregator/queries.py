"""Persistence reads. Callers own the database connection."""

# Peewee query expressions and model primary-key descriptors are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import cast

from peewee import JOIN, fn

from .models import Email, FieldParser, Template, Transaction
from .parser_configuration import (
    TRANSACTION_FIELD_NAMES,
    ConstantFieldParser,
    ExtractedFieldParser,
    FieldParserConfiguration,
    FieldParserRule,
    FieldParserSet,
    MissingFieldParser,
    validate_field_name,
    validate_parameter_bounds,
    validate_parser_rule,
)
from .read_models import Page
from .template_syntax import template_parameter_count

PAGE_SIZE = 50


class TemplateNotFoundError(Exception):
    """The requested template does not exist."""


@dataclass(frozen=True, slots=True)
class EmailTemplateFilter:
    """An exact template filter, including the untagged-email case."""

    template_id: int | None


def email_page(page: int, template_filter: EmailTemplateFilter | None = None) -> Page[Email]:
    """Return emails newest first in fixed-size pages."""
    query = Email.select()
    if template_filter is not None:
        query = query.where(Email.template == template_filter.template_id)
    query = query.order_by(Email.received_at.desc(), Email.id.desc())
    return Page[Email](list(query.paginate(page, PAGE_SIZE)), query.count())


def email_by_id(email_id: int) -> Email | None:
    """Return one email, if present."""
    return Email.get_or_none(Email.id == email_id)


def transaction_page(page: int) -> Page[Transaction]:
    """Return transactions by newest associated email in fixed-size pages."""
    query = (
        Transaction.select(Transaction, Email)
        .join(Email)
        .order_by(Email.received_at.desc(), Email.id.desc())
    )
    return Page[Transaction](list(query.paginate(page, PAGE_SIZE)), query.count())


def template_page(
    page: int, classifications: Collection[bool | None] | None = None
) -> Page[Template]:
    """Return templates with aggregate email counts in fixed-size pages."""
    query = (
        Template.select(
            Template,
            fn.COUNT(fn.DISTINCT(Email.id)).alias("email_count"),
            fn.COUNT(fn.DISTINCT(FieldParser.id)).alias("field_parser_count"),
        )
        .join(Email, join_type=JOIN.LEFT_OUTER)
        .switch(Template)
        .join(FieldParser, join_type=JOIN.LEFT_OUTER)
    )
    if classifications is not None:
        classified_values = [value for value in classifications if value is not None]
        predicate = Template.is_transaction_alert.in_(classified_values)
        if None in classifications:
            predicate |= Template.is_transaction_alert.is_null()
        query = query.where(predicate)
    query = query.group_by(Template.id).order_by(Template.id.desc())
    return Page[Template](list(query.paginate(page, PAGE_SIZE)), query.count())


def template_by_id(template_id: int) -> Template | None:
    """Return one template annotated with its email count, if present."""
    query = (
        Template.select(
            Template,
            fn.COUNT(fn.DISTINCT(Email.id)).alias("email_count"),
            fn.COUNT(fn.DISTINCT(FieldParser.id)).alias("field_parser_count"),
        )
        .join(Email, join_type=JOIN.LEFT_OUTER)
        .switch(Template)
        .join(FieldParser, join_type=JOIN.LEFT_OUTER)
        .where(Template.id == template_id)
        .group_by(Template.id)
    )
    return query.first()


def require_template(template_id: int) -> Template:
    template = Template.get_or_none(Template.id == template_id)
    if template is None:
        raise TemplateNotFoundError("Template not found")
    return template


def example_email(template_id: int) -> Email | None:
    return (
        Email.select()
        .where(Email.template == template_id)
        .order_by(Email.received_at.asc(), Email.id.asc())
        .first()
    )


def templates_by_ids(template_ids: set[int]) -> dict[int, Template]:
    if not template_ids:
        return {}
    return {
        template.id: template for template in Template.select().where(Template.id.in_(template_ids))
    }


def parser_sets(
    templates: dict[int, Template], *, complete_only: bool = False
) -> dict[int, FieldParserSet]:
    """Load validated configurations; extraction can exclude incomplete sets."""
    if not templates:
        return {}
    counts = {
        template_id: template_parameter_count(template.text)
        for template_id, template in templates.items()
    }
    query = (
        FieldParser.select()
        .where(FieldParser.template.in_(list(templates)))
        .order_by(FieldParser.id)
    )
    rows = list(query)
    eligible_ids = set(templates)
    if complete_only:
        names: dict[int, set[str]] = {template_id: set() for template_id in templates}
        for parser in rows:
            names[parser.template_id].add(parser.field_name)
        eligible_ids = {
            template_id
            for template_id, field_names in names.items()
            if field_names == set(TRANSACTION_FIELD_NAMES)
        }
    values: dict[int, dict[str, FieldParserConfiguration]] = {
        template_id: {} for template_id in eligible_ids
    }
    for parser in rows:
        if parser.template_id not in eligible_ids:
            continue
        validate_field_name(parser.field_name)
        indices = cast(list[int], parser.parameter_indices)
        rule = validate_parser_rule(parser.rule, indices, parser.constant_value)
        validate_parameter_bounds(indices, counts[parser.template_id])
        if rule is FieldParserRule.EXTRACTED:
            configuration = ExtractedFieldParser(rule="extracted", parameter_indices=indices)
        elif rule is FieldParserRule.CONSTANT:
            configuration = ConstantFieldParser(
                rule="constant", constant_value=cast(str, parser.constant_value)
            )
        else:
            configuration = MissingFieldParser(rule="missing")
        values[parser.template_id][parser.field_name] = configuration
    return {
        template_id: FieldParserSet.model_validate(configurations)
        for template_id, configurations in values.items()
    }
