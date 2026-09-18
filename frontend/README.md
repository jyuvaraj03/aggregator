# Email and template workspace

React + TypeScript + Vite frontend for the local Aggregator API. Requires Node.js
22.12+ and the Python environment described in the root README.

Start FastAPI from the repository root (after migrations and Gmail credentials setup):

```bash
uv run aggregator-api
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Vite forwards `/api/*` to
`http://127.0.0.1:8000/*`. This proxy is for development; production serving and
deployment packaging are outside this slice. `npm run preview` only previews the
built assets and does not provide an API proxy.

The list includes all stored emails in the server's order. Syncing uses the server's
configured Gmail label, resets the list to page one, and reports the job's pulled,
inserted, and already-stored counts.
Pagination lives in `?page=` and is retained in detail/back links. Received times
use the browser's locale and timezone. Email bodies are rendered as plain text.

After each successful email sync, the worker mines all stored emails without a template
and starts parser generation for every newly created template. These later stages continue
in the background after the sync result appears. Emails already assigned keep their template.

Browse templates at `/templates?page=1`, then open a template to inspect its full
pattern, example email, and paginated matching messages. Template detail URLs retain
the template-list page in `page` and the matching-email page in `emailsPage`.
Links to email details carry `fromTemplate`, `templatePage`, and `emailsPage` so
**Back to template** returns to the same position. Email details also link to their
assigned template. Patterns and example bodies are rendered as plain text.

Template inspection is read-only; parser generation progress, accounts, and transaction
extraction are not part of this interface.

## API types

Generated types are committed in `src/lib/api/schema.d.ts`. Regenerate after any
backend schema change:

```bash
npm run generate:api
```

This exports `app.openapi()` through the repository's `uv` environment and runs
`openapi-typescript`; it does not need a running API or open the database. The
client uses openapi-fetch, following its [typed client documentation](https://openapi-ts.dev/openapi-fetch/).
Do not edit the generated file manually.

## Verification

```bash
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

Playwright starts Vite and mocks every API call in the tests. It checks desktop
and mobile layouts, sync counts and retries, pagination, template
and email detail navigation, plain-text rendering, loading, empty, and failure states. Neither Gmail nor
the local database is touched.
