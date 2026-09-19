"""Template read routes."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from .. import template_accounts
from ..queries import PAGE_SIZE
from ..reads import template_by_id, template_page
from .schemas import TemplateAccountUpdate, TemplateDetailResponse, TemplatePage, TemplateResponse
from .serializers import template_email_example, template_response

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateClassification(StrEnum):
    TRANSACTION_ALERT = "transaction_alert"
    UNCLASSIFIED = "unclassified"
    NOT_TRANSACTION_ALERT = "not_transaction_alert"

    def query_value(self) -> bool | None:
        if self is TemplateClassification.TRANSACTION_ALERT:
            return True
        if self is TemplateClassification.NOT_TRANSACTION_ALERT:
            return False
        return None


@router.get("", response_model=TemplatePage)
def list_templates(
    page: int = Query(default=1, ge=1),
    classification: Annotated[list[TemplateClassification] | None, Query()] = None,
) -> TemplatePage:
    classifications = (
        frozenset(value.query_value() for value in classification)
        if classification is not None
        else None
    )
    result = template_page(page, classifications)
    return TemplatePage(
        items=[template_response(template) for template in result.items],
        total=result.total,
        page=page,
        page_size=PAGE_SIZE,
        total_pages=(result.total + PAGE_SIZE - 1) // PAGE_SIZE,
    )


@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(
    template_id: int,
) -> TemplateDetailResponse:
    template = template_by_id(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    example = template.example
    return TemplateDetailResponse(
        **template_response(template).model_dump(),
        example=template_email_example(example) if example is not None else None,
    )


@router.put("/{template_id}/account", response_model=TemplateResponse)
def update_template_account(template_id: int, payload: TemplateAccountUpdate) -> TemplateResponse:
    try:
        template_accounts.set_template_account(template_id, payload.account_id)
    except template_accounts.TemplateNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except template_accounts.AccountNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    template = template_by_id(template_id)
    if template is None:  # pragma: no cover - protected by the atomic update above
        raise HTTPException(status_code=404, detail="Template not found")
    return template_response(template)
