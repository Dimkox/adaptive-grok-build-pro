# Proposed design — reviewable contract documentation metadata

## Decision for human approval

Choose issue #120 option 1 for a bounded first change: compare root JSON Schema `title` and `description` and emit a distinct stable `changed_documentation` finding. A changed description is reviewable contract metadata, but the result must not claim that wire shape is incompatible. The existing fitness result shape remains unchanged; the category fails with a clear metadata-review finding so the change cannot pass silently.

## Compatibility behavior

- Metadata-only change to root `title` or `description`: `contract_compatibility` reports `changed_documentation` and requires review.
- Structural-only or combined changes: run existing directional compatibility checks unchanged; preserve existing findings/status and include any metadata finding separately.
- No effective document change: existing `pass` behavior remains.
- Existing `event` semantic comparison is unchanged.
- OpenAPI and nested annotations are explicitly unmeasured and out of scope; do not infer behavior for them.

## Implementation boundary

Documents are already loaded, digested, and classified as changed; the information is dropped in the JSON Schema comparator. Preserve preflight/unsupported checks and comparison budgets. Add one stable reason code with tests for metadata-only, structural-only control, combined change, both directions, and unchanged documents. Do not change Trust CI, receipt schema, route schema, or deployed policy.

## Recovery

Rollback is a source revert. The new fail-closed finding may require existing contract prose edits to receive architectural review; no external side effect is introduced.
