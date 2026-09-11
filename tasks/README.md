# Email-to-transaction UX backlog

Implement the [accepted UX specification](ux-spec.md) through independently reviewable tasks.
This directory is a backlog, not evidence that the described capabilities already exist.

## Picking up a task

1. Read the UX specification and the task's prerequisites.
2. Choose a task whose dependencies are complete; set its status to `In progress` and add an owner.
3. Inspect current backend contracts and repository instructions before changing code.
4. Implement the task, its focused regression coverage, and required documentation.
5. Check acceptance criteria, record verification commands/results and the PR or commit, then set
   status to `Done`. Use `Blocked` with a concrete reason when a prerequisite is unavailable.

Each task owns its implementation tests. Task 15 verifies integration rather than deferring testing.
Keep completion status in task files; this index is the dependency map.

## Tasks and dependencies

| ID | Task | Depends on |
| --- | --- | --- |
| 01 | [Parser versioning](01-parser-versioning.md) | — |
| 02 | [Parser preview and validation](02-parser-preview-and-validation.md) | 01 |
| 03 | [Account resolution](03-account-resolution.md) | — |
| 04 | [Email processing state](04-email-processing-state.md) | — |
| 05 | [Approved transaction extraction](05-approved-transaction-extraction.md) | 01, 03, 04 |
| 06 | [Parser approval](06-parser-approval.md) | 02, 05 |
| 07 | [Workflow orchestration](07-workflow-orchestration.md) | 04, 05, 06 |
| 08 | [Transaction reprocessing](08-transaction-reprocessing.md) | 02, 05, 06 |
| 09 | [Transaction query and export](09-transaction-query-and-export.md) | 05 |
| 10 | [Workspace navigation and sync](10-workspace-navigation-and-sync.md) | 07 |
| 11 | [Parser review experience](11-parser-review-experience.md) | 02, 03, 04, 06, 10 |
| 12 | [Attention and email experience](12-attention-and-email-experience.md) | 04, 07, 10, 11 |
| 13 | [Transactions and export experience](13-transactions-and-export-experience.md) | 08, 09, 10 |
| 14 | [Supporting management](14-supporting-management.md) | 03, 04, 10, 11 |
| 15 | [End-to-end acceptance](15-end-to-end-acceptance.md) | 11, 12, 13, 14 |

Suggested execution waves: **01/03/04 → 02/05 → 06/09 → 07/08 → 10 → 11/13 → 12/14 → 15**.
Tasks in the same wave can be worked on independently after their prerequisites finish.
Coordinate migration numbering and edits to shared models/API schemas across concurrent work.

## Shared implementation rules

- The UX specification is the product contract. Do not adopt the throwaway frontend as a design
  reference. Inspect runtime/build configuration only when needed to implement the replacement.
- These tasks specify behavior and information architecture, not colors, typography, or layouts.
- Keep routes thin, application behavior in core modules, and persistence behind existing boundaries.
- Add ordered migrations for persisted changes. Use isolated databases for tests and migration checks.
- Update Bruno requests and response examples when API contracts change; document the resulting
  interface in the task's completion notes for downstream implementers.
- Preserve emails and historical transactions during migration. Existing parser configurations become
  unapproved drafts; historical transactions retain their values and have explicit unknown provenance.
  Do not imply historical transactions were generated with reviewed rules.
- Missing approval must fail closed in extraction, including legacy action endpoints. Roll out the
  backend prerequisites together before enabling automated processing in a running installation.
- Run focused pytest coverage, Ruff checks/format checks, and strict Pyright for backend changes.
  For browser work, run the chosen frontend's build/type checks and relevant interaction tests.
- Mock Gmail/model providers, avoid real mailbox/model calls in tests, and never commit secrets or
  the local database.

## Completion notes template

Append this to each completed task:

```text
Owner:
PR/commit:
Implemented behavior and API contracts:
Migrations/configuration:
Verification commands and results:
Remaining limitations:
```
