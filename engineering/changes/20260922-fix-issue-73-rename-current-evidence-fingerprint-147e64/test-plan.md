# Test plan — Fix issue #73: rename current evidence fingerprint fields that trigger GitGuardian secret heuristics while preserving historical evidence immutability and schema/test compatibility.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Prove the flagged key is historical-only and preserve exact bytes | Analysis report |
| P0 | New grants emit only `grant_binding_digest` | `test_new_grant_uses_neutral_binding_digest_key` |
| P0 | Legacy grants remain valid and conflicting dual fields fail closed | Two policy migration tests |
| P1 | Historical fixtures remain byte-identical | SHA-256-pinned history regression |

## Automated checks

- Unit: focused policy and history tests.
- Integration: full `tests.test_policy` and `tests.test_history` modules.
- Contract: typed change-spec validation and route-selected verification.
- E2E:
- Static analysis: read-only field inventory in `evidence/analysis-repo_explorer.md`.

## Manual checks

- External GitGuardian result/allow-list must be validated outside the agent environment.
