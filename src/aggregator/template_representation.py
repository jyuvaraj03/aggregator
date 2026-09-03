# Drain3 is intentionally dynamically typed.
# Peewee model primary-key descriptors are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from drain3.template_miner import ExtractedParameter

from aggregator.models import Field, FieldParser, FieldParserRule
from aggregator.template_mining import MiningRecord, get_extracted_parameters

if TYPE_CHECKING:
    from aggregator.models import Email


@dataclass(frozen=True, slots=True)
class TemplateRepresentation:
    template_text: str
    extracted_parameters: list[ExtractedParameter]
    field_parsers: list[FieldParser]

    @property
    def resolved_fields(self) -> dict[str, str | None]:
        """Resolve this template's configured fields for the represented email."""
        resolved: dict[str, str | None] = {}
        for parser in self.field_parsers:
            parser.validate()
            rule = FieldParserRule(parser.rule)
            if rule is FieldParserRule.EXTRACTED:
                resolved[parser.field.name] = " ".join(
                    self.extracted_parameters[index].value
                    for index in cast(list[int], parser.parameter_indices)
                )
            elif rule is FieldParserRule.CONSTANT:
                resolved[parser.field.name] = parser.constant_value
            else:
                resolved[parser.field.name] = None
        return resolved


def represent_email_template(email: Email) -> TemplateRepresentation:
    """Build a representation for an email known to have a template."""
    template = email.template
    if template is None:
        raise ValueError("Cannot represent an email without a template")

    mining_record = MiningRecord(email.id, email.readable_body())
    template_text = template.text
    parameters = get_extracted_parameters(mining_record, template_text)

    field_parsers = list(
        FieldParser.select(FieldParser, Field)
        .join(Field)
        .where(FieldParser.template == template)
        .order_by(FieldParser.id)
    )
    return TemplateRepresentation(
        template_text=template_text,
        extracted_parameters=parameters,
        field_parsers=field_parsers,
    )
