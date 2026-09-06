from typing import cast

import pytest
from pydantic import ValidationError

from aggregator.email_content import readable_body
from aggregator.parser_configuration import (
    ConstantFieldParser,
    ExtractedFieldParser,
    FieldParserSet,
    MissingFieldParser,
    validate_parser_rule,
)
from aggregator.template_mining import ExtractedParameter
from aggregator.template_representation import represent_email_template, resolve_fields


@pytest.mark.parametrize("indices", [[], [0, 0], [-1], [True], ["0"]])
def test_extracted_configuration_rejects_invalid_indices(indices: list[object]) -> None:
    with pytest.raises(ValidationError):
        FieldParserSet.model_validate(
            {"amount": {"rule": "extracted", "parameter_indices": indices}}
        )
    with pytest.raises(ValueError):
        validate_parser_rule("extracted", cast(list[int], indices), None)


def test_field_resolution_uses_values_without_database_models() -> None:
    parsers = FieldParserSet(
        amount=ExtractedFieldParser(rule="extracted", parameter_indices=[1, 0]),
        payee=ConstantFieldParser(rule="constant", constant_value="Shop"),
        description=MissingFieldParser(rule="missing"),
    )
    fields = resolve_fields(
        (ExtractedParameter("12", "NUMBER"), ExtractedParameter("$", "CURRENCY_CODE")),
        parsers,
    )
    assert fields["amount"] == "$ 12"
    assert fields["payee"] == "Shop"
    assert fields["description"] is None
    assert fields["currency_code"] is None


@pytest.mark.parametrize(
    ("template", "text", "index"),
    [
        ("Paid <NUMBER>", "Paid 10", 1),
        ("Paid <NUMBER>", "Unrelated message", 0),
    ],
)
def test_representation_rejects_unavailable_parameters(
    template: str, text: str, index: int
) -> None:
    parsers = FieldParserSet(
        amount=ExtractedFieldParser(rule="extracted", parameter_indices=[index])
    )
    with pytest.raises(ValueError, match="unavailable"):
        represent_email_template(template, text, parsers)


def test_resolution_revalidates_mutated_configuration() -> None:
    parser = ExtractedFieldParser(rule="extracted", parameter_indices=[0])
    parsers = FieldParserSet(amount=parser)
    parser.parameter_indices.append(0)
    with pytest.raises(ValueError, match="duplicate"):
        resolve_fields((ExtractedParameter("10", "NUMBER"),), parsers)


@pytest.mark.parametrize(
    ("html", "plain", "expected"),
    [
        ("<h1>Paid</h1><p>10</p>", "Paid 20", "Paid 10"),
        (None, "Paid 20", "Paid 20"),
        ("<div> </div>", "Paid 20", "Paid 20"),
        (None, None, ""),
        ("<div> </div>", None, ""),
    ],
)
def test_email_content_selection(html: str | None, plain: str | None, expected: str) -> None:
    assert readable_body(html, plain) == expected
