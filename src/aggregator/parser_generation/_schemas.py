"""Required, non-null parser fields for model structured output."""

from pydantic import BaseModel, ConfigDict

from ..parser_configuration import FieldParserConfiguration


class GeneratedFieldParsers(BaseModel):
    """A complete set of inferred transaction field parsers."""

    model_config = ConfigDict(extra="forbid")

    amount: FieldParserConfiguration
    currency_code: FieldParserConfiguration
    payee: FieldParserConfiguration
    description: FieldParserConfiguration
    transaction_date: FieldParserConfiguration
    account_hint: FieldParserConfiguration
    is_credit: FieldParserConfiguration
