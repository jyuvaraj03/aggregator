# 03 — Resolve accounts through explicit user choices

Status: Not started

Dependencies: None. Read the [UX specification](ux-spec.md) and
[shared rules](README.md#shared-implementation-rules).

## Objective and context

Support multiple accounts sharing an email format while keeping account choice with the user.
`src/aggregator/template_accounts.py` currently assigns one account to a whole template and changes
all its historical transactions. `src/aggregator/accounts.py` provides account management.

## Work and interfaces

- Persist explicit per-email account assignments and optional remembered mappings keyed by template
  and exact, nonblank account hint. A per-email choice takes precedence over a remembered mapping.
- Expose unresolved hints and affected email counts, account selection, and inline account creation
  through application operations and APIs. Remembering a mapping must be an explicit request.
- Never infer an account from similar hints, an account name, or another template. Absent hints need
  per-email assignment; do not create a catch-all mapping for missing hints.
- Separate changing one transaction's account from remembering a mapping for future processing.
  Mapping changes must not rewrite existing transactions.
- Preserve historical account values during migration. Present legacy template assignments for user
  confirmation before converting them into remembered mappings.
- Prevent deleting accounts referenced by transactions, assignments, or mappings with an actionable
  conflict response; do not retain the current possibility of cascading transaction deletion.

## Acceptance criteria and verification

- [ ] Two hints on one template can resolve to two accounts after explicit user choices.
- [ ] Unknown, absent, or conflicting hints never inherit an unrelated account selection.
- [ ] Remembered mappings and individual transaction corrections have distinct effects.
- [ ] Missing/deleted account references cannot leave silent or destructive results.
- [ ] Migration, account API, and resolver tests cover precedence, exact matching, and legacy data;
  update Bruno requests and run backend checks.

## Exclusions

Automatic bank/account inference, global hint matching, and review UI are outside this task.
