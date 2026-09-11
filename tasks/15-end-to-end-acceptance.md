# 15 — Verify the complete workflow and document operation

Status: Not started

Dependencies: [11](11-parser-review-experience.md), [12](12-attention-and-email-experience.md),
[13](13-transactions-and-export-experience.md), [14](14-supporting-management.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Prove the independently implemented tasks form the accepted personal-use workflow.
Focused tests belong to their implementation tasks; this task targets cross-feature integration.

## Work and interfaces

- Build deterministic mailbox/model fixtures spanning approved/new templates, two account hints on
  one template, missing hints, malformed fields, ignored emails, and repeated imports.
- Exercise browser/API/worker integration against an isolated database with mocked external services.
  Verify worker restart and queue interruption using the project's testable worker arrangement.
- Test migrations using a pre-feature database containing parser configurations and transactions.
  Verify no automatic approvals, preserved historical values, and explicit unknown provenance.
- Update setup and operational documentation for migrations, worker/API startup, manual sync,
  approval, recovery, reprocessing, and export. Keep Bruno examples aligned with final contracts.
- Record remaining limitations and actual validation results; do not claim semantic extraction
  accuracy or cross-email deduplication from fixture success.

## Acceptance criteria and verification

- [ ] First import reaches review; drafts cannot create transactions through any entry point.
- [ ] Review with explicit account choices creates valid transactions automatically.
- [ ] Repeat imports create no duplicates; new hints return to attention despite approved parsers.
- [ ] One malformed email does not block valid siblings; retries preserve successful work.
- [ ] Refresh/navigation/restart preserve saved review and durable workflow status.
- [ ] Draft regeneration does not change active rules or history; confirmed reprocessing preserves IDs.
- [ ] Ignore/restore works; incomplete current/legacy results stay outside normal export.
- [ ] Selected and filtered CSVs match exact records across pages with correct serialized values.
- [ ] Backend suite, Ruff, format check, strict Pyright, frontend build/type checks, and relevant browser
  suites pass; document any pre-existing failures separately with evidence.

## Exclusions

Do not add new product capabilities or redesign visuals during acceptance. Route discovered defects
to their owning task, add targeted regressions, and rerun only affected checks before final validation.
