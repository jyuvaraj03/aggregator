# 10 — Build workspace navigation and manual sync experience

Status: Not started

Dependencies: [07](07-workflow-orchestration.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Establish the new product shell around user activities and durable progress.
The backend workflow from task 07 is the source of truth. The current frontend is throwaway and
must not be inspected or reused as a UX/design reference.

## Work and interfaces

- Provide Transactions, Needs attention, and Emails as primary destinations; supporting navigation
  exposes Templates, Accounts, and sync configuration. Later tasks own their destination contents.
- For first use, explain the configured Gmail source, show actionable missing-configuration guidance,
  request the import start date, and offer Sync emails. Do not require accounts before syncing.
- For returning users, open Transactions, retain sync settings, and offer the backend's default date
  with an earlier-date override for backfills.
- Display durable active-run status with named stages and actual counts. Link completion outcomes
  to relevant filtered destinations; distinguish no new emails from failed sync.
- Resume status after refresh/navigation and handle duplicate submissions, connection loss, and
  retryable service errors without suggesting successful work was lost.
- Expose configured-source/status information through a minimal backend read if task 07 does not
  already provide it; never expose credentials.

## Acceptance criteria and verification

- [ ] A first-time user can understand prerequisites and start sync without a financial account.
- [ ] Returning users can sync/backfill without triggering duplicate runs.
- [ ] Leaving or refreshing a page preserves active-run visibility and remembered settings.
- [ ] Outcomes provide meaningful next actions with no fake percentage progress.
- [ ] Navigation has accessible names, keyboard access, and useful empty/loading/error states.
- [ ] Build/type checks and browser tests cover first use, repeat sync, refresh, empty results,
  configuration failure, and partial processing failure.

## Exclusions

Visual-system design, parser review, transaction lists, attention lists, and Gmail OAuth setup flows
are not part of this task. Do not expose dead navigation as a finished destination.
