"""Explicit account assignment for templates and their transactions."""

# Peewee's query methods and field expressions are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false

from .database import database_connection
from .models import Account, Email, Template, Transaction


class AccountNotFoundError(Exception):
    """The requested account does not exist."""


class TemplateNotFoundError(Exception):
    """The requested template does not exist."""


def set_template_account(template_id: int, account_id: int | None) -> None:
    """Atomically assign a template and all its transactions to an account."""
    with database_connection() as connection, connection.atomic():
        template = Template.get_or_none(Template.id == template_id)
        if template is None:
            raise TemplateNotFoundError("Template not found")
        if account_id is not None and Account.get_or_none(Account.id == account_id) is None:
            raise AccountNotFoundError("Account not found")

        Template.update(account=account_id).where(Template.id == template_id).execute()
        template_email_ids = Email.select(Email.id).where(Email.template == template_id)
        Transaction.update(account=account_id).where(
            Transaction.email.in_(template_email_ids)
        ).execute()
