"""Guided transaction-field parser configuration routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from peewee import SqliteDatabase

from ..field_parsers import field_parser_snapshot, replace_field_parsers
from ..queries import template_by_id
from .dependencies import database_dependency
from .schemas import FieldParserSet, TemplateFieldParsersResponse

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/{template_id}/field-parsers", response_model=TemplateFieldParsersResponse)
def get_field_parsers(
    template_id: int,
    database: Annotated[SqliteDatabase, Depends(database_dependency)],
) -> TemplateFieldParsersResponse:
    del database
    template = template_by_id(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return field_parser_snapshot(template)


@router.put("/{template_id}/field-parsers", response_model=TemplateFieldParsersResponse)
def put_field_parsers(
    template_id: int,
    parser_set: FieldParserSet,
    database: Annotated[SqliteDatabase, Depends(database_dependency)],
) -> TemplateFieldParsersResponse:
    del database
    template = template_by_id(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        replace_field_parsers(template, parser_set)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return field_parser_snapshot(template)
