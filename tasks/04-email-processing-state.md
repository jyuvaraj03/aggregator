# 04 — Persist processing states and actionable attention items

Status: Not started

Dependencies: None. Read the [UX specification](ux-spec.md) and
[shared rules](README.md#shared-implementation-rules).

## Objective and context

Make every waiting or failed email explainable across page refreshes and worker restarts.
Current models record extraction status at template level and extraction returns aggregate counts.

## Work and interfaces

- Add durable per-email processing outcomes and reasons sufficient to distinguish waiting for
  matching, parser review, account assignment, processing, completion, failure, and ignoring.
- Keep prerequisite blockers distinct from execution failures. Define deterministic primary status
  precedence while retaining all applicable reasons; counts must not double-count emails.
- Persist reversible template ignoring. Ignoring excludes pending and future matching emails;
  it does not delete source emails or existing transactions.
- Expose paginated/filterable email status and grouped attention reads with template, reason,
  affected count, example email, field/error details, and supported recovery action identifiers.
- Provide state-transition operations for downstream workers and restoration, plus source/template/
  transaction links in read models. Backfill existing data conservatively without inventing outcomes.
- Extend restore behavior to queue eligible pending work when task 07 supplies orchestration.

## Acceptance criteria and verification

- [ ] Status and actionable reasons survive reconnection and process restart.
- [ ] Attention counts identify distinct affected emails and remain consistent with detail lists.
- [ ] Ignoring/restoring is reversible and preserves transactions and source emails.
- [ ] Failure details distinguish invalid fields from missing prerequisites and infrastructure errors.
- [ ] Migration, state transition, read/API, pagination, and ignore/restore tests pass; update Bruno
  examples and run backend checks.

## Exclusions

This task owns state storage and read contracts, not workflow orchestration or browser presentation.
