from __future__ import annotations

# Peewee and its migration helper are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownMemberType=false
from collections.abc import Generator
from pathlib import Path

import pytest
from playhouse.migrations import Runner

from aggregator import template_classification
from aggregator.database import PROJECT_ROOT, close_database, database, database_connection
from aggregator.models import Template
from aggregator.queries import TemplateNotFoundError


@pytest.fixture(autouse=True)
def isolated_database(tmp_path: Path) -> Generator[None]:
    close_database()
    original_path = database.database
    database.init(str(tmp_path / "classification.sqlite3"))
    with database_connection():
        Runner(database, directory=str(PROJECT_ROOT / "migrations")).up()
    try:
        yield
    finally:
        close_database()
        database.init(original_path)


def test_placeholder_predictor_leaves_template_unclassified() -> None:
    assert template_classification.predict_transaction_alert("Paid <NUMBER>") is None


@pytest.mark.parametrize("prediction", [True, False, None])
def test_classification_persists_and_returns_detached_result(
    prediction: bool | None,
) -> None:
    with database_connection():
        template = Template.create(text="Paid <NUMBER>", is_transaction_alert=not prediction)

    result = template_classification.classify_template(
        template.id,
        predictor=lambda text: prediction if text == "Paid <NUMBER>" else None,
    )

    assert result == template_classification.TemplateClassificationResult(template.id, prediction)
    assert database.is_closed()
    with database_connection():
        assert Template.get_by_id(template.id).is_transaction_alert is prediction


def test_missing_template_does_not_invoke_predictor() -> None:
    def unexpected_predictor(_: str) -> bool | None:
        pytest.fail("predictor was invoked")

    with pytest.raises(TemplateNotFoundError, match="Template not found"):
        template_classification.classify_template(999, predictor=unexpected_predictor)
    assert database.is_closed()
