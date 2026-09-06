# Aggregator

Aggregator is a small, composable foundation for record-processing workflows.

## Setup

The project pins CPython 3.14.7, installed with pyenv. Create the project environment
and install all locked dependencies with:

```bash
uv sync
```

Apply the database schema migrations before running a sync:

```bash
uv run pwmigrate up
```

## Run the example

```bash
uv run aggregator cli
# or
uv run python -m aggregator cli
```

## Generate field parsers

Run Ollama locally with `deepseek-r1` installed (`ollama pull deepseek-r1`). The
workflow always uses this model at `http://localhost:11434/v1`, including correction
attempts. Copy `.env.example` to `.env` and set `OPENAI_API_KEY=ollama`; the client
requires a nonempty key, which the local Ollama endpoint ignores (see
[Ollama's compatibility documentation](https://docs.ollama.com/api/openai-compatibility)).

Supply template text and extracted parameter objects with `index`, `mask_name`,
and `value`. A flat array represents one example email:

```bash
uv run python -m aggregator.parser_generation <<'JSON'
{
  "template_text": "Paid <CURRENCY_CODE> <NUMBER> from account <NUMBER> to <*>",
  "parameter_examples": [
    {"index": 0, "mask_name": "CURRENCY_CODE", "value": "Rs."},
    {"index": 1, "mask_name": "NUMBER", "value": "537.77"},
    {"index": 2, "mask_name": "NUMBER", "value": "6700"},
    {"index": 3, "mask_name": "*", "value": "paytm.d63608789@pty"}
  ]
}
JSON
```

The package also exposes the workflow as a Python function:

```python
from aggregator.parser_generation import generate_field_parsers

parsers = generate_field_parsers(
    "Paid <CURRENCY_CODE> <NUMBER> from account <NUMBER> to <*>",
    [
        {"index": 0, "mask_name": "CURRENCY_CODE", "value": "Rs."},
        {"index": 1, "mask_name": "NUMBER", "value": "537.77"},
        {"index": 2, "mask_name": "NUMBER", "value": "6700"},
        {"index": 3, "mask_name": "*", "value": "paytm.d63608789@pty"},
    ],
)
print(parsers.model_dump_json(indent=2))
```

For multiple emails, pass `[first_email_parameters, second_email_parameters]`.
Python callers can also supply `ParameterExample` Pydantic objects in place of dictionaries.

The model receives a Pydantic-generated JSON schema through
`with_structured_output(..., method="json_schema")`. Pydantic validates the response
directly; no reasoning-tag removal or Markdown cleanup is performed.
The result is a validated `FieldParserSet` covering all seven transaction fields,
using `extracted`, `constant`, or explicit `missing` rules when a field cannot be
inferred. Extracted indices are zero-based; multiple values are joined with spaces
in the selected order. Nothing is saved to the database.

Inputs require nonblank template text and complete examples. Every example must
contain each placeholder index exactly once, with the matching mask name and a string
value. Object order does not matter: the explicit zero-based index identifies the
placeholder. Use `[]` or `[[]]` for a template with no placeholders. Invalid inputs
fail before contacting the model. Invalid model output receives up to two
correction attempts before `ParserGenerationError` is raised; provider failures
propagate. The CLI prints JSON to stdout or an error to stderr with exit code 1.
Repeated requests are not guaranteed to produce identical guesses.

## Gmail credentials

`aggregator.email_pull.pull_messages()` reads the authenticated user's mailbox
using Google Application Default Credentials (ADC). In a Google Cloud project,
enable the Gmail API, configure the OAuth consent screen, add your Gmail address
as a test user when applicable, and create an OAuth **Desktop app** client.

Authenticate the local user once, using the downloaded client JSON file:

```bash
gcloud auth application-default login \
  --client-id-file=/absolute/path/to/client_secret.json \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/gmail.readonly
```

Google stores the resulting ADC at
`~/.config/gcloud/application_default_credentials.json`; `google-auth` discovers
it and refreshes access tokens automatically. To use another credential file,
set `GOOGLE_APPLICATION_CREDENTIALS` to its path. Do not commit OAuth client or
credential files.

This configuration is intended for a local personal Gmail account.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```
