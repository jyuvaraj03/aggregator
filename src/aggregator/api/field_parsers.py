"""Guided transaction-field parser configuration routes."""

from fastapi import APIRouter, HTTPException

from ..field_parsers import field_parser_snapshot, replace_field_parsers
from ..parser_configuration import FieldParserSet
from .schemas import TemplateFieldParsersResponse
from .serializers import parser_snapshot_response

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/{template_id}/field-parsers", response_model=TemplateFieldParsersResponse)
def get_field_parsers(
    template_id: int,
) -> TemplateFieldParsersResponse:
    return parser_snapshot_response(field_parser_snapshot(template_id))


@router.put("/{template_id}/field-parsers", response_model=TemplateFieldParsersResponse)
def put_field_parsers(
    template_id: int,
    parser_set: FieldParserSet,
) -> TemplateFieldParsersResponse:
    try:
        snapshot = replace_field_parsers(template_id, parser_set)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return parser_snapshot_response(snapshot)
