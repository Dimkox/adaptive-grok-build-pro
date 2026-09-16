# Test plan — v2.0.17 published-release successor

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Published record equals the remote truth (tag object, merge, digests, check run) | `tests/test_project_state.py`, `tests/test_manifest_package.py` |
| P1 | Superseded release archived unchanged, history length four | `tests/test_project_state.py` prior_published_releases |
| P1 | No activation claim anywhere | docs sweep + `release_review` receipt |
| P1 | Identity surfaces consistent | `tests/test_structure.py` |

## Automated checks

- `python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package tests.test_change_spec` → 119 OK.
- `python3 scripts/grok_verify.py --mode pr` (expect the disclosed issue #80 blob-analysis red only).

## Manual checks

- `git ls-remote origin 'refs/tags/v2.0.17*'` peel matches `published_release.merge_commit`.
- `gh release view v2.0.17 --json assets` digests match the tracked files.
- `git diff --name-only` touches no code, script or package byte.
