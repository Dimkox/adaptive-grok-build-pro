# Test plan — Build v2.0.19 artifact child from merged release-sync 3f41be92

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Two builds from merged release-sync `3f41be92` are byte-identical and sidecar matches ZIP | package command output, verification receipt |
| P0 | Candidate state names source parent/tree and both artifact digests while publication remains pending | project-state and manifest tests |
| P1 | Diff/archive contains no secret, deployment, Trust policy or GitHub Actions path | security review |
| P1 | README/START_HERE/CHANGELOG/roadmap/handoff/packages README agree on R/A boundary | release review |

## Automated checks

- Unit: `python3 -m unittest tests.test_project_state tests.test_structure tests.test_manifest_package`
- Integration: `python3 scripts/grok_verify.py --mode pr` (includes factory and PostgreSQL exit profiles)
- Contract: `python3 scripts/grok_spec.py validate --change-id 20260924-build-v2-0-19-artifact-child-from-merged-release-09407b`
- E2E: not applicable; no runtime or deployment path is changed.
- Static analysis: verifier secret scan, diff check, architecture/governance checks.

## Manual checks

- Confirm no `v2.0.19` tag or GitHub Release is claimed before the artifact-child merge and separate grants.
