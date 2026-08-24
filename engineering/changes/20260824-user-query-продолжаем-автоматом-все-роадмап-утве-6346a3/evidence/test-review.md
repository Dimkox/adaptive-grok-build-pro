# Test review — M0.1 listener (route 6346a398114f)

**Agent:** test_reviewer (read-only)  
**Verdict:** **PASS**  
**Scope:** M0.1 host listener on compose project `adaptive-trust-ci`. The live bind is runtime (`127.0.0.1:18080` → container `8080`); it is **not** a new unit-test obligation. Characterization remains `trust-ci/tests/test_m0_invariants.py`. Parent: `python3 scripts/grok_verify.py --mode pr` **PASS** after M0.1 product edits. No regression claimed beyond that preflight.

## Adequacy vs this slice

M0.1 does not change API/worker Python. Adding a unittest that curls loopback would couple CI to Docker state and fail on hosts without the stack. That would be the wrong gate. Existing file-level invariants already freeze the published mapping string.

| Claim | Test | Status |
| --- | --- | --- |
| Compose project name `adaptive-trust-ci` | `test_compose_publishes_loopback_not_all_interfaces` | Covered |
| Host publish `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` | same | Covered; `trust-ci/compose.yaml` still contains that exact mapping |
| Must not publish `127.0.0.1:8080:8080` (SearXNG conflict) | same | Covered |
| Must not publish `0.0.0.0:8080` | same | Covered |
| Container healthcheck still hits in-container `http://127.0.0.1:8080/health/ready` | same (`assertIn` that URL) | Covered; host 18080 vs container 8080 is the intended split |
| No `.github/workflows` | `test_no_github_actions_workflows_tree` | Covered |
| API has no `GitHubClient` / `GitHubAppAuth` | `test_api_cannot_hold_github_app_or_client` | Covered |
| Worker still names `GitHubAppAuth` | `test_worker_uses_github_app_auth` | Covered |
| Spec/plan exist, check prefix, pinned SHA, no RSA PEM blob | `test_m0_spec_and_plan_exist` | Covered |
| Host named `claw`, not laptop | `test_m0_docs_name_claw_not_laptop` | Covered |
| Holdout forbids Actions + webhook App key | `test_holdout_example_forbids_github_actions` | Covered |
| Live `GET /health/ready` on 18080 | none (runtime) | **Out of unit-test scope.** Operator evidence: activation report / curl on `claw`. Do not treat unittest green as “listener is up.” |

## Characterization coverage

`test_m0_invariants.py` still matches the tree: seven methods (six original plus `test_m0_docs_name_claw_not_laptop`). No M0.1 product edit required a new failing test first: behavior of the in-tree compose contract did not change.

Gaps (accepted, not blocking this review):

- PEM substring check is RSA-header only (`BEGIN RSA PRIVATE KEY`).
- No assertion that `worker`/`docker-engine`/`runner-loader` stay stopped (process/compose profile, not source).
- `grok_verify` test count does not substitute for Trust CI unittests; keep `python3 -m unittest trust-ci.tests.test_m0_invariants` in PR evidence when that file is in the diff.

## Verification evidence

- Route required evidence: `verification`, `code_review`, `test_review`. This file is `test_review`.
- Parent reported `grok_verify --mode pr` **PASS** after M0.1 product edits. This agent did not re-run verify (read-only; no claim of a fresh fingerprint).
- Compose still publishes `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` with `name: adaptive-trust-ci`. Invariants therefore still match the 18080 default.
- No regression is claimed against prior M0.0 invariant set.

## Pass/fail

**PASS.** Existing `test_m0_invariants` still encode compose 18080; the listener is runtime, not a missing unit test; no extra regression is asserted.

Local receipts and this report are preflight only. Merge remains the App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>` on the exact PR head SHA.
