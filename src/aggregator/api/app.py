"""ASGI application for the local aggregator API."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..email_pull import CredentialsError, GmailRequestError, InvalidInputError
from ..queries import TemplateNotFoundError
from . import accounts, actions, emails, field_parsers, templates, transactions

app = FastAPI(title="Email Aggregator API", version="0.1.0")
app.include_router(accounts.router)
app.include_router(emails.router)
app.include_router(templates.router)
app.include_router(field_parsers.router)
app.include_router(actions.router)
app.include_router(transactions.router)


@app.exception_handler(TemplateNotFoundError)
def template_not_found_error(_: Request, error: TemplateNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(InvalidInputError)
def invalid_input_error(_: Request, error: InvalidInputError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.exception_handler(CredentialsError)
def credentials_error(_: Request, error: CredentialsError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.exception_handler(GmailRequestError)
def gmail_request_error(_: Request, error: GmailRequestError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(error)})


def main() -> None:
    """Run the API with Uvicorn."""
    import uvicorn

    uvicorn.run("aggregator.api.app:app", host="127.0.0.1", port=8000)
