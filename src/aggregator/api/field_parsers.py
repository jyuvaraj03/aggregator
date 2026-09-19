"""Guided transaction-field parser configuration routes."""

# Celery task proxies are untyped.
# pyright: reportFunctionMemberAccess=false

from fastapi import APIRouter, HTTPException, Response, status

from ..background_tasks import generate_field_parsers_task
from ..field_parsers import (
    IncompleteFieldParsersError,
    InvalidParserPreviewError,
    MissingParserExampleError,
    TemplateNotTransactionAlertError,
    approve_field_parsers,
    field_parser_snapshot,
    replace_field_parsers,
    require_parser_generation_eligible,
)
from ..parser_configuration import FieldParserSet
from ..queries import TemplateNotFoundError
from .schemas import BackgroundJobResponse, TemplateFieldParsersResponse
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


@router.post(
    "/{template_id}/field-parsers/approve",
    response_model=TemplateFieldParsersResponse,
)
def post_approve_field_parsers(template_id: int) -> TemplateFieldParsersResponse:
    try:
        snapshot = approve_field_parsers(template_id)
    except (
        IncompleteFieldParsersError,
        MissingParserExampleError,
        TemplateNotTransactionAlertError,
    ) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InvalidParserPreviewError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return parser_snapshot_response(snapshot)


@router.post(
    "/{template_id}/field-parsers/generate",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def post_generate_field_parsers(template_id: int, response: Response) -> BackgroundJobResponse:
    try:
        require_parser_generation_eligible(template_id)
        job = generate_field_parsers_task.delay(template_id)
    except TemplateNotTransactionAlertError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except HTTPException, TemplateNotFoundError:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Background queue is unavailable") from error
    status_url = f"/jobs/{job.id}"
    response.headers["Location"] = status_url
    return BackgroundJobResponse(job_id=job.id, status_url=status_url)
