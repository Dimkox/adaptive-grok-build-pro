# Test plan — v2.0.18 artifact child

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Tracked ZIP matches the recorded digest and the sidecar text is exactly `<sha>  <name>` | `tests/test_manifest_package.py` delivered branch |
| P0 | Candidate claims bytes but not publication | `tests/test_project_state.py` local_candidate block |
| P1 | Identity literals unchanged from `R` | `tests/test_structure.py::test_version_identity_matches_readme` |
| P1 | Repository verification, secret scan and packaging checks | `python3 scripts/grok_verify.py --mode pr` |

## Automated checks

- Unit: the three coupled modules (89 tests OK on the frozen tree).
- Integration: `grok_verify --mode pr`; expect the documented issues #80/#101 (streaming analysis; the tracked pair now passes the local verifier) local-only red on the >10 MB tracked binary and disclose it.
- Contract: `tests/test_change_spec.py` for this package.
- Static: `ruff`, `bandit` as invoked by the verifier.

## Manual checks

- Re-check the dual-build digests from the build log before committing.
- Confirm `git diff --name-only` adds nothing outside `packages/`, the two test modules, the currency docs and this package.
