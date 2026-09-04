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

## Parser-generation connectivity smoke test

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` in `.env`. Then run the
minimal LangGraph workflow:

```bash
uv run python -m aggregator.parser_generation
```

The package also exposes the workflow as a Python function:

```python
from aggregator.parser_generation import say_hello

greeting = say_hello()
```

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
