"""Template-scoped configuration and preview operations for transaction fields."""

# Peewee's query and relationship APIs are intentionally dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from typing import cast

from .api.schemas import (
    ConstantFieldParser,
    ExtractedFieldParser,
    FieldParserConfiguration,
    FieldParserSet,
    MissingFieldParser,
    ResolvedTransactionFields,
    TemplateFieldParsersResponse,
    TemplateParameterResponse,
)
from .database import database
from .models import (
    TRANSACTION_FIELD_NAMES,
    Field,
    FieldParser,
    FieldParserRule,
    Template,
)
from .template_mining import template_parameter_masks


def _parser_configuration(parser: FieldParser) -> FieldParserConfiguration:
    parser.validate()
    rule = FieldParserRule(parser.rule)
    if rule is FieldParserRule.EXTRACTED:
        return ExtractedFieldParser(
            rule="extracted", parameter_indices=cast(list[int], parser.parameter_indices)
        )
    if rule is FieldParserRule.CONSTANT:
        return ConstantFieldParser(rule="constant", constant_value=cast(str, parser.constant_value))
    return MissingFieldParser(rule="missing")


def _configured_parsers(template: Template) -> FieldParserSet:
    values: dict[str, FieldParserConfiguration] = {}
    query = (
        FieldParser.select(FieldParser, Field)
        .join(Field)
        .where(FieldParser.template == template)
        .order_by(FieldParser.id)
    )
    for parser in query:
        if parser.field.name in TRANSACTION_FIELD_NAMES:
            values[parser.field.name] = _parser_configuration(parser)
    return FieldParserSet.model_validate(values)


def field_parser_snapshot(template: Template) -> TemplateFieldParsersResponse:
    """Build the complete configuration view, including an example preview when possible."""
    masks = template_parameter_masks(template.text)
    example = template.example_email()
    values: list[str | None] = [None] * len(masks)
    preview: ResolvedTransactionFields | None = None
    if example is not None:
        representation = example.representation()
        if representation is None:  # pragma: no cover - guarded by the relationship above
            raise ValueError("The example email is not assigned to the requested template")
        parameters = representation.extracted_parameters
        for index, parameter in enumerate(parameters[: len(values)]):
            values[index] = parameter.value
        preview = ResolvedTransactionFields.model_validate(representation.resolved_fields)

    return TemplateFieldParsersResponse(
        template_id=template.id,
        text=template.text,
        example_email_id=example.id if example is not None else None,
        parameters=[
            TemplateParameterResponse(index=index, mask_name=mask, value=values[index])
            for index, mask in enumerate(masks)
        ],
        parsers=_configured_parsers(template),
        preview=preview,
    )


def replace_field_parsers(template: Template, parser_set: FieldParserSet) -> None:
    """Validate and atomically replace every configured parser for a template."""
    fields = {
        field.name: field for field in Field.select().where(Field.name.in_(TRANSACTION_FIELD_NAMES))
    }
    if set(fields) != set(TRANSACTION_FIELD_NAMES):
        raise RuntimeError("The fixed transaction field catalog has not been seeded")

    replacements: list[FieldParser] = []
    for name in TRANSACTION_FIELD_NAMES:
        configuration = getattr(parser_set, name)
        if configuration is None:
            continue
        if isinstance(configuration, ExtractedFieldParser):
            parser = FieldParser(
                template=template,
                field=fields[name],
                rule=FieldParserRule.EXTRACTED.value,
                parameter_indices=configuration.parameter_indices,
                constant_value=None,
            )
        elif isinstance(configuration, ConstantFieldParser):
            parser = FieldParser(
                template=template,
                field=fields[name],
                rule=FieldParserRule.CONSTANT.value,
                parameter_indices=[],
                constant_value=configuration.constant_value,
            )
        else:
            parser = FieldParser(
                template=template,
                field=fields[name],
                rule=FieldParserRule.MISSING.value,
                parameter_indices=[],
                constant_value=None,
            )
        parser.validate()
        replacements.append(parser)

    with database.atomic():
        FieldParser.delete().where(FieldParser.template == template).execute()
        for parser in replacements:
            parser.save(force_insert=True)
