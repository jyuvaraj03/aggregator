"""Template read routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from peewee import SqliteDatabase

from ..queries import PAGE_SIZE, template_by_id, template_page
from .dependencies import database_dependency
from .schemas import TemplateDetailResponse, TemplatePage
from .serializers import template_email_example, template_response

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplatePage)
def list_templates(
    database: Annotated[SqliteDatabase, Depends(database_dependency)],
    page: int = Query(default=1, ge=1),
) -> TemplatePage:
    del database
    result = template_page(page)
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
    database: Annotated[SqliteDatabase, Depends(database_dependency)],
) -> TemplateDetailResponse:
    del database
    template = template_by_id(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    example = template.example_email()
    return TemplateDetailResponse(
        **template_response(template).model_dump(),
        example=template_email_example(example) if example is not None else None,
    )
