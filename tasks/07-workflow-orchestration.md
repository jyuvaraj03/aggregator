# 07 — Orchestrate manual sync through automatic processing

Status: Not started

Dependencies: [04](04-email-processing-state.md),
[05](05-approved-transaction-extraction.md), [06](06-parser-approval.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

One user-triggered sync should advance every email as far as its prerequisites allow.
`src/aggregator/background_tasks.py` exposes separate Celery actions; job results currently expire
after seven days. Email sync and template assignment already have separate core operations.

## Work and interfaces

- Add durable workflow/run records and stage outcomes independent of expiring Celery results.
  Expose run listing/detail, current stage, actual counts, failures, and links to affected records.
- Chain manual sync into template matching, generation for new templates without usable drafts,
  and extraction with approved rules and resolved accounts. Do not regenerate on every sync.
- Keep matching/generation failures isolated so approved templates continue processing. Explicit
  regeneration and targeted retry remain available without repeating successful work.
- Persist selected import settings and the last successful sync's start date. Default subsequent
  syncs to that date; allow explicit backfills. Source configuration remains the configured Gmail
  label, not an invented label-picker or OAuth implementation.
- Resume pending processing after approval, account resolution, or restoration. Reconcile durable
  pending dispatch from task 06 after worker/queue outages.
- Prevent overlapping runs from duplicating imports, drafts, or transactions; return the existing
  active run for duplicate sync submissions. Distinguish stage completion from whole-run success.

## Acceptance criteria and verification

- [ ] First sync creates reviewable drafts without extracting unapproved rules.
- [ ] Repeat sync automatically processes known formats and reports duplicate imports separately.
- [ ] Outcomes distinguish created transactions, waiting review/accounts, ignored emails, and errors.
- [ ] Refresh/restart and expired queue results do not erase workflow visibility.
- [ ] Partial failure and retry preserve successful work; no background schedule starts Gmail sync.
- [ ] Mocked workflow/job/API tests exercise interrupted stages and duplicate requests; update
  operational docs/Bruno examples and run backend checks.

## Exclusions

Scheduled sync, push notifications, provider changes, and browser implementation are outside scope.
