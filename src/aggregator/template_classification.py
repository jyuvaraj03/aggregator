"""Application operations for classifying mined email templates."""

# Peewee exposes dynamically typed fields and query methods.
# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

from . import queries
from .database import PROJECT_ROOT, database, database_connection
from .models import Template
from .pii import sanitize_template_text

_TRANSACTION_ALERT_QUESTION = Noul(
    instructions="Is the given email template a bank/wallet/card transaction alert?"
)
_TRANSACTION_ALERT_THRESHOLD = 0.7
_NON_TRANSACTION_ALERT_THRESHOLD = 0.3
_LANGFUSE_GENERATION_NAME = "classify-template"


def _langfuse_tracing() -> Any:
    """Create the Langfuse client after loading environment variables."""
    from langfuse import get_client

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    return get_client()


class TemplateClassificationPredictor:
    """Classify email templates with TypeSafe AI."""

    def __init__(self, api_key: str | None = None) -> None:
        if api_key is None:
            load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
            api_key = os.getenv("JEV_API_KEY", "")

        self._api_key = api_key.strip()
        if not self._api_key:
            raise RuntimeError("JEV_API_KEY must be set to classify templates")

    def predict(self, template_text: str) -> bool | None:
        """Predict whether a mined template is a transaction alert."""
        sanitized_template_text = sanitize_template_text(template_text)
        state = {"email_template": sanitized_template_text}
        questions = {"is_transaction_alert": _TRANSACTION_ALERT_QUESTION}
        langfuse = _langfuse_tracing()
        try:
            with langfuse.start_as_current_observation(
                name=_LANGFUSE_GENERATION_NAME,
                as_type="generation",
                input={
                    "state": state,
                    "questions": {
                        name: question.model_dump(mode="json")
                        for name, question in questions.items()
                    },
                },
            ) as generation:
                with TypeSafeClient(
                    api_key=self._api_key,
                    retry=RetryPolicy(max_retries=0),
                ) as client:
                    response = client.system_one(state=state, questions=questions)

                usage_details: dict[str, int] = {}
                if response.usage.input_tokens is not None:
                    usage_details["input"] = response.usage.input_tokens
                if response.usage.output_tokens is not None:
                    usage_details["output"] = response.usage.output_tokens
                generation.update(
                    output=response.model_dump(mode="json"),
                    model=response.model,
                    usage_details=usage_details,
                )
                probability = response.nouls["is_transaction_alert"].noul
        finally:
            langfuse.flush()

        if probability >= _TRANSACTION_ALERT_THRESHOLD:
            return True
        if probability <= _NON_TRANSACTION_ALERT_THRESHOLD:
            return False
        return None


@dataclass(frozen=True, slots=True)
class TemplateClassificationResult:
    """Detached result of one persisted template classification."""

    template_id: int
    is_transaction_alert: bool | None


def classify_template(template_id: int) -> TemplateClassificationResult:
    """Predict and persist the transaction-alert classification for a template."""
    with database_connection():
        template = queries.require_template(template_id)
        template_text = str(template.text)

    prediction = TemplateClassificationPredictor().predict(template_text)
    if prediction is not None and type(prediction) is not bool:
        raise TypeError("Template classification must be a boolean or None")

    with database_connection():
        with database.atomic():
            template = queries.require_template(template_id)
            template.is_transaction_alert = prediction
            template.save(only=[Template.is_transaction_alert])

    return TemplateClassificationResult(
        template_id=template_id,
        is_transaction_alert=prediction,
    )
