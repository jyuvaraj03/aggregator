"""Application operations for template-scoped parser configuration."""

# Peewee exposes dynamically typed fields and query methods.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from typing import Literal, cast

from . import queries
from .database import database, database_connection
from .email_content import readable_body
from .models import FieldParser, Template, TransactionExtractionStatus
from .parser_configuration import (
    ConstantFieldParser,
    ExtractedFieldParser,
    FieldParserSet,
    validate_parser_set,
)
from .read_models import ParserSnapshot
from .template_representation import represent_email_template
from .template_syntax import template_parameter_count, template_parameter_masks


def _snapshot(template: Template, parsers: FieldParserSet) -> ParserSnapshot:
    masks = template_parameter_masks(template.text)
    example = queries.example_email(template.id)
    values: list[str | None] = [None] * len(masks)
    preview: dict[str, str | None] | None = None
    if example is not None:
        representation = represent_email_template(
            template.text, readable_body(example.body_html, example.body_text), parsers
        )
        for index, parameter in enumerate(representation.extracted_parameters[: len(values)]):
            values[index] = parameter.value
        preview = representation.resolved_fields

    return ParserSnapshot(
        template_id=template.id,
        text=template.text,
        transaction_extraction_status=cast(
            Literal["pending", "succeeded", "failed"], template.transaction_extraction_status
        ),
        transaction_extraction_error=template.transaction_extraction_error,
        example_email_id=example.id if example is not None else None,
        parameters=tuple(zip(masks, values, strict=True)),
        parsers=parsers,
        preview=preview,
    )


def field_parser_snapshot(template_id: int) -> ParserSnapshot:
    with database_connection():
        template = queries.require_template(template_id)
        parsers = queries.parser_sets({template_id: template})[template_id]
        return _snapshot(template, parsers)


def replace_field_parsers(template_id: int, parser_set: FieldParserSet) -> ParserSnapshot:
    """Atomically replace configurations and prepare the resulting preview."""
    with database_connection():
        with database.atomic():
            template = queries.require_template(template_id)
            validate_parser_set(parser_set, template_parameter_count(template.text))
            FieldParser.delete().where(FieldParser.template == template_id).execute()
            for name, configuration in parser_set.configured().items():
                FieldParser.create(
                    template=template,
                    field_name=name,
                    rule=configuration.rule,
                    parameter_indices=(
                        configuration.parameter_indices
                        if isinstance(configuration, ExtractedFieldParser)
                        else []
                    ),
                    constant_value=(
                        configuration.constant_value
                        if isinstance(configuration, ConstantFieldParser)
                        else None
                    ),
                )
            template.transaction_extraction_status = TransactionExtractionStatus.PENDING.value
            template.transaction_extraction_error = None
            template.save(
                only=[Template.transaction_extraction_status, Template.transaction_extraction_error]
            )
            return _snapshot(template, parser_set.model_copy(deep=True))
