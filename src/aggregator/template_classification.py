"""Application operations for classifying mined email templates."""

# Peewee exposes dynamically typed fields and query methods.
# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

from . import queries
from .database import PROJECT_ROOT, database, database_connection
from .models import Template

_TRANSACTION_ALERT_QUESTION = Noul(
    instructions="Is the given email template a bank/wallet/card transaction alert?"
)
_TRANSACTION_ALERT_THRESHOLD = 0.7
_NON_TRANSACTION_ALERT_THRESHOLD = 0.3


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
        with TypeSafeClient(
            api_key=self._api_key,
            retry=RetryPolicy(max_retries=0),
        ) as client:
            response = client.system_one(
                state={"email_template": template_text},
                questions={"is_transaction_alert": _TRANSACTION_ALERT_QUESTION},
            )

        probability = response.nouls["is_transaction_alert"].noul
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
