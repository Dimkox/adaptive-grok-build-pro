# Test plan — Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Version identity is coherent across `VERSION`, README H1, `Identity:` line, CHANGELOG top heading, ROADMAP product line and `adaptive_grok.__version__` (AC-001) | `tests/test_structure.py::test_version_identity_matches_readme` |
| P0 | Candidate is not published: `local_candidate.version` `2.0.17`, `published` false, null identities, and the `v2.0.17` ZIP+sidecar pair asserted absent (AC-003, `FORBID-001`) | `tests/test_manifest_package.py` candidate/published assertions |
| P0 | Published facts stay `v2.0.16` byte-for-byte and the twelve post-publication merges are recorded with re-derived check-run identifiers (AC-002, `INV-001`) | `tests/test_project_state.py` release and landing records |
| P1 | Bootstrap docs are truthful on a clean clone: only `v2.0.16` published, `2.0.17` in preparation, installed L5 services still on pre-#93 SHAs (AC-004) | `tests/test_project_state.py` + `release_review` report |
| P1 | Whole repository still verifies after the identity move (no unrelated literal left behind) | `python3 scripts/grok_verify.py --mode pr` on the frozen tree |

## Automated checks

- Unit: `python3 -m unittest tests.test_structure tests.test_project_state tests.test_manifest_package` (the lockstep trio), then the full root discovery `python3 -m unittest discover -s tests`.
- Integration: `python3 scripts/grok_verify.py --mode pr` (includes repository verification, doctor, packaging and secret scan).
- Contract: `tests/test_change_spec.py` for this package's typed spec; no OpenAPI/JSON-Schema/event contract files change.
- E2E: not applicable — no runtime, service or provider path is touched.
- Static analysis: `ruff` and `bandit` as invoked by the verifier; `compileall` over `trust-ci` is unaffected.

## Manual checks

- Re-derive each recorded merge commit, checked head and `check_run_id` from `git log` / `gh pr view` / the Trust CI store rather than copying from chat.
- Confirm `git show --stat HEAD` touches only the identity surface, `PROJECT_STATE.json`, the coupled tests and this package.
- Confirm no `packages/` entry appears in the diff (`A` owns those two files).
