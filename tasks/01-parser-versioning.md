# 01 — Separate parser drafts from approved versions

Status: Not started

Dependencies: None. Read the [shared rules](README.md#shared-implementation-rules) and
[UX specification](ux-spec.md).

## Objective and context

Make reviewed parser rules stable while users edit or regenerate replacements.
`src/aggregator/field_parsers.py` currently replaces stored rules directly; models have no approval
state. Generation uses one example email and saves through the replacement operation.

## Work and interfaces

- Add ordered migrations for versioned parser configurations, draft revision identity, approval
  metadata, and the template's active approved version. Approved versions are immutable.
- Change generation and replacement to save drafts. Editing active rules starts a draft; generation
  never changes the active version. Preserve the previous draft if regeneration fails.
- Expose active and draft versions separately through parser reads and mutation responses. Include
  revision identity so later preview and approval requests can reject stale edits.
- Migrate existing rules into unapproved drafts. Preserve historical transactions without inventing
  approval or parser provenance.
- Preserve field validation and atomic replacement semantics; update API examples and boundary docs.

## Acceptance criteria and verification

- [ ] Editing or regenerating a draft leaves approved rules and transactions unchanged.
- [ ] Invalid or failed generation/replacement does not destroy a usable draft or active version.
- [ ] Concurrent stale draft writes fail explicitly rather than overwriting newer edits.
- [ ] Existing data migrates without loss and no parser becomes approved automatically.
- [ ] Parser configuration, generation, API, and migration tests cover these behaviors; run the
  backend checks described in the shared rules.

## Exclusions

Approval actions, typed previews, extraction changes, and browser implementation belong to later
tasks. Tests may create approved-version fixtures without exposing a production approval shortcut.
