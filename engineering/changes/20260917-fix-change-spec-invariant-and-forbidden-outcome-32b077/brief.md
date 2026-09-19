# Fix typed change-spec criterion coverage (#125)

## Problem

The local gate currently treats nonempty evidence as a gate requirement only for acceptance criteria. Invariants and forbidden outcomes are omitted from `criterion_coverage()`, and `_change_specs()` reports coverage metadata without failing for `unmapped_ids`. This allows a typed change to pass while its safety constraints have no evidence references.

## Bounded outcome

Require at least one evidence reference for every AC, INV, and FORBID in gate mode. Coverage and summary output must expose category-aware declared and mapped totals plus unmapped stable IDs and an explicit all-category aggregate, while preserving the existing AC-only projection and historical summary fields for compatibility. The change-spec verification check must fail with actionable findings when any criterion is unmapped. Draft mode stays descriptive. Do not extend this change into proof that a referenced test name exists, provider evidence is authentic, or any local receipt replaces Trust CI.

## Compatibility boundary

The signed Trust CI `criterion_coverage` envelope currently models AC-only coverage. Preserve its v1 wire meaning and existing AC-only signature verification in this PR unless an independent deployed-policy change is authorized. Callers preparing that v1 field must use `attestation_criterion_coverage(spec)`; `criterion_coverage(spec)` is category-aware local metadata and is not a signed-envelope payload. Update the checked-in Trust CI source/holdout only if the implementation can remain wire-compatible; document any live rollout dependency as external evidence, not as completed by local tests.
