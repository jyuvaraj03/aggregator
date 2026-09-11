# 11 — Build results-and-rules parser review

Status: Not started

Dependencies: [02](02-parser-preview-and-validation.md), [03](03-account-resolution.md),
[04](04-email-processing-state.md), [06](06-parser-approval.md),
[10](10-workspace-navigation-and-sync.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Help a user decide whether a template's generated rules produce trustworthy transactions.
Use the new version, preview, account, and approval APIs, not the throwaway frontend.

## Work and interfaces

- Present source email, proposed typed transaction, and inspectable field rules together. Selecting
  a field reveals its source parameter(s), constant, or explicit missing value.
- Start with the representative examples from task 02; allow every matching email to be inspected.
  Distinguish examples inspected from all-email validation and report failures clearly.
- Edit extracted parameters in order, constants, or missing rules without code. Refresh previews
  without transaction creation; persist drafts explicitly and warn before losing unsaved edits.
- Show account hints beside user-controlled account selection and inline creation. Remembering a
  mapping is an explicit choice; distinguish individual assignments from future mappings.
- Provide Approve and process, Regenerate draft, Review later, and Ignore this template. Explain
  approval's eligible and blocked counts; handle stale previews without discarding user work.
- Approval starts processing automatically. Retain context when moving to the next review or an
  affected email, and make saved drafts recoverable after refresh.

## Acceptance criteria and verification

- [ ] Users can trace and correct each field without reading parser JSON or code.
- [ ] Users explicitly choose accounts; absent/new hints cannot inherit unrelated selections.
- [ ] Approval readiness reflects configuration, validation, and account requirements.
- [ ] Regeneration preserves approved rules and handles provider failure without losing usable work.
- [ ] Deferral preserves drafts; ignoring explains future matching-email behavior and is reversible.
- [ ] Browser tests cover correction, multiple accounts, stale approval, partial validity, regeneration
  failure, navigation/refresh, and keyboard operation; run build/type checks.

## Exclusions

Bulk approval without review, full code editors, visual-system decisions, and historical replacement
confirmation are outside this task.
