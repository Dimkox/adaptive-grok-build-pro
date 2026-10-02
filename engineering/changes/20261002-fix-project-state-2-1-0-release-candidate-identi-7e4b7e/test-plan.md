# Test plan — Fix PROJECT_STATE 2.1.0 release candidate identity so the new source-only candidate has no artifact hashes while preserving the immutable 2.0.19 artifact record

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Published v2.0.19 remains immutable | `tests.test_project_state` |
| P0 | v2.1.0 remains source-only | state/manifest lockstep tests |

## Automated checks

- Unit: project-state and manifest tests.
- Integration: structure/state/manifest lockstep.
- Contract: change-spec gate validation.
- E2E: final PR verifier remains coordinator-owned.
- Static analysis: diff check.

## Manual checks

- Inspect the two identities for accidental field inheritance.
