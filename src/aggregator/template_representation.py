"""Database-independent template extraction and field resolution."""

from dataclasses import dataclass

from .parser_configuration import (
    TRANSACTION_FIELD_NAMES,
    ConstantFieldParser,
    ExtractedFieldParser,
    FieldParserSet,
    validate_parser_set,
)
from .template_mining import (
    ExtractedParameter,
    MiningRecord,
    get_extracted_parameters,
)
from .template_syntax import template_parameter_count


@dataclass(frozen=True, slots=True)
class TemplateRepresentation:
    template_text: str
    extracted_parameters: tuple[ExtractedParameter, ...]
    resolved_fields: dict[str, str | None]


def resolve_fields(
    parameters: tuple[ExtractedParameter, ...], parsers: FieldParserSet
) -> dict[str, str | None]:
    """Resolve configurations against the supplied parameter values."""
    validate_parser_set(parsers, len(parameters))
    resolved: dict[str, str | None] = dict.fromkeys(TRANSACTION_FIELD_NAMES)
    for name, parser in parsers.configured().items():
        if isinstance(parser, ExtractedFieldParser):
            resolved[name] = " ".join(parameters[index].value for index in parser.parameter_indices)
        elif isinstance(parser, ConstantFieldParser):
            resolved[name] = parser.constant_value
    return resolved


def represent_email_template(
    template_text: str, text: str, parsers: FieldParserSet
) -> TemplateRepresentation:
    validate_parser_set(parsers, template_parameter_count(template_text))
    parameters = tuple(get_extracted_parameters(MiningRecord("", text), template_text))
    return TemplateRepresentation(template_text, parameters, resolve_fields(parameters, parsers))
