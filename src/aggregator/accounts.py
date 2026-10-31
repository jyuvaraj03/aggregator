"""Application operations for independently managed accounts."""

# Peewee's query methods and field expressions are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false

from typing import cast

from peewee import IntegrityError

from .database import database_connection
from .models import Account, Transaction
from .queries import PAGE_SIZE
from .read_models import AccountRecord, Page


class AccountNotFoundError(Exception):
    """The requested account does not exist."""


class InvalidAccountNameError(Exception):
    """The supplied account name is blank after normalization."""


class AccountInUseError(Exception):
    """The account has saved transactions and cannot be removed."""


class InvalidAccountColorError(ValueError):
    """The account colour is outside the palette."""


class AccountNameConflictError(Exception):
    """The normalized account name is already in use."""


def _normalized_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise InvalidAccountNameError("Account name must not be blank")
    return normalized


def _record(account: Account) -> AccountRecord:
    return AccountRecord(id=account.id, name=account.name, color=account.color)


def create_account(name: str, color: int = 0) -> AccountRecord:
    """Create an account with a normalized, unique name."""
    normalized = _normalized_name(name)
    _validate_color(color)
    with database_connection() as connection, connection.atomic():
        try:
            return _record(Account.create(name=normalized, color=color))
        except IntegrityError as error:
            raise AccountNameConflictError("Account name already exists") from error


def account_page(page: int) -> Page[AccountRecord]:
    """Return accounts newest first in fixed-size pages."""
    with database_connection():
        query = Account.select().order_by(Account.id.desc())
        accounts = [_record(account) for account in query.paginate(page, PAGE_SIZE)]
        return Page(accounts, query.count())


def account_by_id(account_id: int) -> AccountRecord | None:
    """Return one account, if present."""
    with database_connection():
        account = Account.get_or_none(Account.id == account_id)
        return _record(account) if account is not None else None


def _validate_color(color: int) -> None:
    if type(color) is not int or not 0 <= color <= 19:
        raise InvalidAccountColorError("Account color must be an integer from 0 to 19")


def update_account(
    account_id: int, *, name: str | None = None, color: int | None = None
) -> AccountRecord:
    """Update supplied account attributes atomically."""
    normalized = _normalized_name(name) if name is not None else None
    if color is not None:
        _validate_color(color)
    with database_connection() as connection, connection.atomic():
        account = Account.get_or_none(Account.id == account_id)
        if account is None:
            raise AccountNotFoundError("Account not found")
        if normalized is not None:
            account.name = normalized
        if color is not None:
            account.color = color
        try:
            account.save()
        except IntegrityError as error:
            raise AccountNameConflictError("Account name already exists") from error
        return _record(account)


def delete_account(account_id: int) -> None:
    """Delete an account or report that it does not exist."""
    with database_connection() as connection, connection.atomic("IMMEDIATE"):
        if Transaction.select().where(Transaction.account == account_id).exists():
            raise AccountInUseError(
                "This account has saved transactions. Moving transactions is not available yet."
            )
        deleted = cast(int, Account.delete().where(Account.id == account_id).execute())
        if deleted == 0:
            raise AccountNotFoundError("Account not found")
