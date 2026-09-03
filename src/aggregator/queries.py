"""Read-only database queries used by the HTTP surface."""

# Peewee query expressions and model primary-key descriptors are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from dataclasses import dataclass

from peewee import JOIN, fn

from .models import Email, Template

PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class Page[ModelType: (Email, Template)]:
    """A page of model instances plus its total count."""

    items: list[ModelType]
    total: int


def email_page(page: int) -> Page[Email]:
    """Return emails newest first in fixed-size pages."""
    query = Email.select().order_by(Email.received_at.desc(), Email.id.desc())
    return Page[Email](list(query.paginate(page, PAGE_SIZE)), query.count())


def email_by_id(email_id: int) -> Email | None:
    """Return one email, if present."""
    return Email.get_or_none(Email.id == email_id)


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
