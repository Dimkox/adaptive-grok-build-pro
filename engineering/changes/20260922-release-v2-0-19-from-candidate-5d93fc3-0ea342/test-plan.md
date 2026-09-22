# Test plan — Release v2.0.19 from candidate 5d93fc3

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Identity, state and published v2.0.18 immutability | `tests/test_structure.py`, `tests/test_project_state.py`, `tests/test_manifest_package.py` |
| P0 | Exact source verifier and current-fingerprint reviews | `verification`, `code_review`, `test_review`, `security_review`, `release_review` |
| P0 | Two package builds from one sealed tree are byte-identical | package provenance report and sidecar digest |
| P0 | Tag and GitHub Release target the artifact-child merge | release review and external App-owned check |
| P1 | Missing check/grant or changed head fails closed | gate/grant records and release review |

## Automated checks

- Unit: coupled release/state/manifest unittest modules.
- Integration: `python3 scripts/grok_verify.py --mode pr`.
- Contract: change-spec and package manifest validation.
- E2E: external Trust CI exact-head check; no production E2E is claimed.
- Static analysis: route-selected verifier profile and independent reviews.

## Manual checks

- Confirm the ZIP digest equals the sidecar and the tag target equals the artifact-child merge.
- Confirm `v2.0.18` remains immutable and no deployment/activation wording is introduced.
