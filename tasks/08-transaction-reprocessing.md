# 08 — Preview and confirm historical transaction changes

Status: Not started

Dependencies: [02](02-parser-preview-and-validation.md),
[05](05-approved-transaction-extraction.md), [06](06-parser-approval.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Let users deliberately apply corrected rules to existing transactions without silent changes.
Current extraction skips emails already having transactions; parser edits do not rebuild them.

## Work and interfaces

- Add a read-only reprocessing preview for explicitly selected existing transactions or an explicit
  template scope, using the selected current approved version and account resolutions.
- Return affected count, before/after values, changed fields, and per-email failures. Freeze IDs,
  source transaction revisions, parser version, and account decisions in the preview identity.
- Require explicit confirmation of that preview before replacing valid results in place, preserving
  transaction IDs. Reject stale previews and provide refreshed changes for another confirmation.
- Keep failed results unchanged and actionable. Record processing outcome and updated provenance;
  retain enough previous/replacement information to explain the correction.
- Repeated confirmation must not duplicate transactions or apply a different scope/version.

## Acceptance criteria and verification

- [ ] Preview, rule editing, and parser approval alone do not change historical transactions.
- [ ] Confirmation changes only the previewed valid records, retaining their transaction IDs.
- [ ] Stale data, parser, or account decisions require another review.
- [ ] Partial failure leaves failed records intact and reports which changes were applied.
- [ ] Focused reprocessing/API tests cover no-op changes, invalid replacements, stale confirmation,
  retries, and provenance; update Bruno examples and run backend checks.

## Exclusions

Automatic historical rewrites, transaction merging, and full accounting-ledger versioning are outside
scope. Browser confirmation is task 13.
