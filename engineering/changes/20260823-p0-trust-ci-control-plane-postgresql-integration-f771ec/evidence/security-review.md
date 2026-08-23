# Security review — `2865fdc`

**PASS**

Route: `f771ecaf458d` (intent=`review`, risk=`medium`, `write_agent: null`)  
Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Object reviewed: `2865fdc632860534c8ffc61aa9981844a0685b5d` (`fix: enqueue draft PRs and prove live PostgreSQL Trust CI state`) vs parent `04348dbde391eaccb574c96740e2fa7b2fa9825a`  
Replay on origin: the same patch was later rebased as `dbace962d74795fe3b18c2b67b0698b74cc4a444` onto `bf63f8af`. Product-security conclusions below apply to both SHAs.  
Reviewer: `security_reviewer` (read-only except this report; listed in `allowed_agents`)  
Inspected: active route, change package, `webhooks.py` / `api.py` / `worker.py` / `github.py` / `settings.py` / `policy.py` / `cli.py` / holdout / compose / env examples / gitignore / structure tests, GitHub commit patch for `dbace96`. `.env` was not opened as evidence. No push, merge, deploy, webhook registration, GitHub App mutation, or `branch-protect`.

---

## Verdict in one screen

Draft pull-request webhooks now enqueue jobs so draft PR `#2` can receive the App-owned check. That is a parser change, not an authz bypass. HMAC is still verified on the raw body **before** JSON parse; allowlist still returns HTTP 403; the API still cannot publish a Check Run; no private keys or GitHub Actions land in this commit; branch protection is still only a CLI payload and is **not** applied.

| Required confirmation | Result |
| --- | --- |
| Draft webhook enqueue still HMAC-verified and allowlisted | **PASS.** `parse_pull_request_event` no longer returns `None` for `draft=true` except via the existing action filter. `POST /webhooks/github` still calls `verify_webhook_signature` first (`hmac.compare_digest`, SHA-256, 64-hex), then `policy.allows_repository`. Invalid HMAC → 401. Foreign repo → 403. Tests: `test_valid_signature_verifies`, `test_invalid_webhook_signature_is_rejected`, `test_disallowed_repository_is_rejected`, `test_draft_pull_request_is_enqueued`. |
| API still cannot publish checks | **PASS.** `api.py` does not import `GitHubClient` / `GitHubAppAuth`. Ready/webhook/approval responses still set `status_publisher=worker-github-app`. Holdout continues to require that split. Worker remains the only Checks publisher. |
| No private keys committed | **PASS.** Diff has no PEM, App key, webhook secret, admin token, or filled `trust-ci/env/*.env`. Examples stay `REPLACE_WITH_*`. `.gitignore` still covers `.env`, `*.pem` / `*.key`, `trust-ci/env/*.env`, `trust-ci/runtime/*`. |
| No GitHub Actions | **PASS.** `.github/` absent. Diff adds no workflow. `test_no_github_actions_workflow_exists` and `test_repository_contains_no_github_actions_workflow` still lock the ban. |
| Branch protection still not applied in this commit | **PASS (correct).** Diff only renames `normalized_name` → `status_context` in `branch_protection_payload` so the holdout string-match works, and drops quotes around a docs placeholder. No `TRUST_CI_GITHUB_ADMIN_TOKEN`, no GitHub `PUT …/protection` from this commit, no App ID in tree. |

**Authz** for this slice is HMAC + repository allowlist + worker-only App key. **Secrets / PII** are not introduced. **Tenant isolation** remains policy allowlist on one PostgreSQL database. **Irreversible** `branch-protect` / merge / GHA restore did not happen and must not happen until the App-owned check is observed on an exact SHA.

---

## 1. What `2865fdc` is

| Probe | Value |
| --- | --- |
| Subject | `fix: enqueue draft PRs and prove live PostgreSQL Trust CI state` |
| Parent | `04348db` |
| Later replay | `dbace96` on `feat/trust-ci-control-plane` (rebase onto `bf63f8af`) |
| Product security delta | enqueue drafts; named-volume Postgres restart drill; holdout-aligned `status_context`; baseline test repairs |
| Not in this commit | GitHub App creation, webhook registration, image pins, deploy, `branch-protect`, merge of PR `#2` |

Product files that matter for this review:

| Path | Change |
| --- | --- |
| `trust-ci/src/adaptive_trust_ci/webhooks.py` | Remove `if pull_request.get("draft") and action != "closed": return None` |
| `trust-ci/tests/test_webhooks_github.py` | `test_draft_pull_request_is_ignored` → `test_draft_pull_request_is_enqueued` |
| `trust-ci/src/adaptive_trust_ci/github.py` | `normalized_name` → `status_context` in protection payload (holdout match) |
| `trust-ci/compose.test.yaml` | Named volume `trust-ci-pgtest-data` instead of tmpfs; drill cleanup still `down --volumes` |
| `trust-ci/config/policy.example.json` | Example holdout digest updated to match `holdout.example` |
| Tests / docs / change package | Baseline repairs, decisions, analysis; no live secrets |

`api.py` is **not** in the diff. Intake authz is unchanged around the parser.

---

## 2. Required confirmations

### 2.1 Draft enqueue is still HMAC-verified and allowlisted

Intake order in `create_app` / `github_webhook`:

1. Read raw body.
2. `verify_webhook_signature(settings.webhook_secret, body, X-Hub-Signature-256)`.
3. `parse_pull_request_event`.
4. `active_policy.allows_repository` → HTTP 403 if not listed.
5. Closed → `cancel_pr`. Else enqueue. Kill switch still 503s new jobs.

HMAC details (unchanged):

- Empty secret → `WebhookError` (API settings require `TRUST_CI_WEBHOOK_SECRET`).
- Header must be `sha256=` + 64 hex; otherwise reject **before** `compare_digest` (length-mismatch side channel avoided).
- `hmac.compare_digest` on hex SHA-256 of the **raw** body, so flipping `draft` without the secret fails 401.
- Invalid HMAC is HTTP 401, same as malformed signature.

Allowlist is exact membership in `policy.allowed_repositories` (example: `Dimkox/adaptive-grok-build-pro` only), not a glob. That check is after HMAC so unsigned callers cannot probe the list.

Draft semantics after this commit:

- `opened` / `synchronize` / `reopened` / `ready_for_review` with `draft=true` become a `JobRequest` (exact head/base SHA).
- `closed` + draft still parses with `closed=True` and cancels active jobs.
- Parser does not copy the draft flag into the job; isolation and approval rules do not weaken for drafts.

Rationale is recorded in `decisions.md`: PR `#2` stays draft until the App-owned check exists, so ignoring drafts made that check unreachable. This is an availability fix for the intended gate, not a shortcut around HMAC or the worker/App split.

Residual (non-blocking): there is no dedicated FastAPI test that posts `draft: true` with a valid HMAC. The HTTP tests already cover HMAC 401, allowlist 403, and signed enqueue; the parser test covers draft=true. Same code path.

### 2.2 API still cannot publish checks

`trust-ci/src/adaptive_trust_ci/api.py`:

- Imports `verify_webhook_signature` / `parse_pull_request_event` only from `.webhooks`.
- Does **not** import `GitHubClient` or `GitHubAppAuth`.
- OpenAPI/docs disabled (`docs_url=None`, `redoc_url=None`, `openapi_url=None`).
- Health, webhook, and approval JSON include `'status_publisher': 'worker-github-app'`.
- Job GET strips command output tails (`stdout_tail` cannot leak through the read API).
- Metrics omit repository, SHA, and job id.

Worker (`worker.py`) is the only process that constructs `GitHubAppAuth` and `GitHubClient(token_provider=…)`. `JobRunner.ensure_check_run` / `complete_check_run` stay on that client. Holdout `validate.py` still requires `GitHubClient`/`GitHubAppAuth` absent from `api.py` and present on the worker.

This commit’s `github.py` edit is the protection **payload builder**, used by CLI `branch-protect` (admin token) and tests — not by the API process.

### 2.3 No private keys committed

Tracked delta contains:

- Test fixture strings `wh-secret` / `read-token` (not live credentials).
- Disposable compose-test role passwords that already lived in `compose.test.yaml` (not production; scripts trap `down --volumes`).
- Policy example holdout digest (SHA-256 of the example bundle, asserted by `test_example_holdout_digest_matches_example_bundle`).
- `REPLACE_WITH_*` placeholders in env/trust-store examples (unchanged by this commit).

`.gitignore` still excludes `.env`, `*.pem`, `*.key`, `trust-ci/env/*.env`, `trust-ci/runtime/*`. Worker App key and CI signing key remain path mounts (`/run/secrets/…`). Trust-store example holds a public-key placeholder only.

This reviewer did not open `.env` or any private key file as evidence. No PEM / App RSA / human Ed25519 private key is in `2865fdc` / `dbace96`.

### 2.4 No GitHub Actions

- Local `.github/` does not exist.
- Diff file list has no `.github/workflows/**`, no Dependabot, no `runs-on:`.
- `tests/test_structure.py::test_no_github_actions_workflow_exists` still fails if a workflow tree appears.
- `trust-ci/tests/test_ops.py::test_repository_contains_no_github_actions_workflow` still fails closed.
- Holdout still requires `.github/workflows` absent in the verified workspace.

### 2.5 Branch protection is still not applied (correct)

`branch_protection_payload` still binds `{context: <epoch name>, app_id}` with `strict=true`, `enforce_admins=true`, linear history, conversation resolution, no force-push, no deletion. This commit only renames the local variable so `holdout.example/validate.py` can string-match `'checks': [{'context': status_context, 'app_id': app_id}]`.

CLI `branch-protect` still requires `TRUST_CI_GITHUB_ADMIN_TOKEN` and a deployed policy file. That command is **not** executed here. Docs still tell operators to wait for the App-owned check. Architecture / brief / tasks keep protection as a later step.

Applying protection in this commit would be a fail: it could lock `main` before any App-owned check exists. Absence is required.

---

## 3. Authz, secrets, PII, tenant isolation, irreversible actions

### Authz

- Webhook: HMAC then allowlist then enqueue/cancel. Drafts no longer short-circuit after a valid signature.
- Approvals: Ed25519 envelope vs server trust store; exact SHA/repo/PR/policy/scope; nonce replay → 409. Unchanged.
- Reads (`/jobs`, `/attestations`, `/metrics`): bearer `TRUST_CI_READ_TOKEN` with `compare_digest`.
- Checks publication: worker App JWT → reduced installation token (`checks:write`, `contents:read`, `pull_requests:read`). API has no App key.
- `branch-protect`: separate short-lived human admin token; not the long-lived App. Not invoked.
- Human approval private keys remain out of the agent environment.

### Secrets

No new credential path. Worker-only App key, API-only webhook secret, API-only trust store, runner without `GITHUB_TOKEN` / `TRUST_CI_GITHUB*` remain the split. Sandbox argv still `--network none --cap-drop ALL --read-only --pull never`. Checkout token is used only for `git fetch` of `refs/pull/*/head`, then detached at the webhook SHA.

### PII

No customer PII. Job identity is repository / PR number / SHAs. Public job endpoint continues to strip command tails. Metrics stay low-cardinality. Git author email on the commit is the existing public identity.

### Tenant isolation

Single policy allowlist, single PostgreSQL database, no RLS. Isolation is repository string match plus HMAC on the inbound webhook. Draft enqueue does not add a second tenant or a wildcard allowlist.

### Irreversible actions

None executed by this reviewer. This commit does not merge, tag, deploy, register a webhook, mint an App, or PUT branch protection.

| Forbidden in this slice | Observed |
| --- | --- |
| `adaptive-trust-ci branch-protect` / GitHub protection PUT | docs placeholder only; no token, no App ID committed |
| Merge / un-draft PR `#2` | still draft by design |
| `.github/workflows` | absent |
| Commit private keys / filled env | absent |
| Replace PostgreSQL with JSON/SQLite | not done |
| Read human approval private key | not done |

---

## Findings

No blocking findings.

| ID | Severity | Item | Disposition |
| --- | --- | --- | --- |
| S1 | Residual (accepted) | Draft PRs on an allowlisted repo now run in the isolated worker, same as non-drafts | Intended. HMAC + allowlist + no-network runner + source-mutation fail + worker-only Checks still apply. |
| S2 | Residual (process) | Working tree currently has unresolved conflict markers in `trust-ci/compose.test.yaml` (`<<<<<<< HEAD` / `>>>>>>> 2865fdc`) | **Not in `2865fdc` or `dbace96`.** GitHub raw of `dbace96` is clean (named volume + role-separated test users). Do not commit the conflicted file. Restore the committed compose before further product work. |
| S3 | Residual (test gap) | No HTTP-level `draft=true` HMAC/allowlist case | Parser + existing API HMAC/allowlist tests cover the path. Nice-to-have, not a bypass. |
| S4 | Residual (pre-existing) | Privileged rootless DinD on TCP 2375 inside the executor network | Out of this commit. Keep worker off production hosts; do not grant the App `administration`. |
| S5 | Residual (process) | `branch-protect` remains a one-shot human admin-token command | Do not run it until the App-owned `adaptive-trust-ci/verified@<policy-sha12>` exists on an exact SHA. Revoke the token after. |
| S6 | Observational | `2865fdc` is not on GitHub; origin tip is the rebase `dbace96` | Same product patch. Review both SHAs as equivalent for this slice. |

---

## Recommendation

**PASS.** Treat `2865fdc` (and its rebase `dbace96`) as a bounded intake/test repair: draft PR jobs stay behind HMAC + allowlist; the API still cannot publish checks; no keys, no GitHub Actions, no branch-protection apply.

Do not apply `branch-protect` from this review. Do not merge PR `#2`. Do not commit the conflicted working-tree `compose.test.yaml`. Do not read or copy `.env` / App keys. Next operational steps (App install, digest-pinned deploy, webhook proof, then app-bound protection) remain outside this commit and still need exact delegated grants plus a live App-owned check.
