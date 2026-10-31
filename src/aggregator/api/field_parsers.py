"""Guided transaction-field parser configuration routes."""

# Celery task proxies are untyped.
# pyright: reportFunctionMemberAccess=false

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field, StrictStr, field_validator
from redis.exceptions import RedisError

from ..background_tasks import queue_parser_generation
from ..field_parsers import (
    FieldParserGenerationError,
    IncompleteFieldParsersError,
    InvalidParserPreviewError,
    MissingParserExampleError,
    TemplateNotTransactionAlertError,
    field_parser_snapshot,
)
from ..parser_configuration import FieldParserSet
from ..parser_review import ParserSessionConflictError, approve_review, replace_manual
from ..queries import TemplateNotFoundError
from .schemas import BackgroundJobResponse, TemplateFieldParsersResponse
from .serializers import parser_snapshot_response

router = APIRouter(prefix="/templates", tags=["templates"])


class GenerateFieldParsersRequest(BaseModel):
    feedback: StrictStr | None = Field(default=None, max_length=4000)

    @field_validator("feedback")
    @classmethod
    def normalize_feedback(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


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
        snapshot = replace_manual(template_id, parser_set)
    except ParserSessionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RedisError as error:
        raise HTTPException(status_code=503, detail="Parser coordination is unavailable") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return parser_snapshot_response(snapshot)


@router.post(
    "/{template_id}/field-parsers/approve",
    response_model=TemplateFieldParsersResponse,
)
def post_approve_field_parsers(template_id: int) -> TemplateFieldParsersResponse:
    try:
        snapshot = approve_review(template_id)
    except ParserSessionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RedisError as error:
        raise HTTPException(status_code=503, detail="Parser coordination is unavailable") from error
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
def post_generate_field_parsers(
    template_id: int,
    response: Response,
    request: GenerateFieldParsersRequest | None = None,
) -> BackgroundJobResponse:
    try:
        job = queue_parser_generation(template_id, request.feedback if request else None)
    except (TemplateNotTransactionAlertError, ParserSessionConflictError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except FieldParserGenerationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except HTTPException, TemplateNotFoundError:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Background queue is unavailable") from error
    status_url = f"/jobs/{job.id}"
    response.headers["Location"] = status_url
    return BackgroundJobResponse(job_id=job.id, status_url=status_url)
