# Test review — M0 invariants (`test_m0_invariants.py`)

- **Route:** `3722694830f7`
- **Change:** `20260824-user-query-read-agents-md-decisions-md-mistakes-372269`
- **Reviewer:** `test_reviewer` (read-only)
- **Verdict:** **pass with residual characterization gaps**
- **This review is not merge authority.** Local unittest + `grok_verify --mode pr` are preflight only.

## Scope inspected

`trust-ci/tests/test_m0_invariants.py` (six `M0InvariantTests` methods) against the M0 characterization checklist:

| Required coverage | Test | Adequacy |
|---|---|---|
| Spec and plan exist | `test_m0_spec_and_plan_exist` | Covered: both paths `is_file()`, plus check-name prefix `adaptive-trust-ci/verified@`, pinned main SHA `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`, plan phases `M0.0`/`M0.3` |
| No `.github/workflows` | `test_no_github_actions_workflows_tree` | Covered: tree must not exist at repo root |
| API has no `GitHubClient` / `GitHubAppAuth` | `test_api_cannot_hold_github_app_or_client` | Covered as **source substring** on `trust-ci/src/adaptive_trust_ci/api.py` |
| Worker has `GitHubAppAuth` | `test_worker_uses_github_app_auth` | Covered as **source substring** on `worker.py` |
| Compose `127.0.0.1` not `0.0.0.0` | `test_compose_publishes_loopback_not_all_interfaces` | Covered for **exact** `127.0.0.1:8080:8080` and absence of `0.0.0.0:8080:8080` |
| Holdout forbids Actions | `test_holdout_example_forbids_github_actions` | Covered via example holdout `validate.py` strings (Actions forbidden + webhook must not hold App key) |
| No PEM material in spec/plan | `test_m0_spec_and_plan_exist` | Covered only for `BEGIN RSA PRIVATE KEY` |

## Verification evidence (parent-run; not re-executed here)

- `PYTHONPATH=trust-ci/src python3 -m unittest trust-ci.tests.test_m0_invariants` → **6 OK**
- `python3 scripts/grok_verify.py --mode pr` → **PASS**

These are local fingerprints of the working tree, not the GitHub App policy-epoch check `adaptive-trust-ci/verified@<policy-sha12>` on an exact PR head SHA.

## Characterization quality

Strengths:

- Tests are **static invariants** (file existence + forbidden/required substrings). That is appropriate for M0 policy-as-code: they fail if someone reintroduces Actions, binds the App key into the webhook process, or publishes the API on all interfaces.
- Spec/plan tests pin **identity** (check-name shape + current main SHA) so a generic placeholder spec cannot satisfy M0.0.
- Holdout example encodes two independent trust rules (no Actions; API without App key), matching the split-process design.

Gaps (do not fail this review, but they are not equivalent to live Trust CI):

1. **PEM:** only `BEGIN RSA PRIVATE KEY`. EC (`BEGIN EC PRIVATE KEY`), PKCS8 (`BEGIN PRIVATE KEY`), OpenSSH (`BEGIN OPENSSH PRIVATE KEY`), or base64 blobs without that header would not fail.
2. **API/worker:** substring on a single file, not AST/import graph. `GitHubClient` in comments, or App auth imported via another module into the API process, would not be detected. Worker test does not require that `GitHubAppAuth` is constructed or used for Check Runs.
3. **Compose:** only port `8080` mapping. Other services could still bind `0.0.0.0`.
4. **Actions:** only `.github/workflows` existence, not workflow YAML elsewhere or `uses: actions/` in docs.
5. **Holdout:** example tree, not the **deployed** holdout bundle Trust CI actually runs.
6. **No live drills** in this file: App installation, Check Runs, webhook deliveries, branch protection, PostgreSQL durable state.

## Adequacy ruling

For **M0 local characterization of the in-repo contract**, the six tests match the requested checklist and the reported 6 OK run is consistent with the file. Residual gaps are expected for static tests and must be closed by deployed holdout + App-owned exact-SHA Check Run, not by treating this unittest as merge authority.

**Local test review: pass.** Do not merge on this receipt.
