"""Template read routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..queries import PAGE_SIZE
from ..reads import template_by_id, template_page
from .schemas import TemplateDetailResponse, TemplatePage
from .serializers import template_email_example, template_response

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplatePage)
def list_templates(
    page: int = Query(default=1, ge=1),
) -> TemplatePage:
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
) -> TemplateDetailResponse:
    template = template_by_id(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    example = template.example
    return TemplateDetailResponse(
        **template_response(template).model_dump(),
        example=template_email_example(example) if example is not None else None,
    )
