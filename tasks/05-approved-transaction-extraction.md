# 05 — Extract only eligible transactions with approved rules

Status: Not started

Dependencies: [01](01-parser-versioning.md), [03](03-account-resolution.md),
[04](04-email-processing-state.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Make extraction enforce the review contract independently of the browser.
`src/aggregator/transaction_extraction.py` currently accepts any complete rules, permits missing
values, and fails a whole template when one email cannot be parsed.

## Work and interfaces

- Require an immutable approved parser version, a user-confirmed account resolution, and valid
  amount, currency, date, and credit/debit direction. Payee and description remain optional.
- Process each email independently. Persist structured errors/blockers from task 04 while allowing
  valid emails in the same template to complete. Respect ignored templates.
- Store the parser version and account decision used for each transaction; migrate historical rows
  with explicitly unknown parser provenance. Use task 02's shared conversion when available.
- Support scoped extraction of eligible pending emails/templates for approval, sync, and retries.
  Legacy bulk actions must use the same approval gate.
- Preserve one transaction per email under retries and concurrent jobs. Bind each processing attempt
  to a specific approved version and recheck eligibility before committing.
- Completed historical rows with missing core fields must remain inspectable but not qualify for
  normal export; expose a remediation reason without deleting them.

## Acceptance criteria and verification

- [ ] Unapproved drafts cannot produce transactions through any extraction entry point.
- [ ] Core-field failures and unresolved accounts remain actionable, outside completed results.
- [ ] One malformed email does not block valid emails sharing its template.
- [ ] Retries/concurrent execution do not duplicate transactions or alter existing completed rows.
- [ ] Provenance identifies the actual version and account used, including during concurrent approval.
- [ ] Extraction, migration, API, and concurrency regression tests pass; update Bruno examples and
  run backend checks. Approved fixtures can be used before task 06 exists.

## Exclusions

Approval actions, automatic orchestration, historical reprocessing, and export delivery are separate.
