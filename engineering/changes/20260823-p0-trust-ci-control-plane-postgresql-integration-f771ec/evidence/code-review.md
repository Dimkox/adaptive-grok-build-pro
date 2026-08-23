# Code review — P0 Trust CI control plane (draft enqueue, holdout lock, named volume)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Route: `f771ecaf458d` · reviewer: `code_reviewer` (read-only) · write owner: none  
Reviewed: 2026-08-23

Assigned commit: `2865fdc632860534c8ffc61aa9981844a0685b5d` (`fix: enqueue draft PRs and prove live PostgreSQL Trust CI state`) on top of `04348db`.  
Landed equivalent after rebase onto `bf63f8a`: `dbace962d74795fe3b18c2b67b0698b74cc4a444` (same message; this is current `feat/trust-ci-control-plane` / origin).  
PR: draft `#2` targeting `main`.

**PASS.** I would not block this slice.

This is a bounded baseline repair, not GitHub App activation, deploy, or branch protection. Those remain later tasks in the change package. Local receipts still are not merge authority.

---

## Verdict against the assigned focus

| # | Check | Result |
| --- | --- | --- |
| 1 | Draft PR webhook enqueue | **PASS.** Parser no longer drops `draft=true` except `closed`. |
| 2 | Holdout string match vs `github.py` `status_context` | **PASS.** Payload identifier renamed to `status_context`; holdout substring now hits live source. |
| 3 | `compose.test.yaml` named volume | **PASS.** Data dir is `trust-ci-pgtest-data`; tmpfs removed; least-privilege test roles kept on the rebased tree. |
| 4 | No GitHub Actions | **PASS.** No `.github/workflows/`; no workflow files in the diff. |
| 5 | No secrets committed | **PASS.** No `.env`, PEM, App key, or webhook secret in the commit. |
| 6 | Residual risk / would you block? | Residuals only. **No block.** |

Would I block? **No.**

---

## What was actually inspected

```text
# refs
.git/HEAD                                      → feat/trust-ci-control-plane
.git/COMMIT_EDITMSG                            → fix: enqueue draft PRs…
.git/logs/refs/heads/feat/trust-ci-control-plane
  04348db → 2865fdc  commit
  2865fdc → dbace962 rebase (finish) onto bf63f8a
.git/refs/heads/feat/trust-ci-control-plane    → dbace962
.git/refs/remotes/origin/feat/trust-ci-control-plane → dbace962

# actual product diff (GitHub patch of landed SHA)
https://github.com/Dimkox/adaptive-grok-build-pro/commit/dbace962d74795fe3b18c2b67b0698b74cc4a444.diff
Original 2865fdc HTML 404 after rewrite; dbace962 is the same message and file set.

# contracts
engineering/changes/…-f771ec/{brief,architecture,requirements,tasks,test-plan,rollback}.md
engineering/changes/…-f771ec/evidence/analysis-{architect,data_architect,docs_researcher,integration_architect,repo_explorer}.md
GROK_BUILD_HANDOFF.md  (PR #2 stays draft until App-owned check)

# product (surrounding + delta)
trust-ci/src/adaptive_trust_ci/{webhooks,api,github,policy,workspace}.py
trust-ci/holdout.example/validate.py
trust-ci/{compose.test.yaml,compose.yaml,Dockerfile.test}
trust-ci/config/policy.example.json
trust-ci/scripts/{postgres-integration,postgres-restart-drill}.sh
trust-ci/tests/{test_webhooks_github,test_api,test_ops,test_backup,test_runner,test_postgres_integration,postgres_restart_probe,test_database_roles}.py
trust-ci/postgres/init/001_roles.sh
tests/test_structure.py
.gitignore  (excludes .env, *.pem, trust-ci/env/*.env, trust-ci/runtime/*)

# absences
.github/          does not exist
.github/workflows does not exist
```

No `.env` or credential files were used as review evidence. No push, merge, or deploy.

During this session the working tree briefly contained rebase conflict markers in `trust-ci/compose.test.yaml`. Those markers are **not** in `dbace962`. Do not commit a conflicted working copy; restore the committed compose if the workspace is dirty.

---

## 1. Draft PR webhook enqueue

Handoff keeps PR `#2` draft until the App-owned check exists. Pre-change intake was:

```python
if pull_request.get("draft") and action != "closed":
    return None
```

That made the check unreachable for a draft PR. The landed diff deletes those two lines. `parse_pull_request_event` still builds a `JobRequest` for `opened|synchronize|reopened|ready_for_review`, including `draft=true`. `closed` still sets `event.closed` so `api.py` cancels jobs.

`api.py` has no second draft filter. HMAC, allowlist, kill switch, and idempotent `enqueue` are unchanged. Duplicate identity still reuses the job, so `ready_for_review` on the same SHA does not create a second row.

Tests: `test_draft_pull_request_is_ignored` was replaced with `test_draft_pull_request_is_enqueued` (non-None event, not closed, same PR/SHA). Closed-draft cancellation remains covered.

Residual: `test_api.py` still posts `'draft': False` only. That is a test gap, not a behavior gap, because the API consumes the parser result.

---

## 2. Holdout string match vs `github.py`

Pre-change `branch_protection_payload` used `normalized_name`. `holdout.example/validate.py` still requires the literal:

```python
"'checks': [{'context': status_context, 'app_id': app_id}]"
```

Live `github.py` now binds `status_context = check_name.strip()` and emits that exact checks list (trailing comma in the dict is fine; holdout searches a substring). Deploying the example holdout against this tree can pass the string lock.

Semantics are unchanged: the value is still the full policy-epoch check name (`adaptive-trust-ci/verified@<sha12>`), still app-bound, still no legacy `contexts` array. Unit tests continue to assert `{'context': check_name, 'app_id': …}`.

`policy.example.json` holdout digest moved

`28ee9c80…` → `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8`.

`holdout.example/validate.py` is not in this commit; `test_ops.test_example_holdout_digest_matches_example_bundle` is the lock. I did not recompute the SHA-256 here.

---

## 3. `compose.test.yaml` named volume

`compose restart` discards a tmpfs data dir. The landed compose keeps role bootstrap and replaces tmpfs with a named volume:

```yaml
volumes:
  - ./postgres/init:/docker-entrypoint-initdb.d:ro
  - trust-ci-pgtest-data:/var/lib/postgresql/data
# ...
volumes:
  trust-ci-pgtest-data:
```

Least-privilege test users from the rebase parent remain (`trust_ci_admin_test` + API/worker/migrator/backup passwords and DSNs). Healthcheck still uses `trust_ci_admin_test`. That is the correct merge: named volume for catalog survival, not a rollback to a single superuser.

`postgres-restart-drill.sh` still `compose restart postgres-test` then `postgres_restart_probe verify`. Both integration and restart scripts use unique project names and `down --volumes` on EXIT, so the named volume does not leak across runs.

`test_ops.test_postgres_restart_drill_uses_named_volume_and_container_restart` asserts the volume mount, absence of `tmpfs:` in **test** compose, and the seed/restart/verify script. Production `compose.yaml` still uses named volume `trust-ci-postgres` for the database; API/worker tmpfs is process scratch, not catalog.

Dockerfile.test / compose command now use `unittest discover -s tests -p test_postgres_integration.py`, which still loads `postgres_restart_probe.py` as a module when the drill invokes it explicitly.

---

## 4. No GitHub Actions

Diff adds no `.github/**`, no workflow YAML, no Dependabot. `.github/` is absent. `tests/test_structure.py` and `trust-ci/tests/test_ops.py` still fail if workflows appear. Branch-protection payload tests still forbid `"actions"` in the protection object. Holdout still forbids `.github/workflows` in the workspace.

---

## 5. No secrets committed

Committed paths are source, tests, example policy, docs, and the change package. Not present: `trust-ci/env/*.env` (non-example), `*.pem`, GitHub App key, webhook secret, human private key, filled compose `.env`.

`.gitignore` already excludes `.env`, `*.pem`, `*.key`, `trust-ci/env/*.env`, and `trust-ci/runtime/*`. Example env files still use `REPLACE_WITH_*`. Compose test passwords are disposable fixtures that already existed on the parent (not production credentials). `test_api.py` only shortened fixture names (`webhook-secret` → `wh-secret`).

---

## Other baseline repairs in the same commit

These are coherent with the red `04348db` baseline and are not scope creep:

| Change | Assessment |
| --- | --- |
| `WorkspaceMutationError(('production.py',))` | Matches current one-arg constructor in `workspace.py`. |
| Backup tamper writes same-length bytes | Forces digest check, not size check. |
| Example sandbox image may end with `REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST` | Matches architecture: example placeholder; deployed policy must pin. |
| README mermaid edge count scoped to the graph | Avoids false positives from other ` --- ` prose. |
| Protected-path assert accepts `scripts/grok_*.py` | Still requires verify-script protection. |

README / rollout only dropped quotes around the admin-token placeholder. They still document `--exit-code-from tests` while the live service is `postgres-integration`. The executable path `trust-ci/scripts/postgres-integration.sh` is already correct. That is a residual docs miss, not a product regression.

---

## Change-package / contract fit

In scope for this slice: baseline repairs, draft enqueue so PR `#2` can receive a check while remaining draft, holdout/`github.py` alignment, live Postgres restart durability.

Out of scope and still open (do not treat this commit as activation complete):

- digest-pinned API/worker/runner images
- GitHub App create/install
- isolated deploy, HMAC webhook, App-owned check on the exact SHA
- app-bound `branch-protect`

`write_agent` is null; this is a parent-owned repair, not a new product design.

---

## Residuals (non-blocking)

1. No API-level test that a signed `draft=true` webhook returns `created=true`. Parser coverage is the behavior lock.
2. README and `engineering/runbooks/trust-ci-rollout.md` still say `--exit-code-from tests`. Copy-paste fails; use `postgres-integration.sh`.
3. Example policy still has a runner-digest placeholder. Do not deploy it as-is.
4. I did not execute unittest, the live Postgres 8/8 harness, or `grok_verify`. Those belong to verification / test review.
5. GitHub App, deploy, and branch protection are not in this diff. Do not merge `#2` on this evidence.

---

## Ruling

The landed product delta does the three repairs the handoff needed before a draft PR can be proven, without introducing GitHub Actions or committed secrets. Surrounding implementation (`api.py` enqueue path, holdout validator, restart drill, role-separated test DSN, gitignore) is consistent with that delta.

**PASS.**
