# 06 — Approve a validated parser and process waiting emails

Status: Not started

Dependencies: [02](02-parser-preview-and-validation.md),
[05](05-approved-transaction-extraction.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Give approval a precise, enforceable meaning: the user activates the exact rules they inspected.
No current API separates saving parser configurations from approving them.

## Work and interfaces

- Add explicit approval accepting draft revision and validation identity. Require all field rules
  configured and at least one preview with valid core fields and a confirmed account.
- Reject stale draft approval. If the waiting email set changed, refresh validation and return the
  updated summary for review before approval; never present old counts as current.
- Atomically activate the approved immutable version, record approval metadata, and durably record
  that eligible waiting work must be dispatched. Reuse background extraction for execution.
- Allow approval when some emails fail validation or lack accounts; report how many can proceed and
  how many remain in Needs attention.
- Make repeated approval requests idempotent. If dispatch fails after activation, retain approval
  and expose retryable pending processing rather than claiming extraction completed.

## Acceptance criteria and verification

- [ ] The approved version exactly matches the reviewed revision.
- [ ] Incomplete configuration, no valid preview, and stale review produce actionable responses.
- [ ] Approval automatically queues eligible emails without requiring a second extraction action.
- [ ] Other emails retain specific blockers and existing transactions remain unchanged.
- [ ] Queue outages/retries cannot lose pending work, double-approve, or duplicate transactions.
- [ ] Approval/API tests cover partial readiness, stale state, repeat requests, and dispatch failure;
  update Bruno requests and run backend checks.

## Exclusions

Full sync orchestration and the browser review flow are handled by tasks 07 and 11.
