# Test plan — release routing remains high-control

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Release wording pair with/without PR phrase and mixed “prepare release and review rollout” yields release/high/two gates/release+security review/release evidence/release-readiness | route unit tests and verification |
| P0 | Standalone explicit “review this pull request” stays review with ordinary review controls | route unit tests and verification |
| P0 | Generic feature task mentioning only “pull request” or “PR” stays feature intent with a write owner | route unit tests |
| P1 | Release-installer bugfix mentioning PR stays bugfix under existing precedence | route unit tests and verification |
| P1 | Prompt-order and release+PR variants preserve complete control fields | route unit tests and verification |

## Automated checks

- Unit: all 30 tests in `tests.test_repo_router` pass; the release/review/bugfix and bare-delivery-word matrix asserts expected route intent and controls.
- Integration: `python3 scripts/grok_verify.py --mode pr`.
- Contract: route schema v1 unchanged (no schema edits); `python3 scripts/grok_spec.py validate --gate --json` passes.
- Static: `python3 -m py_compile .grok-stack/adaptive_grok/router.py tests/test_repo_router.py` and `git diff --check` pass.

## Manual checks

- Compare root cause and acceptance table to issue #123.
- Confirm no edits to approval grant consumers, Trust CI, branch protection, or production actions.
