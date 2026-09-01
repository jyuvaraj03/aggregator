# Aggregator

Aggregator is a small, composable foundation for record-processing workflows.

## Setup

The project pins CPython 3.14.7, installed with pyenv. Create the project environment
and install all locked dependencies with:

```bash
uv sync
```

## Run the example

```bash
uv run aggregator cli
# or
uv run python -m aggregator cli
```
## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```
