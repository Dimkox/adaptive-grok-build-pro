# Test plan — Fix issue 95: enforce repository and verifier-source identity in grok_verify; add a cross-worktree regression test for external script copies.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Invoke source checkout's verifier with a different target checkout as cwd; require nonzero identity diagnostic before target runtime/receipt creation. | `tests.test_structure.StructureTests.test_grok_verify_rejects_script_from_another_repository` |
| P1 | Verify root identity accepts two paths resolving to the same checkout without launching verification. | `tests.test_structure.StructureTests.test_grok_verify_root_identity_accepts_same_checkout` |

## Automated checks

- Unit: focused subprocess regression above.
- Integration:
- Contract:
- E2E:
- Static analysis:

## Manual checks

- This identity guard runs before `verify()`; existing verification suites cover unchanged verifier behavior.
