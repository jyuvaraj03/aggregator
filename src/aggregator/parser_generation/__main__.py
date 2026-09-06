"""Generate field parsers from a JSON request on stdin."""

from __future__ import annotations

import sys

from . import generate_field_parsers
from ._inputs import GenerationInput


def main() -> None:
    """Print parser JSON to stdout, or report failure to stderr and exit nonzero."""
    try:
        request = GenerationInput.model_validate_json(sys.stdin.read())
        parsers = generate_field_parsers(request.template_text, request.parameter_examples)
    except Exception as error:
        print(f"Parser generation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(parsers.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
