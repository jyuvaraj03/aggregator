"""Email read routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from peewee import SqliteDatabase

from ..queries import PAGE_SIZE, email_by_id, email_page
from .dependencies import database_dependency
from .schemas import EmailDetail, EmailPage
from .serializers import email_detail, email_summary

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=EmailPage)
def list_emails(
    database: Annotated[SqliteDatabase, Depends(database_dependency)],
    page: int = Query(default=1, ge=1),
) -> EmailPage:
    del database
    result = email_page(page)
    return EmailPage(
        items=[email_summary(email) for email in result.items],
        total=result.total,
        page=page,
        page_size=PAGE_SIZE,
        total_pages=(result.total + PAGE_SIZE - 1) // PAGE_SIZE,
    )


@router.get("/{email_id}", response_model=EmailDetail)
def get_email(
    email_id: int,
    database: Annotated[SqliteDatabase, Depends(database_dependency)],
) -> EmailDetail:
    del database
    email = email_by_id(email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return email_detail(email)
