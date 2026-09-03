# Drain3 is intentionally dynamically typed.
# Peewee model primary-key descriptors are dynamically typed.
# pyright: reportAttributeAccessIssue=false, reportMissingTypeStubs=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from dataclasses import dataclass
from typing import TYPE_CHECKING

from drain3.template_miner import ExtractedParameter

from aggregator.template_mining import MiningRecord, get_extracted_parameters

if TYPE_CHECKING:
    from aggregator.models import Email


@dataclass(frozen=True, slots=True)
class TemplateRepresentation:
    template_text: str
    extracted_parameters: list[ExtractedParameter]


def represent_email_template(email: Email) -> TemplateRepresentation:
    """Build a representation for an email known to have a template."""
    template = email.template
    if template is None:
        raise ValueError("Cannot represent an email without a template")

    mining_record = MiningRecord(email.id, email.readable_body())
    template_text = template.text
    parameters = get_extracted_parameters(mining_record, template_text)

    return TemplateRepresentation(template_text=template_text, extracted_parameters=parameters)
