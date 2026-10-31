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

The current application runs locally with a Python FastAPI backend backed by
SQLite. Gmail access uses the user's locally configured Google credentials with
read-only mailbox access. There is currently no browser interface; a new frontend
is planned.

Local operation describes the existing implementation; a permanent local-only
deployment requirement has not been established.

## Capabilities and Constraints

### Existing implementation

- Backend APIs support email sync, paginated browsing, email detail, template
  extraction, and template inspection with paginated matching emails.
- Backend APIs support template assignment and inspection, account management,
  template-to-account assignment, parser generation and replacement, transaction
  extraction, and transaction listing.
- Parser rules describe extracted values, constants, or explicitly missing fields
  for amount, currency code, payee, description, transaction date, account hint,
  and credit/debit direction.
- Parser generation can use a local Ollama model or a remote Mistral provider.
  Local application storage does not imply all model processing stays local.
- Transaction extraction requires an assigned account and an approved, complete
  parser configuration. Extraction reports skipped records and failures.
- Saved parser drafts remain ineligible for extraction until approval. Approval
  validates the representative preview, and saving or regenerating rules revokes it.

### Intended behavior and open decisions

- The future browser interface should support the complete workflow above.
- Transaction export is an intended capability. Export formats, destinations,
  and selection behavior remain undecided.
- Supported banks, required currencies, and any permanent deployment or external
  model-provider restrictions remain undecided.

## Evidence on Hand

- `README.md` documents local setup, Gmail credentials, and parser generation.
- `src/aggregator/api/` and `docs/bruno/` establish the backend operations and
  example API requests.
- `tests/` contains backend behavioral coverage and fixtures. Fixtures are not
  evidence of supported banks or extraction accuracy.

## Product Principles

- Optimize for the personal user's complete email-to-export workflow.
- Make generated parser rules inspectable before they are used for parsing.
- Reuse template-level parsing rules across matching emails.
- Keep missing values, skipped records, and failures explicit so the user can
  understand what needs attention.

## Accessibility & Inclusion

Accessibility is not a top product priority at this stage. No specific conformance
target or additional user needs have been established. Accessibility requirements
for the future interface remain to be defined.
