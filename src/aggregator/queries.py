"""Read-only database queries used by the HTTP surface."""

# Peewee query expressions and model primary-key descriptors are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from dataclasses import dataclass

from peewee import JOIN, fn

from .models import Email, Template, Transaction

PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class Page[ModelType: (Email, Template, Transaction)]:
    """A page of model instances plus its total count."""

    items: list[ModelType]
    total: int


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


def template_page(page: int) -> Page[Template]:
    """Return templates with aggregate email counts in fixed-size pages."""
    query = (
        Template.select(Template, fn.COUNT(Email.id).alias("email_count"))
        .join(Email, join_type=JOIN.LEFT_OUTER)
        .group_by(Template.id)
        .order_by(Template.id.desc())
    )
    return Page[Template](list(query.paginate(page, PAGE_SIZE)), query.count())


def template_by_id(template_id: int) -> Template | None:
    """Return one template annotated with its email count, if present."""
    query = (
        Template.select(Template, fn.COUNT(Email.id).alias("email_count"))
        .join(Email, join_type=JOIN.LEFT_OUTER)
        .where(Template.id == template_id)
        .group_by(Template.id)
    )
    return query.first()
