"""Template parameter syntax shared by mining and parser validation."""

import re

# Drain3 uses these markers for values masked by this application's mining
# configuration. ``<*>`` is its generic variable marker.
TEMPLATE_PARAMETER_PATTERN = re.compile(r"<(?:DATE|TIME|CURRENCY_CODE|NUMBER|\*)>")


def template_parameter_count(template_text: str) -> int:
    """Return the number of extractable parameter positions in a template."""
    return len(TEMPLATE_PARAMETER_PATTERN.findall(template_text))


def template_parameter_masks(template_text: str) -> list[str]:
    """Return parameter mask names in their template order."""
    return [match.group()[1:-1] for match in TEMPLATE_PARAMETER_PATTERN.finditer(template_text)]
