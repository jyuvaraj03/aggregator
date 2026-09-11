# 02 — Preview and validate parser drafts

Status: Not started

Dependencies: [01](01-parser-versioning.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Let users verify real transaction results before approval without creating transactions.
Current parser snapshots in `src/aggregator/field_parsers.py` show one example's resolved strings.
Typed conversion currently lives in `src/aggregator/transaction_extraction.py`.

## Work and interfaces

- Share typed conversion and field validation between preview and extraction; show exactly the same
  date, amount, and direction in both. Require amount, currency, date, and direction; expose account
  assignment as a separate readiness condition consumed by tasks 03 and 06.
- Add non-persisting preview operations for a draft revision or proposed unsaved rules. Return email
  identity, typed values, per-field rule/parameter/constant provenance, missing values, and errors.
- Provide up to five deterministic examples covering oldest, newest, then distinct account hints,
  filling remaining slots in received-date/ID order. Allow paginated access to all matching emails.
- Validate all currently waiting emails; return totals, per-email failures, revision identity, and
  the validated email-set identity. Separate sample inspection from validation counts.
- Include all seven field configurations in completeness checks. Explicitly missing optional fields
  are configured; unresolved core fields are not valid results.

## Acceptance criteria and verification

- [ ] Preview creates no transactions and does not activate or save rules implicitly.
- [ ] Preview values match extraction conversion, including date and decimal edge cases.
- [ ] Every displayed field has traceable provenance or an explicit missing/error state.
- [ ] Samples handle zero, one, fewer than five, and many emails without duplicates.
- [ ] One bad email does not suppress other previews or misstate validation totals.
- [ ] Focused representation/conversion/API tests cover invalid rules and stale revisions; update
  Bruno examples and run backend checks.

## Exclusions

Account inference, approval, review UI, and guarantees of semantic correctness based solely on
successful validation are outside this task.
