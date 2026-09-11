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

## Background actions

Email sync, template assignment, parser generation, and transaction extraction run through
Celery. Start Redis, then run the API and worker in separate terminals:

```bash
docker compose up -d redis
uv run aggregator-api
uv run aggregator-worker
```

The action POST endpoints return `202 Accepted` with a `job_id` and `status_url`. Poll
`GET /jobs/{job_id}` until its status is `succeeded` or `failed`; successful results use
the action's former response shape. Configure Redis with `AGGREGATOR_REDIS_URL` (default:
`redis://127.0.0.1:16379/0` when using the included Compose service). Jobs retry transient failures twice and their results expire
after seven days.

## Run the example

```bash
uv run aggregator cli
# or
uv run python -m aggregator cli
```

## Generate field parsers

Copy `.env.example` to `.env` and select the parser-generation backend with
`PARSER_GENERATION_PROVIDER`. It defaults to `ollama` and accepts `ollama` or `mistral`.

For Ollama, install and run `deepseek-r1` (`ollama pull deepseek-r1`) and set
`OPENAI_API_KEY=ollama`. The workflow uses `http://localhost:11434/v1`; the client
requires a nonempty key, which the local endpoint ignores (see
[Ollama's compatibility documentation](https://docs.ollama.com/api/openai-compatibility)).

For Mistral, set the following values. The workflow uses `mistral-large-latest`.

```dotenv
PARSER_GENERATION_PROVIDER=mistral
MISTRAL_API_KEY=your-api-key
```

All correction attempts use the initially selected provider and model; the workflow does
not automatically fall back between providers.

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

### Langfuse tracing

Every parser-generation LangChain call uses Langfuse's native callback. Set
`LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in `.env` to send traces to your
project. `LANGFUSE_BASE_URL` defaults to the local [endpoint](https://langfuse.com/self-hosting/deployment/docker-compose) at `http://localhost:3000`, as
shown in `.env.example`, but can point to another Langfuse region or a self-hosted
deployment. Set `LANGFUSE_TRACING_ENVIRONMENT` to keep local, staging, and production
traces separate.

The LangGraph run is named `generate-field-parsers`; its model generations include
the prompt, completion, model, and token usage.

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

Set `GMAIL_LABEL` in `.env` before syncing. It is required and names the single Gmail label
that Aggregator reads; surrounding whitespace is ignored.

## Development

### Local email frontend

The React application in [`frontend/`](frontend/README.md) lets you choose a sync start
date and inspect all stored emails. Start `uv run aggregator-api`, then run
`npm ci` and `npm run dev` from `frontend/`. Open http://127.0.0.1:5173.
See the frontend README for API type generation and browser test commands.

### Backend checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```
