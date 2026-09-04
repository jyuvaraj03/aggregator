"""Shared serialization for ordered template parameters."""

from __future__ import annotations

from collections.abc import Iterable

from .schemas import IndexedParameterResponse


def indexed_parameter_responses(
    parameters: Iterable[tuple[str, str | None]],
) -> list[IndexedParameterResponse]:
    """Serialize ordered ``(mask_name, value)`` pairs with zero-based indices."""
    return [
        IndexedParameterResponse(index=index, mask_name=mask_name, value=value)
        for index, (mask_name, value) in enumerate(parameters)
    ]
