# Security review — M0.0 docs + invariant tests

**Agent:** `security_reviewer` (read-only; in route `allowed_agents`)  
**Route:** `3722694830f7`  
**Change:** `20260824-user-query-read-agents-md-decisions-md-mistakes-372269`  
**HEAD:** `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` plus uncommitted M0.0 files listed below  
**Skills:** `/adaptive-delivery`, `/security-sensitive-change`  
**This review is not merge authority.** Local receipts cannot create `adaptive-trust-ci/verified@<policy-sha12>`.

Did not read `.env`, `*.pem`, private keys, trust-store private material, or `trust-ci/env/*.env`. Did not push, merge, deploy, compose-up, webhook, `branch-protect`, or run `grok_review.py`.

## Verdict: **pass**

M0.0 is design-freeze documentation plus static characterization tests. It does not leak secrets, does not read PEM, does not add GitHub Actions, does not instruct agents to hold human approval keys, preserves the API/worker role split, and forbids protecting `main` before a live App-owned check. Leftover Actions workflow **340420982** is named for **M0.3**, not this slice.

| Confirmation | Result |
| --- | --- |
| No secret leak in M0.0 docs+tests | **PASS.** No PEM/JWT/webhook/admin/human-private-key bodies. App ID, installation ID, policy digest, and check epoch stay `UNKNOWN` or unstated. Live-gap table records HTTP outcomes only. |
| Tests/docs do not read PEM | **PASS.** Spec records `trust-ci/runtime/github-app-private-key.pem` as gitignored filename **not opened**. Plan M0.0 STOP: no PEM read. `test_m0_invariants.py` reads spec, plan, `compose.yaml`, `api.py`, `worker.py`, `holdout.example/validate.py` only. |
| No GitHub Actions added | **PASS.** No `.github/` tree. Spec forbids `.github/workflows/**`. Test asserts the workflows directory is absent. Tracked files include no `*.pem` / `trust-ci/env/*.env` / `.github/**`. |
| Agents must not hold human approval keys | **PASS.** Spec: private keys never on the CI host or in the agent workspace; `approval-create` on a human machine. Report template forbids pasting those keys. Plan does not assign `approval-create` to agents. |
| API/worker role split kept | **PASS.** Spec restates the split. Tests freeze it as source invariants. Surrounding `compose.yaml` still mounts App RSA + signing key on **worker only** and trust-store on **API only**. |
| Do not protect `main` before a live App-owned check | **PASS.** Spec rollout step 4 and Forbidden list. Plan M0.2: **Do not protect `main`**. Plan M0.3 only after M0.2 is unambiguous. |
| Workflow `340420982` | **Noted, not now.** Disable/delete is an M0.3 operator action after the live check exists. M0.0 does not disable it and must not. |

**Local security review: pass.** Do not merge on this receipt. Do not treat leftover registry workflow `340420982` as gone.

---

## Scope inspected

Product slice (uncommitted on `milestone/m0-live-trust-authority`):

- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`
- `engineering/runbooks/trust-ci-activation-report.md`
- `trust-ci/tests/test_m0_invariants.py`

Surrounding implementation (read-only, not modified by this slice): `trust-ci/src/adaptive_trust_ci/{api,worker,settings,github_app}.py`, `trust-ci/compose.yaml`, `trust-ci/holdout.example/validate.py`, `trust-ci/env/{api,worker,common}.env.example`, `trust-ci/config/trust-store.example.json`, `.gitignore`. Filename-only listing of `trust-ci/runtime/` (PEM body not opened). Change package analysis + code/test reviews for consistency.

No application runtime behavior changed. No webhook, Check Run, or branch-protection mutation in this slice.

---

## 1. Secrets, PII, credential handling

**Assets:** GitHub App RSA, installation tokens, webhook HMAC, CI Ed25519 signing key, human approval private keys, admin token used for `branch-protect`, PostgreSQL role passwords, `TRUST_CI_READ_TOKEN`.

**Findings:**

- Spec, plan, activation report, and invariant tests contain **no** `-----BEGIN` blocks, JWTs, `ghp_`/`github_pat_` tokens, or filled secrets. Secret-pattern grep on those four files is clean.
- Activation report is an operator-safe template: live fields are `UNKNOWN`; header forbids pasting PEM, JWT, webhook secret, admin token, or human approval private keys. Public identifiers allowed later (App ID, installation ID, digests, Check Run id) are not secrets and are still unfilled.
- Spec names the gitignored PEM **path** and states it was not opened. That is operator-safe. `.gitignore` covers `*.pem`, `*.key`, `.env`, `trust-ci/env/*.env`, and `trust-ci/runtime/*` (except `.gitkeep`). `git ls-files` tracks no PEM, no filled env, no `.github/`.
- Tests reject `BEGIN RSA PRIVATE KEY` in spec/plan. They never open `trust-ci/runtime/github-app-private-key.pem`.
- Env examples still use `REPLACE_WITH_*` placeholders. Trust-store example holds a public-key placeholder only.
- No customer PII. Repository name `Dimkox/adaptive-grok-build-pro`, SHA `48cb973…`, and workflow id `340420982` are public GitHub metadata.

**Residual (not fail):** tests do not also reject PKCS8 `BEGIN PRIVATE KEY`, EC, or OpenSSH headers, and they do not scan the activation report. Current files have none of those. Fixture-key crypto in later drills must stay in tmpdirs; M0.1 must mount a **host-owned** App key, not the agent-readable laptop path.

Laptop still has a gitignored `trust-ci/runtime/github-app-private-key.pem` (mode `600`). Filename confirmed; body not opened. This file is **not** a live installation and must not be copied into git or into agent evidence.

---

## 2. Authorization and role split

Spec role split matches the already-built service:

| Process | May hold | Must not hold |
| --- | --- | --- |
| API | webhook HMAC, human **public** trust store, read token | App RSA, installation tokens, CI signing key, Check Run publish |
| Worker | App ID + installation ID + RSA, CI Ed25519, reduced installation token (`checks:write`, `contents:read`, `pull_requests:read`) | webhook secret, human trust store |
| Runner | none | token, key, Docker socket, network |
| Human machine | approval private keys; one-shot admin token for `branch-protect` | long-lived App Administration |

Surrounding code still enforces that split. `api.py` imports webhook verify + `TrustStore`; it does not import `GitHubClient` / `GitHubAppAuth`. Ready and webhook responses set `status_publisher: worker-github-app`. Approvals are verified against the public trust store and requeue the durable job; the API does not publish a Check Run. `worker.py` constructs `GitHubAppAuth` and `GitHubClient`. Compose mounts `github-app-private-key.pem` and `trust-ci-signing-key.pem` on **worker** only; `trust-store.json` on **API** only. API env example has `TRUST_CI_WEBHOOK_SECRET` and `TRUST_CI_ROLE=api`; worker env example has App ID/installation ID/PEM path and `TRUST_CI_ROLE=worker`. Holdout example already forbids API holding the App key and forbids `.github/workflows`.

`test_m0_invariants.py` freezes the in-tree half of this contract (API substring absence, worker substring presence, compose loopback bind, holdout strings). That is appropriate characterization for M0.0. It is **not** a substitute for a live App-owned Check Run.

Check contract in the spec is the operator contract: name `adaptive-trust-ci/verified@<policy-sha12>`, `external_id` = durable job id, owner = Trust CI App, success backed by stored Ed25519 attestation. Same **text** from GitGuardian, leftover Actions, or a PAT must not satisfy branch protection. Long-lived App must not have repository Administration. `branch-protect` uses a **temporary human** admin token.

---

## 3. Irreversible / production actions — correctly deferred

M0.0 executes none of: compose-up, webhook registration, Check Run publish, `branch-protect`, disable workflow `340420982`, PEM/JWT install-ID lookup, human `approval-create`.

Binding order in the spec:

1. Dedicated-host API + PostgreSQL + worker (`/health/ready`).
2. HTTPS webhook.
3. Disposable PR → App-owned Check Run on exact head SHA → attestation verify → mutation/approval/kill/backup drills. **Do not protect `main`.**
4. **Then** protect `main` with epoch name **and** App ID. Disable leftover Actions workflow `340420982`. Supersede bootstrap-exception language because a live check exists — never by forging one.

Protecting `main` before that check can lock the repository. Plan M0.2 repeats **Do not protect `main`**. Plan grants put host compose / webhook / `branch-protect` / disable `340420982` in **M0.1–M0.3 only**. This laptop is forbidden as the CI host (SearXNG on `:8080`, shared Docker engine, privileged DinD).

Named gates remain: `migration_or_external_write_approval` plus exact delegated grants before those writes. This review does not authorize them.

---

## 4. GitHub Actions and workflow 340420982

- Git tree: no `.github/` directory. Test `test_no_github_actions_workflows_tree` will fail if one is added.
- GitHub **registry** still has leftover workflow `trusted-ci` id **340420982**, path `.github/workflows/trusted-ci.yml`, state=active, 0 runs on `main` (file absent from git). Live “no GitHub Actions” is therefore **false in the catalog**, true in the tree.
- Spec live-gap, spec exit extras, plan M0.3, and activation-report field all require disable/delete of **340420982 by M0.3**.
- M0.0 must **not** disable it now (needs `external-write` after a live App-owned check). M0.0 must **not** revive the YAML.

Do not treat GitGuardian or this stale Actions catalog entry as merge authority.

---

## 5. Tenant isolation, injection, auditability

This product is a single-repo Trust CI control plane, not a multi-tenant SaaS. Isolation that M0.0 documents and does not weaken:

- Server policy `allows_repository` on webhook enqueue (existing `api.py`).
- Runner: `network=none`, no token/key/socket (spec + existing compose).
- API published `127.0.0.1:8080:8080`, not `0.0.0.0` (spec + test + compose).
- Holdout outside the PR checkout; PR tree is untrusted.
- Human approvals bound to repository, PR, base SHA, head SHA, policy digest, actor, key_id, nonce, TTL.
- Kill switch, backup/restore/restart are M0.2/M0.3 drills, not this slice.

No new HTTP surface, SQL, or parser. Input-validation / CSRF / SSRF risk is unchanged from the already-reviewed 2.1.0 source.

**Pre-existing, not introduced:** DinD `docker-engine` listens `tcp://0.0.0.0:2375` on the internal `executor` network (not published to the host). Dedicated-host deployment must keep that network isolated. Out of scope for M0.0.

---

## 6. Abuse cases checked against this slice

| Abuse | Why M0.0 does not enable it |
| --- | --- |
| Commit App PEM / webhook secret / approval key | Forbidden in spec; gitignore; tests reject RSA PEM header in spec/plan; report template empty |
| Agent reads laptop PEM to mint JWT | Plan M0.0 STOP; spec “not opened”; tests do not open the file |
| Agent holds human approval private key | Spec forbids; `approval-create` is human-machine only |
| Add GitHub Actions / Dependabot CI | Forbidden; test fails if `.github/workflows` appears |
| Forge `adaptive-trust-ci/verified@*` | Forbidden; local receipts remain preflight |
| Protect `main` with no live App check | Explicitly forbidden; M0.3 only after M0.2 |
| API process publishes checks or holds App RSA | Spec + tests + compose/holdout invariants |
| Use this laptop as CI host | Spec Host section forbids it |
| Disable 340420982 now, or leave it as authority | Named for M0.3; catalog leftover is untrusted |

---

## Residual risk (does not fail M0.0)

1. Characterization tests are substrings, not an import graph. A later `from .github_app import GitHubAppAuth` in a new API helper would need holdout/AST coverage (holdout already re-checks `api.py` / `worker.py` on the **deployed** bundle).
2. PEM header check is RSA-only; PKCS8/EC/OpenSSH would not trip `test_m0_spec_and_plan_exist`.
3. Leftover gitignored PEM on this laptop remains an agent-workspace hazard until M0.1 uses a host-owned key on a dedicated machine.
4. Workflow **340420982** stays **active** in GitHub until M0.3. Tree tests cannot see the catalog.
5. Sibling untracked `engineering/changes/*` packages exist in the worktree. They were not scanned as product; path-limited add only when committing M0.0. No secret bodies observed in the M0.0 product files.

---

## Recommendation

**Pass** M0.0 for local independent security review.

Next slices still require `migration_or_external_write_approval`, a **named** dedicated CI host, and exact grants. Do not protect `main` until an App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run exists on an exact disposable-PR SHA. Disable leftover Actions workflow **340420982 in M0.3, not now**.
