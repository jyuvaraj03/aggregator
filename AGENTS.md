# Repository Guidelines

## Project Structure & Module Organization

Application code uses a `src` layout under `src/aggregator/`. Core modules cover email synchronization, template mining, field parsing, and transaction extraction. FastAPI routes live in `src/aggregator/api/`; parser-generation code lives in `src/aggregator/parser_generation/`. Keep schema changes as ordered scripts in `migrations/`. Tests mirror features in `tests/test_*.py`, while `docs/bruno/` contains requests for manually exercising the API. Use `playground.py` only for local experiments.

## Build, Test, and Development Commands

- `uv sync` creates the Python 3.14 environment and installs locked dependencies.
- `uv run pwmigrate up` applies all migrations to the default `aggregator.sqlite3` database.
- `uv run aggregator-api` starts the local API at `http://127.0.0.1:8000`.
- `uv run pytest` runs the full test suite; pass a path such as `tests/test_api.py` for a focused run.
- `uv run ruff check .` checks lint rules and import ordering.
- `uv run ruff format --check .` verifies formatting; use `uv run ruff format .` to apply it.
- `uv run pyright` runs strict static type checking across `src` and `tests`.

## Coding Style & Naming Conventions

Use four-space indentation, type annotations, and a maximum line length of 100 characters. Ruff enforces `E`, `F`, `I`, `UP`, and `B`; resolve warnings rather than adding broad suppressions. Use `snake_case` for modules, functions, fixtures, and variables; use `PascalCase` for classes and models. Keep route handlers thin and place reusable behavior in core modules.

## Testing Guidelines

Write pytest tests named `test_<behavior>` in the corresponding `tests/test_<feature>.py` file. Use fixtures and `monkeypatch` to isolate Gmail, OpenAI, and other external calls. Database tests should use temporary or in-memory databases and restore the shared database afterward. Add regression coverage for bug fixes and cover both successful and error responses for API changes. No numeric coverage threshold is configured.

## Commit & Pull Request Guidelines

Recent commits use concise, imperative subjects such as `Extract transactions` and `Add transactions listing endpoint`. Follow that style, keep each commit focused, and include a body when the reason is not obvious. Pull requests should explain the behavior change, note migrations or configuration changes, link relevant issues, and list the verification commands run. Include updated Bruno requests or response examples when API contracts change.

## Security & Configuration

Copy `.env.example` to `.env` for local secrets. Never commit OpenAI keys, Google OAuth client files, application-default credentials, or the local SQLite database. Use `AGGREGATOR_DATABASE_PATH` when a task needs an isolated database.
