"""Email read routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..queries import PAGE_SIZE, EmailTemplateFilter
from ..reads import email_by_id, email_page
from .schemas import EmailDetail, EmailPage
from .serializers import email_detail, email_summary

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=EmailPage)
def list_emails(
    page: int = Query(default=1, ge=1),
    template_id: int | Literal["null"] | None = Query(default=None),
) -> EmailPage:
    template_filter = None
    if isinstance(template_id, int):
        template_filter = EmailTemplateFilter(template_id)
    elif template_id == "null":
        template_filter = EmailTemplateFilter(None)

    result = email_page(page, template_filter)
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
) -> EmailDetail:
    email = email_by_id(email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return email_detail(email)
