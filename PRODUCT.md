# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Aggregator is intended for personal use. Its user wants to turn their financial
emails into structured transactions that they can export.

## Product Purpose

Provide the complete workflow from email ingestion to transaction export:

1. Sync emails.
2. Match emails to templates.
3. Automatically generate parsers.
4. Have the user review generated parsers.
5. Parse the emails using the reviewed parsers.
6. Produce structured transactions.
7. Export transactions.

Success means the user can complete this workflow with visibility into the
generated parsing rules before those rules are used to produce transactions.
This is the intended product scope; not every stage has a browser interface or
is implemented yet.

## Positioning

The product combines reusable email templates, automatic parser generation, and
human review to support a personal transaction-processing workflow. Generated
parsers are an intermediate artifact the user must be able to inspect, rather
than an opaque step in transaction creation.

## Operating Context

The current application runs locally with a React, TypeScript, and Vite frontend
and a Python FastAPI backend backed by SQLite. Gmail access uses the user's
locally configured Google credentials with read-only mailbox access.

The current browser workflow accepts a Gmail label and start date, syncs messages,
reports pulled, inserted, and already-stored counts, and lets the user browse
stored emails and inspect their bodies as plain text. Pagination survives detail
navigation, and received times use the browser's locale and timezone.

Local operation describes the existing implementation; a permanent local-only
deployment requirement has not been established.

## Capabilities and Constraints

### Existing implementation

- The web interface provides email sync, paginated browsing, and email detail.
- Backend APIs support template assignment and inspection, account management,
  template-to-account assignment, parser generation and replacement, transaction
  extraction, and transaction listing.
- Parser rules describe extracted values, constants, or explicitly missing fields
  for amount, currency code, payee, description, transaction date, account hint,
  and credit/debit direction.
- Parser generation can use a local Ollama model or a remote Mistral provider.
  Local application storage does not imply all model processing stays local.
- Transaction extraction requires an assigned account and complete parser
  configuration. Extraction reports skipped records and failures.
- The current generation API saves generated parsers; it does not establish a
  separate human-approval state before extraction.

### Intended behavior and open decisions

- Human review belongs between automatic parser generation and parsing. The
  review interface and how approval gates parsing remain to be defined.
- The browser should eventually support the complete workflow above; current
  email-only screens do not define the long-term product boundary.
- Transaction export is an intended capability. Export formats, destinations,
  and selection behavior remain undecided.
- Supported banks, required currencies, and any permanent deployment or external
  model-provider restrictions remain undecided.

## Evidence on Hand

- `README.md` documents local setup, Gmail credentials, and parser generation.
- `frontend/README.md` and `frontend/src/features/emails/` establish the current
  browser capabilities and behavior.
- `src/aggregator/api/` and `docs/bruno/` establish the backend operations and
  example API requests.
- `tests/` and `frontend/tests/emails.spec.ts` contain behavioral coverage and
  fixtures. Fixtures are not evidence of supported banks or extraction accuracy.

## Product Principles

- Optimize for the personal user's complete email-to-export workflow.
- Make generated parser rules inspectable before they are used for parsing.
- Reuse template-level parsing rules across matching emails.
- Keep missing values, skipped records, and failures explicit so the user can
  understand what needs attention.

## Accessibility & Inclusion

Accessibility is not a top product priority at this stage. No specific conformance
target or additional user needs have been established. Existing keyboard access,
focus behavior, semantic labels, and status announcements remain part of the
current interface.
