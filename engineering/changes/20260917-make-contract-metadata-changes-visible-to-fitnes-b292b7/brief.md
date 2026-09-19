# Make contract metadata changes visible to fitness (#120)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260917-make-contract-metadata-changes-visible-to-fitnes-b292b7`
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

The architecture fitness gate treats JSON Schema document `title` and `description` as irrelevant to contract changes. A semantics-bearing metadata-only edit is reported compatible with no finding, even though structural edits to the same contract are detected.

## Proposed outcome

Make JSON Schema root `title` and `description` changes visible as a distinct `changed_documentation` finding requiring review. Keep that finding separate from wire-shape compatibility; retain existing structural checks unchanged.

## Scope

### In scope

- Compare root JSON Schema `title` and `description` when a registered JSON Schema contract changes.
- Emit a stable metadata-specific review finding without calling it wire incompatible.
- Add metadata-only red/green tests and structural control tests.
- Document the distinction between documentation metadata review and structural compatibility.

### Out of scope

- OpenAPI or event contract behavior changes; these were not measured for this issue.
- Trust CI policy, deployed holdout, merge authority, or approval protocol changes.
- Treating arbitrary nested JSON Schema annotations as governed metadata.

## Constraints

- Metadata-only changes must no longer report an unqualified compatible/pass result.
- Existing schema-direction and structural compatibility checks remain intact.
- Existing event semantic comparison remains unchanged.
- Findings use the current fitness result shape; no receipt or route schema migration.
