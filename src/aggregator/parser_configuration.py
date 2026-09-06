"""Transport-independent parser configuration and shared validation rules."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


class FieldParserRule(StrEnum):
    EXTRACTED = "extracted"
    CONSTANT = "constant"
    MISSING = "missing"


class TransactionFieldName(StrEnum):
    AMOUNT = "amount"
    CURRENCY_CODE = "currency_code"
    PAYEE = "payee"
    DESCRIPTION = "description"
    TRANSACTION_DATE = "transaction_date"
    ACCOUNT_HINT = "account_hint"
    IS_CREDIT = "is_credit"


TRANSACTION_FIELD_NAMES = tuple(field.value for field in TransactionFieldName)


def validate_parameter_indices(indices: list[int]) -> None:
    if any(type(index) is not int for index in indices):
        raise ValueError("Expected integer parameter indices")
    if not indices:
        raise ValueError("An extracted field parser requires at least one parameter index")
    if len(indices) != len(set(indices)):
        raise ValueError("An extracted field parser cannot contain duplicate parameter indices")
    if any(index < 0 for index in indices):
        raise ValueError("An extracted field parser cannot contain negative parameter indices")


def validate_parameter_bounds(indices: list[int], parameter_count: int) -> None:
    if any(index >= parameter_count for index in indices):
        raise ValueError("An extracted field parser references an unavailable parameter index")


def validate_parser_rule(rule: str, indices: list[int], constant_value: object) -> FieldParserRule:
    try:
        parsed_rule = FieldParserRule(rule)
    except ValueError as error:
        raise ValueError(f"Unsupported field parser rule: {rule!r}") from error
    if parsed_rule is FieldParserRule.EXTRACTED:
        validate_parameter_indices(indices)
        if constant_value is not None:
            raise ValueError("An extracted field parser cannot have a constant value")
    else:
        if indices:
            raise ValueError(f"A {parsed_rule.value} field parser cannot have parameter indices")
        if parsed_rule is FieldParserRule.CONSTANT:
            if constant_value is None:
                raise ValueError("A constant field parser requires a constant value")
            if not isinstance(constant_value, str):
                raise ValueError("A constant field parser requires a string constant value")
        elif constant_value is not None:
            raise ValueError("A missing field parser cannot have a constant value")
    return parsed_rule


def validate_field_name(field_name: str) -> None:
    try:
        TransactionFieldName(field_name)
    except ValueError as error:
        raise ValueError(f"Unsupported transaction field name: {field_name!r}") from error


class ExtractedFieldParser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: Literal["extracted"]
    parameter_indices: list[StrictInt]

    @field_validator("parameter_indices")
    @classmethod
    def validate_indices(cls, indices: list[int]) -> list[int]:
        validate_parser_rule("extracted", indices, None)
        return indices


class ConstantFieldParser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: Literal["constant"]
    constant_value: str

    @field_validator("constant_value")
    @classmethod
    def validate_constant(cls, value: str) -> str:
        validate_parser_rule("constant", [], value)
        return value


class MissingFieldParser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: Literal["missing"]


FieldParserConfiguration = Annotated[
    ExtractedFieldParser | ConstantFieldParser | MissingFieldParser,
    Field(discriminator="rule"),
]


class FieldParserSet(BaseModel):
    """The complete fixed parser set; null and omitted values are unconfigured."""

    model_config = ConfigDict(extra="forbid")

    amount: FieldParserConfiguration | None = None
    currency_code: FieldParserConfiguration | None = None
    payee: FieldParserConfiguration | None = None
    description: FieldParserConfiguration | None = None
    transaction_date: FieldParserConfiguration | None = None
    account_hint: FieldParserConfiguration | None = None
    is_credit: FieldParserConfiguration | None = None

    def configured(self) -> dict[str, FieldParserConfiguration]:
        return {
            name: parser
            for name in TRANSACTION_FIELD_NAMES
            if (parser := getattr(self, name)) is not None
        }


def validate_parser_set(parser_set: FieldParserSet, parameter_count: int) -> None:
    for name, parser in parser_set.configured().items():
        validate_field_name(name)
        indices = parser.parameter_indices if isinstance(parser, ExtractedFieldParser) else []
        constant = parser.constant_value if isinstance(parser, ConstantFieldParser) else None
        validate_parser_rule(parser.rule, indices, constant)
        validate_parameter_bounds(indices, parameter_count)
