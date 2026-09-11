# 12 — Build the attention queue and email inspection

Status: Not started

Dependencies: [04](04-email-processing-state.md), [07](07-workflow-orchestration.md),
[10](10-workspace-navigation-and-sync.md), [11](11-parser-review-experience.md).
Read the [UX specification](ux-spec.md) and [shared rules](README.md#shared-implementation-rules).

## Objective and context

Turn processing exceptions into a short, persistent list of resolvable user tasks.
Consume the grouped attention and email-status contracts; do not derive durable state in the browser.

## Work and interfaces

- Group attention by template and shared reason, with affected-email counts and actions to review
  rules, assign accounts, retry failed work, or ignore a template.
- Prioritize actionable blockers that release the most emails, using stable ordering for ties.
  Show unresolved-account and validation details without generic "skipped" buckets.
- Provide email browsing/filtering by processing status and template, source detail, and links to
  review and resulting transactions. Preserve filters and paging during detail navigation.
- Show the failing field/reason and source evidence; retry only eligible failed/pending work.
  An unresolved prerequisite should lead to its remedy, not a futile retry.
- Handle all-clear, no imported emails, active processing, partial failure, and service-unavailable
  states distinctly. Ignored emails remain discoverable through filters.

## Acceptance criteria and verification

- [ ] Queue counts match affected emails and distinguish shared from individual problems.
- [ ] Every attention item explains what happened and offers an appropriate next action.
- [ ] Resolving an account or approving rules updates the queue as processing proceeds.
- [ ] Source inspection and back navigation preserve context; imported HTML is never executed.
- [ ] Browser tests cover grouped failures, unknown accounts, retries, ignoring, pagination, empty
  states, and refresh; run build/type checks.

## Exclusions

Manual template splitting/merging, mailbox editing, visual-system decisions, and cross-email
transaction duplicate detection are outside scope.
