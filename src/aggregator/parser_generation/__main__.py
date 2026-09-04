"""Run the parser-generation connectivity smoke test."""

from __future__ import annotations

from . import say_hello


def main() -> None:
    """Print a greeting returned by the parser-generation workflow."""
    print(say_hello())


if __name__ == "__main__":
    main()
