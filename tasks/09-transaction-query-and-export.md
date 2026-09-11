# 09 — Query transaction evidence and export CSV

Status: Not started

Dependencies: [05](05-approved-transaction-extraction.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Provide consistent transaction browsing and exports, including records beyond one page.
`src/aggregator/api/transactions.py` currently lists transactions; there is no CSV export workflow.

## Work and interfaces

- Extend paginated reads with transaction-date range, account, and direction filters plus matching
  totals. Detail returns source email, applied rules/version, and account provenance.
- Distinguish export-ready records from incomplete historical rows. Unknown historical parser
  provenance must be explicit rather than falsely attributed to a current parser.
- Export either explicit selected transaction IDs or all records matching supplied filters, never
  only the visible page. Materialize a consistent snapshot at export request time.
- Return a downloadable UTF-8 CSV with columns in this order: transaction ID, transaction date,
  account, amount, currency, direction, payee, description, account hint, source email ID.
- Use ISO dates, lossless decimals, credit/debit labels, blanks for optional missing fields, proper
  CSV escaping, and spreadsheet-safe treatment of email-derived text. Document serialized headers.
- Export must not mutate transactions or mark them excluded from later downloads. Explicit selection
  containing unavailable/ineligible IDs returns an actionable error rather than silently omitting rows.

## Acceptance criteria and verification

- [ ] Browse counts and exported filtered counts agree across multiple pages.
- [ ] Selected IDs produce precisely that eligible set; incomplete rows are excluded from normal
  filtered export and explained when selected explicitly.
- [ ] Concurrent ingestion/updates do not change an export's snapshot after it is captured.
- [ ] Dates, decimals, quotes, newlines, Unicode, empty values, and formula-like text serialize safely.
- [ ] Repeated export changes no state; read/export/API tests pass with updated Bruno examples and
  backend checks.

## Exclusions

JSON export, external destinations, cross-email deduplication, and download UI are outside scope.
