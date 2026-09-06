"""Validated inputs shared by the generation workflow and CLI."""

from typing import Self, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..template_syntax import template_parameter_masks


class ParameterExample(BaseModel):
    """One extracted parameter, identified by its index in the template."""

    model_config = ConfigDict(extra="forbid", strict=True)

    index: int = Field(ge=0)
    mask_name: str
    value: str


type ParameterExamples = (
    list[ParameterExample]
    | list[dict[str, object]]
    | list[list[ParameterExample]]
    | list[list[dict[str, object]]]
)


class GenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    template_text: str
    parameter_examples: list[list[ParameterExample]] = Field(min_length=1)

    @field_validator("parameter_examples", mode="before")
    @classmethod
    def normalize_examples(cls, value: object) -> object:
        if isinstance(value, list):
            items = cast(list[object], value)
            return [items] if not items or not isinstance(items[0], list) else items
        return value

    @field_validator("template_text")
    @classmethod
    def validate_template(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Template text must not be blank")
        return value

    @model_validator(mode="after")
    def validate_examples(self) -> Self:
        masks = template_parameter_masks(self.template_text)
        for parameters in self.parameter_examples:
            if sorted(parameter.index for parameter in parameters) != list(range(len(masks))):
                raise ValueError("Each example must contain every template parameter index once")
            for parameter in parameters:
                if parameter.mask_name != masks[parameter.index]:
                    raise ValueError(
                        f"Parameter {parameter.index} must have mask_name "
                        f"{masks[parameter.index]!r}"
                    )
        return self
