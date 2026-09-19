# Code review: #125 final tree

Status: **PASS** — no remaining code-review findings in the requested areas.

## Review results

- **Fail-closed gate behavior:** `_semantic_errors()` now requires nonempty evidence for AC, invariants, and forbidden outcomes under gate validation, and still rejects malformed or unsupported references. `validate_spec(..., gate=False)` now correctly exposes draft validation for the in-memory adapter; the prior implementation ignored that argument there. `_change_specs()` independently rejects unmapped IDs in each category for non-exempt PR/release gates.
- **Invalid-spec metadata:** `_change_specs()` loads parseable specs and records category-aware coverage even when semantic validation has already returned errors. It then appends unmapped-category findings, sets `valid=False`, and retains the complete error list. Digest/fingerprint are emitted only when validation and coverage checks have no errors. Unparseable/unsafe specs correctly cannot produce semantic coverage.
- **Trust CI v1 attestation contract:** the existing strict wire contract remains exactly `{spec_count, criterion_total, criterion_mapped, unmapped_ids}` and AC-only. New `attestation_criterion_coverage()` returns exactly that shape; its regression passes the adapter output through Trust CI's strict `normalize_criterion_coverage()`. Category-aware local coverage is kept separate in `criterion_coverage()` and does not change any Trust CI source, signed envelope, or holdout in this diff. Existing signatures therefore retain their original payload semantics.
- **Failure paths:** malformed references still fail the validator even if the descriptive coverage view counts a nonempty evidence list as mapped; invalid records do not receive a fingerprint. No fail-open path found.

## Scope note

Trust CI's runner derives coverage using its own data-only parser and continues to emit AC-only v1 coverage. The new adapter is an explicit compatibility API and is directly tested against Trust CI's strict normalizer; it does not alter the deployed or checked-in Trust CI signing path.

## Evidence

Read-only review of the final diff against route base `2f66ba6`, surrounding spec validation and local verification, the Trust CI v1 schema/model, and call sites. No files changed; tests were not run by this read-only reviewer.
