# Repo explorer — crash resume (README/QUICKSTART/toolchain docs pass)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Crashed session: `01a02fb3-44ee-73f2-9a2a-9daf856c17ae` / write owner `general_implementer` `01a03014-ade4-73c2-acf3-696f250d85bf`  
Crashed route: `2335b3d0d9fc` (intent=docs, micro)  
This inspection route: `56da62035c35` (intent=feature; write=`general_implementer`)  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` (`feat/trust-ci-control-plane` == `origin/feat/trust-ci-control-plane`)  
Inspected: 2026-08-23. Read-only. No `.env`, keys, push, merge, or deploy.

Crash clock: `.grok-stack/runtime/last-session-end.json` `ended_at=2026-08-23T19:31:20+00:00` reason `shutdown`. Last successful write of that turn is `evidence/implementation-readme.md` mtime `2026-08-23T19:30:56Z`.

**There are no half-written product files.** The blocked README / `trust-ci/README.md` / `decisions.md` edits never landed. Working-tree dirty files are complete uncommitted batches from *before* the grant went stale, plus this evidence directory.

Do **not** commit `engineering/changes/20260817-user-query-вычисти-*`. Do **not** `git push origin main`.

---

## 1. Git facts at resume

```text
## feat/trust-ci-control-plane...origin/feat/trust-ci-control-plane
 M .grok-stack/config/toolchain.json        (19:27:34Z)
 M tests/test_structure.py                  (19:27:34Z)
 M tests/test_toolchain.py                  (19:27:34Z)
 M QUICKSTART.md                            (19:28:50Z)
 M engineering/runbooks/trust-ci-rollout.md (19:30:17Z)
?? engineering/changes/.../evidence/analysis-repo_explorer-readme.md  (19:21:49Z)
?? engineering/changes/.../evidence/implementation-readme.md         (19:30:56Z)
?? engineering/changes/20260817-user-query-вычисти-*                 (unrelated leftover)
```

`git diff --cached` empty. `Makefile` clean vs HEAD. `README.md` / `trust-ci/README.md` / `decisions.md` / `GROK_BUILD_HANDOFF.md` / `VERSION` clean vs HEAD (mtime still 17:37 / 18:01). No `.swp` / `*~` / `README.md.*` leftovers.

Grant used for the crashed turn: `6fcd3898df7b0eae` (`protected-path-write`, route `2335b3d0d9fc`, HEAD `5915b56…`, fingerprint `aa731cb93c12…`). It matched at the start of that turn. The first successful batch mutated the tree, so the grant is stale. Exact PreToolUse denials (no disk mutation):

- `Hook denied: Protected path edit requires an exact delegated grant for README.md.`
- `Hook denied: Protected path edit requires an exact delegated grant for trust-ci/README.md.`
- `Hook denied: Protected path edit requires an exact delegated grant for decisions.md.`

A **new** grant bound to the **current** dirty tree fingerprint is required for those three. Do not use shell redirects/tee/python to mutate them. `QUICKSTART.md` and `engineering/runbooks/trust-ci-rollout.md` are not protected today.

Older grants in `approvals.json` (ids `0b7f4cfda7ac…`, `a66b0923…`, etc.) are bound to HEAD `04348db` and are also invalid for this tree.

---

## 2. Landed (uncommitted, complete, keep)

| File | What landed | Grant needed to have written it |
| --- | --- | --- |
| `tests/test_structure.py` | Method renamed `test_readme_stack_graph_is_complete`. Nodes = K16 IDs. Edge count = `len(list(itertools.combinations(nodes, 2)))` (120). `itertools` already imported at HEAD. | protected (`tests/test_*.py`) — landed under `6fcd3898` before it went stale |
| `tests/test_toolchain.py` | Catalog must contain `docker`, `syft`, `trivy`, `cosign`, all `required: false` | protected — landed |
| `.grok-stack/config/toolchain.json` | grok `built`/`fallback` `1.0.5`; appended those four optional tools (`docker` 29.7.2 / `syft` 1.51.0 / `trivy` 0.74.0 / `cosign` min 2.0 fallback 2.4, linux pin `v2.4.3`). No `grype`, no standalone `docker-compose`, no required `psql` | protected — landed |
| `QUICKSTART.md` | Consumer 0–7 kept. Operator sections: scope split, Bitrix, Postgres, live harness, two-file compose build, `$TRUST_CI_*_IMAGE` inspect, keys, start/health, webhook/protect, backup/kill-switch/supply-chain, scanner installs | **not protected** — landed |
| `engineering/runbooks/trust-ci-rollout.md` | two-file merge build, `$TRUST_CI_*_IMAGE` inspect, `make trust-ci-postgres-test` / `--exit-code-from postgres-integration` | **not protected** — landed |

### Makefile (already in HEAD `5915b56`, not a leftover)

```make
docker-compose-build-config:
	docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml config

trust-ci-postgres-test:
	... --exit-code-from postgres-integration postgres-integration
```

`make trust-ci-compose` remains `compose.yaml` config-only (production has no `build:`). Service name in `trust-ci/compose.test.yaml` is **`postgres-integration`** (image default `adaptive-trust-ci-test:2.1.0`), not `tests`. Do not retouch Makefile for this docs pass.

### Residual inaccuracy inside already-landed `QUICKSTART.md`

Line ~145: “Draft PRs are ignored.” That is **false on HEAD**. `parse_pull_request_event` does not read `draft`. `test_draft_pull_request_is_enqueued` locks enqueue. Commit `dbace96` (“enqueue draft PRs”). Optional one-line fix in the next QUICKSTART edit: prove on a disposable PR (draft #2 is eligible); still prefer a docs-only disposable first because `trust-ci/**` needs governance approval.

---

## 3. Blocked files (no crash leftovers on disk)

| File | Protected? | Status vs HEAD | Why blocked |
| --- | --- | --- | --- |
| `README.md` | yes (control-plane) | **unchanged** — still K10 / 45 edges | grant stale after first batch |
| `trust-ci/README.md` | yes (`trust-ci/**`) | **unchanged** — stale compose commands | grant stale |
| `decisions.md` | yes (control-plane) | **unchanged** — last graph ruling is 2026-08-16 K10 | grant stale |

These are the only product files the crashed implementer still owed. Nothing partial is sitting beside them.

---

## 4. Exact remaining in-tree edits

### 4.1 `README.md` — required for tests

Current first mermaid (lines 65–117): caption still says Trust CI is **outside** the graph. Fence is K10. Grep of `\S+ --- \S+` in the fence = **45** lines (72–116). Node-role table has 10 rows. No `TrustAPI` / `TrustWorker` / `Postgres` / `Runner` / `Holdout` / `GitHubApp`.

`test_readme_stack_graph_is_complete` now expects this ordered ID list and `C(16,2)=120` undirected `---` edges, no `-->`, no duplicates:

```text
Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes,
TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp
```

Suggested labels (IDs must stay as above):

```text
Contract["AGENTS.md"]
Decisions["decisions.md"]
Mistakes["mistakes.md"]
TrustAPI["trust-ci API"]
TrustWorker["trust-ci worker"]
Postgres["PostgreSQL 17"]
Runner["isolated runner"]
Holdout["external holdout"]
GitHubApp["GitHub App Checks"]
```

Emit:

```python
for left, right in itertools.combinations(nodes, 2):
    print(f"  {left} --- {right}")
```

Replace caption “Trust CI is deliberately outside this graph” with: local workflow plus independently deployed Trust CI applications and PostgreSQL; prompts are not merge authority.

Add six node-role rows. Do **not** add a second mermaid (the test parses the **first** fence and also scans whole-file pair text).

Also recommended (not locked by the graph test, but the toolchain batch already moved):

| README row today | Working-tree toolchain |
| --- | --- |
| Grok CLI built/fallback **1.0.4** | **1.0.5** |
| No docker/syft/trivy/cosign rows | four optional tools present |

Keep H1 `# Adaptive Grok Build Pro v2.0.11`. Do not bump `VERSION`. Trust CI package identity stays `2.1.0`. Current-state already names `trust-ci/`; naming both identities there is enough.

Keep CHANGELOG 2.0.8 “K10 complete graph” as history.

### 4.2 `trust-ci/README.md` — three stale command blocks

**Build/pin (lines 89–93)** — `compose.yaml` has no `build:`; api/worker are not tagged `adaptive-trust-ci-api:2.1.0`. Replace with the already-landed runbook/QUICKSTART form:

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
```

Only `runner-image` in `compose.build.yaml` sets a local tag (`TRUST_CI_RUNNER_BUILD_TAG` default `adaptive-trust-ci-runner:2.1.0`).

**Verification (lines 262–266)** — replace:

```bash
docker compose -f trust-ci/compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f trust-ci/compose.yaml config
docker compose -f trust-ci/compose.yaml build api worker
docker compose -f trust-ci/compose.yaml --profile build build runner-image
```

with:

```bash
make trust-ci-postgres-test
# or: docker compose -f trust-ci/compose.test.yaml up --build --abort-on-container-exit --exit-code-from postgres-integration
docker compose -f trust-ci/compose.yaml config
docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml config
docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml --profile build build api worker runner-image
```

Bootstrap env copy (lines 71–81) still omits `.env`, `env/migration.env`, `env/backup.env` that QUICKSTART now copies. Align if touching this file; not required for the structure test.

### 4.3 `decisions.md` — K16 ruling not recorded

Last graph entry is still:

> ## 2026-08-16 — README stack graph is K10 with every pair written out

Do not rewrite that. Append one ≤3-sentence 2026-08-23 ruling: the listed core set now includes Trust CI API/worker, PostgreSQL 17, isolated runner, external holdout, and GitHub App Checks, so the first mermaid is K16 with `C(16,2)=120` `---` edges and the structure test derives the count from `itertools.combinations`. Dual-graph was rejected so AGENTS.md “one complete graph” stays a single fence.

### 4.4 Optional residual (landed files, not blocked)

- QUICKSTART “Draft PRs are ignored” vs `test_draft_pull_request_is_enqueued`.
- `GROK_BUILD_HANDOFF.md` still says “4 skipped” Postgres tests (HEAD has 8 `skipUnless`; live 8/8 already recorded in `tasks.md`). Handoff is the user-approved order, not this docs pass’s required edit.

### 4.5 Do not touch

- `Makefile` (already correct in HEAD)
- `VERSION` / `CHANGELOG.md` / `__init__.py` / zip (identity stays 2.0.11)
- filled `trust-ci/env/*.env`, `trust-ci/runtime/**`, keys
- `engineering/changes/20260817-user-query-вычисти-*`
- `.github/`

---

## 5. Tests that will fail until README is updated

Only this product test is red **because** the graph test moved and README did not:

| Test | Failure mode on current tree |
| --- | --- |
| `tests.test_structure.StructureTests.test_readme_stack_graph_is_complete` | `missing` ≈ 75 K16 pairs (`C(16,2)-C(10,2)=120-45`); then `len(edge_lines) == 45 != 120` |

Will stay green without README:

| Test | Why |
| --- | --- |
| `test_version_identity_matches_readme` | H1 still `v2.0.11` |
| `test_core_product_files_exist` | `QUICKSTART.md` still not in the required list |
| `test_trust_ci_control_plane_is_complete` | does not parse mermaid |
| `test_no_github_actions_workflow_exists` | `.github/workflows` absent |
| `tests.test_toolchain.ToolchainTests.test_real_toolchain_json_required_and_optional_sets` | dirty `toolchain.json` already has the four optional ids |
| `test_optional_missing_does_not_fail_doctor` | new tools are `required: false` |
| `test_manifest_package` | VERSION unchanged |

`python3 scripts/grok_verify.py --mode pr` will fail closed on the structure test until README’s first mermaid is the K16 clique. `scripts/grok_verify.py` still does **not** discover `trust-ci/tests`.

No other in-tree test asserts the 10-id set. Do not add a root Dockerfile/compose just to document Trust CI (`test_this_repo_shaped_tree_omits_bucket_b` / live `trivy-config`).

---

## 6. Remaining Trust CI activation files (in-tree vs not)

Control-plane **code and templates are already in HEAD**. Activation that is still open is almost entirely **out of tree**. `tasks.md` (still `approved`, not `ready`):

```text
[x] live PostgreSQL integration (8/8) and restart drill (PASS)   # recorded; stdout not copied into evidence/
[ ] Build and pin immutable images and holdout digest
[ ] Create/install GitHub App (worker-only key, API-only webhook secret)
[ ] Deploy isolated API/worker/postgres/holdout/TLS intake
[ ] Prove webhook → App-owned check on PR #2
[ ] Apply app-bound branch protection only after that check exists
[ ] Commit, update draft PR #2, record independent reviews
```

The last checkbox is only partly true: product activation repairs **are** committed through `5915b56` and origin is in sync; the README/QUICKSTART docs pass is **not** committed; PR #2 remains draft.

### In-tree activation surface (present; do not recreate)

- `trust-ci/compose.yaml` (no `build:`; digest-pinned images)
- `trust-ci/compose.build.yaml` (api/worker/migrate/runner-image)
- `trust-ci/compose.test.yaml` + `scripts/postgres-integration.sh` + `postgres-restart-drill.sh`
- Dockerfiles, SQL `001`–`003`, `postgres/init/001_roles.sh`
- `env/*.env.example`, `.env.example` (`REPLACE_WITH_*` digests)
- `config/policy.example.json` (runner still `…@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`)
- `config/trust-store.example.json`, `holdout.example/`
- systemd compose + backup timer
- `scripts/supply-chain-release.sh` / `verify-supply-chain.sh` (docker, syft, trivy, cosign — **not grype**)
- CLI: migrate, holdout-digest, keygen, doctor, branch-protect, backup, kill-switch, attestation-verify

`trust-ci/runtime/*` is gitignored. A host-local `trust-ci/runtime/github-app-private-key.pem` is visible to directory listing; **do not read, copy, or commit it**. Treat it as an operator secret, not a product file.

### GROK_BUILD_HANDOFF steps 3–9 — NOT in-tree work

| Step | In-tree? | Remaining |
| --- | --- | --- |
| 3 Build/pin artifacts | Dockerfiles + compose.build + holdout-digest CLI | Real image `@sha256` pins, policy digest, SBOM, vuln report, CI public key. Example policy runner digest is still REPLACE. Cosign is **not** installed on this host (toolchain fallback 2.4 / linux pin v2.4.3). |
| 4 GitHub App | JWT/Checks client + tests | Create/install App on `Dimkox/adaptive-grok-build-pro`; App ID; installation ID; worker-only RSA key; API-only webhook secret. API must not receive App credentials. |
| 5 Deploy | compose + systemd units | Isolated host: Postgres, migrate, API, worker, runner image, holdout mount, HTTPS reverse proxy (**no in-tree proxy**), backup target, logs. `/health/ready` stays 503 until Postgres **and** an active human public key exist. |
| 6 Webhook proof | HMAC intake; **drafts now enqueue** | Register HTTPS webhook; prove Check Run `adaptive-trust-ci/verified@<policy-sha12>` on an exact SHA; offline attestation-verify. Handoff still says update draft PR #2 first — code will enqueue it, but a docs-only disposable PR is safer because this branch’s `trust-ci/**` diff is governance. |
| 7 Approval behavior | CLI + unit tests | Live disposable PR: docs-only vs `trust-ci/**` needs_approval, wrong signer, tamper, replay, new commit/policy digest invalidation. Human Ed25519 private key must stay off this workspace. |
| 8 Protect `main` | `branch-protect` CLI + tests | Apply only after a successful App-owned check exists. Bind exact policy-epoch name + App ID. Negative tests: direct push, merge without the check, same check text from another actor. |
| 9 Finish PR #2 | reviews already on `5915b56` | Commit **this** docs pass on `feat/trust-ci-control-plane`, update the draft, attach digests / App ID without secrets / check run ID. Do not merge unless the user explicitly orders it after external evidence. Do not push `main`. |

Handoff “Current code state / Fresh local verification” still claims 4 skipped Postgres tests. That paragraph is stale vs `tasks.md` 8/8 + restart drill PASS. Do not “fix” it by adding GitHub Actions or by treating local receipts as merge authority.

---

## 7. Write-owner resume order

1. Materialize a **new** `protected-path-write` grant for **current** HEAD `5915b56` + **current dirty fingerprint**, resources at least `README.md`, `trust-ci/README.md`, `decisions.md`. Optionally include the already-dirty protected files if they will be edited again.
2. Apply §4.1–4.3. Optionally fix QUICKSTART draft-PR sentence.
3. `PYTHONPATH=.grok-stack python3 -m unittest tests.test_structure.StructureTests.test_readme_stack_graph_is_complete tests.test_toolchain.ToolchainTests.test_real_toolchain_json_required_and_optional_sets`
4. `python3 scripts/grok_verify.py --mode pr` and route reviews (`code_reviewer` + `test_reviewer` on this route).
5. Do not start handoff steps 3–9 from this docs pass. Those are operational and need an exact delegated grant per named action/resource.
6. Leave `20260817-user-query-вычисти-*` untracked.

Route `56da62035c35` analysis complete. Write owner is `general_implementer`.
