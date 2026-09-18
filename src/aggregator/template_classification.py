"""Application operations for classifying mined email templates."""

# Peewee exposes dynamically typed fields and query methods.
# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import queries
from .database import database, database_connection
from .models import Template

TemplateClassificationPredictor = Callable[[str], bool | None]


@dataclass(frozen=True, slots=True)
class TemplateClassificationResult:
    """Detached result of one persisted template classification."""

    template_id: int
    is_transaction_alert: bool | None


def predict_transaction_alert(template_text: str) -> bool | None:
    """Predict whether a mined template is a transaction alert.

    This placeholder deliberately leaves templates unclassified until a real
    predictor is supplied.
    """
    del template_text
    return None


def classify_template(
    template_id: int,
    *,
    predictor: TemplateClassificationPredictor | None = None,
) -> TemplateClassificationResult:
    """Predict and persist the transaction-alert classification for a template."""
    with database_connection():
        template = queries.require_template(template_id)
        template_text = str(template.text)

    prediction = (predictor or predict_transaction_alert)(template_text)
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
