# 13 — Build transaction inspection, correction, and CSV download

Status: Not started

Dependencies: [08](08-transaction-reprocessing.md), [09](09-transaction-query-and-export.md),
[10](10-workspace-navigation-and-sync.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Make completed transactions immediately usable, explainable, and exportable.
Use backend query, provenance, account-correction, and reprocessing contracts as the source of truth.

## Work and interfaces

- Build paginated transaction browsing with date, account, and direction filters and matching totals.
  Retain filters and selection while inspecting records; clearly distinguish page selection from
  all matching results. Clear explicit selection when filters change.
- Show source email, applied field rules, account, and parser version in detail. Display historical
  unknown provenance explicitly and keep incomplete legacy results outside normal export selection.
- Offer individual account correction separately from remembering a mapping. Link rule corrections
  to template review; parser approval alone must not suggest historical rows were updated.
- Provide Reprocess existing transactions with explicit scope, before/after preview, affected count,
  and confirmation. Surface stale preview and partial failure without hiding unchanged records.
- Offer Selected transactions and All matching current filters for CSV export with accurate counts
  across pages, downloading the fixed snapshot produced by task 09.
- Explain that downloads do not remove records or prevent repeated export. Do not add a mandatory
  second transaction-approval step.

## Acceptance criteria and verification

- [ ] Users can find transactions and trace their values to approved rules/source evidence.
- [ ] Account correction and historical reprocessing have explicit, distinct scopes.
- [ ] Reprocessing requires reviewing changes; invalid/stale replacements are explained.
- [ ] Selected/filtered downloads contain the requested records beyond the visible page.
- [ ] Browser tests cover filters, selection, downloads, empty/error states, account correction,
  historical provenance, and reprocessing; run build/type checks.

## Exclusions

Direct arbitrary editing of financial fields, JSON exports, external integrations, and visual-system
design are outside scope.
