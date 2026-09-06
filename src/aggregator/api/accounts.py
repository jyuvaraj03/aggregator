"""Account CRUD routes."""

from __future__ import annotations

from typing import Never

from fastapi import APIRouter, HTTPException, Query, Response, status

from .. import accounts
from ..queries import PAGE_SIZE
from ..read_models import AccountRecord
from .schemas import AccountCreate, AccountPage, AccountResponse, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _response(account: AccountRecord) -> AccountResponse:
    return AccountResponse(id=account.id, name=account.name)


def _raise_http_error(error: Exception) -> Never:
    if isinstance(error, accounts.AccountNotFoundError):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, accounts.InvalidAccountNameError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    if isinstance(error, accounts.AccountNameConflictError):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise error


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate) -> AccountResponse:
    try:
        return _response(accounts.create_account(payload.name))
    except (accounts.InvalidAccountNameError, accounts.AccountNameConflictError) as error:
        _raise_http_error(error)


@router.get("", response_model=AccountPage)
def list_accounts(page: int = Query(default=1, ge=1)) -> AccountPage:
    result = accounts.account_page(page)
    return AccountPage(
        items=[_response(account) for account in result.items],
        total=result.total,
        page=page,
        page_size=PAGE_SIZE,
        total_pages=(result.total + PAGE_SIZE - 1) // PAGE_SIZE,
    )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int) -> AccountResponse:
    account = accounts.account_by_id(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return _response(account)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, payload: AccountUpdate) -> AccountResponse:
    try:
        return _response(accounts.rename_account(account_id, payload.name))
    except (
        accounts.AccountNotFoundError,
        accounts.InvalidAccountNameError,
        accounts.AccountNameConflictError,
    ) as error:
        _raise_http_error(error)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_account(account_id: int) -> Response:
    try:
        accounts.delete_account(account_id)
    except accounts.AccountNotFoundError as error:
        _raise_http_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
