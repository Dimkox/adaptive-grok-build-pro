# Test plan — Fix issue157 repository language classifier: bounded Swift and other language signal detection, symlink-safe manifests, truncation and unknown reporting without suppressing detected signals.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Symlink manifests/root/subtrees, FIFO, symlink swap, file mutation, each scan/read budget and exact-bound inventory | tests/test_repo_language_disclosure.py |
| P0 | Weak Swift masked Python; confirmed Swift masked Kotlin; canonical Swift evidence | tests/test_repo_language_disclosure.py |
| P1 | Legacy manifests/Node scripts/Bitrix; case conflict/variant; generated/vendor/unknown/empty/unreadable | dedicated classifier tests plus tests/test_repo_router.py |
| P1 | Example-tree PHP remains detected-only; root/src/app/local/public/www PHP still confirms; real demo API-only route remains compatible | dedicated classifier regressions plus tests/test_demo.py |

## Automated checks

- Unit/integration: `taskset -c 6-7 python3 -m unittest tests.test_repo_language_disclosure tests.test_repo_router -q`; maximum two focused workers.
- Parallel adjacent qualification after the verifier-discovered compatibility repair: pinned pytest/xdist, two workers, worksteal, classifier/router/demo modules; exact command and RED/GREEN results in evidence/classifier-compatibility-followup.md. No diagnostic run substitutes for aggregate full verification.
- Contract: validate this typed package and additive profile expectations. No HTTP/event schema changed.
- E2E: no external execution; focused existing router tests exercise the consuming boundary.
- Static analysis: `python3 -m ruff check .grok-stack/adaptive_grok/repo.py tests/test_repo_language_disclosure.py` and `git diff --check`.
- Full verifier and independent code/test reviews: coordinator owns `python3 scripts/grok_verify.py --mode pr` and fingerprint-bound receipts after final integration.

## Manual checks

- Read the actual scoped diff and source identity before handoff. Historical repo157 evidence is never reused as current acceptance.
