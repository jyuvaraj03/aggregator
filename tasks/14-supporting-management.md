# 14 — Build supporting template, account, and sync management

Status: Not started

Dependencies: [03](03-account-resolution.md), [04](04-email-processing-state.md),
[10](10-workspace-navigation-and-sync.md), [11](11-parser-review-experience.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Provide maintenance controls without making them mandatory stops in routine processing.
The backend already has account/template reads; new tasks add mappings, versioning, and ignoring.

## Work and interfaces

- List templates with active/draft/ignored state, matching-email counts, remembered account mappings,
  and links to review/source emails. Avoid treating templates as another required wizard stage.
- Allow ignored templates to be restored, explaining that eligible pending emails resume processing
  while unapproved rules still require review.
- Provide account creation/renaming and mapping inspection/removal. Mapping removal affects future
  resolution, not existing transaction values. Explain blocked deletion for referenced accounts.
- Show sync configuration and the remembered import date with access to manual backfill. Clearly
  distinguish configured Gmail source from financial accounts.
- Reuse task 11's review interactions for draft edits, regeneration, and approval rather than creating
  a second approval path with different semantics.

## Acceptance criteria and verification

- [ ] Users can discover templates and account mappings without following the processing sequence.
- [ ] Restoring ignored templates resumes only eligible pending work.
- [ ] Mapping/account maintenance cannot silently rewrite or delete transactions.
- [ ] Setup labels make mailbox source and financial accounts unambiguous.
- [ ] Browser tests cover restoring templates, mapping removal, account rename/deletion conflicts,
  and navigation into existing review flows; run build/type checks.

## Exclusions

Account merging, manual template editing/splitting, provider credential editors, scheduled sync, and
visual-system design are outside scope.
