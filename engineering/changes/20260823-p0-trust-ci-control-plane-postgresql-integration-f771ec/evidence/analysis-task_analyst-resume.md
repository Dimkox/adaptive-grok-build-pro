# Task analyst — resume acceptance (not a new design)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `56da62035c35` (intent=feature, write=`general_implementer`, reviews=`code_reviewer`+`test_reviewer`, evidence=`verification`+`code_review`+`test_review`)  
Prior docs route that crashed: `2335b3d0d9fc`  
Last session: `2026-08-23T19:31:20+00:00` reason=`shutdown`  
Agent: `task_analyst` (read-only except this report)

This is a resume of unfinished work on the existing Trust CI activation change. `GROK_BUILD_HANDOFF.md` remains the user-approved operational sequence. Do not reopen product design.

---

## Crash point

The last productive slice was the README / QUICKSTART / toolchain refresh. It died after the first protected-path batch, not during Trust CI code design.

1. Grant `6fcd3898df7b0eae` (`protected-path-write`, source=`explicit-user-consent`, route `2335b3d0d9fc`, HEAD `5915b56db7d6aedcd52a6c023418db84d45dd98f`, fingerprint `aa731cb93c12…`) authorized `README.md`, `trust-ci/README.md`, `decisions.md`, tests, toolchain, QUICKSTART, and the runbook.
2. The write owner used that grant to land tests + `toolchain.json`. That dirty-tree write changed the fingerprint, so the grant became stale.
3. PreToolUse then denied structured writes:

   - `README.md`
   - `trust-ci/README.md`
   - `decisions.md`

4. Session ended `shutdown` before a replacement grant could be minted. No shell mutation of those files is allowed.

`has_valid_approval` binds repository + **current** `route_id` + change + Git HEAD + tree fingerprint. The grant is now invalid for **three** independent reasons, any one of which is enough:

| Binding | Grant `6fcd3898` | Now |
| --- | --- | --- |
| `route_id` | `2335b3d0d9fc` | `56da62035c35` |
| `tree_fingerprint` | `aa731cb93c12…` | last-fingerprint `d0a1bbb0cebdc0ea…` (dirty tree after tests/toolchain/QUICKSTART/runbook) |
| TTL | expires `2026-08-23T20:53:28Z` | still inside the window; TTL does not rescue a binding miss |

Older grants in `.grok-stack/runtime/approvals.json` (`0b7f4cfda7acdf96`, `a66b092309fcdd02`, `1c1927d340e09116`, `0c37edeb8cdd5e5b`, `5eb8ab066c9f0aa8`, `e058d458caabc881`) are bound to route `f771ecaf458d` and HEAD `04348db…`. They cannot be reused.

Do not reuse grant `6fcd3898`. Mint a new grant on route `56da62035c35` after measuring the **current** HEAD and fingerprint, covering every remaining protected path **before** the first remaining write.

---

## Already landed (do not redo)

Uncommitted / dirty from the crashed pass (keep; do not revert):

| File | State | Grant needed to re-edit? |
| --- | --- | --- |
| `tests/test_structure.py` | Renamed `test_readme_stack_graph_is_complete`; 16 node IDs; edge count = `C(n,2)` = 120 | yes (already done) |
| `tests/test_toolchain.py` | Asserts `docker`, `syft`, `trivy`, `cosign` exist and `required: false` | yes (already done) |
| `.grok-stack/config/toolchain.json` | grok built/fallback `1.0.5`; appended those four optional tools | yes (already done) |
| `QUICKSTART.md` | Consumer 0–7 kept; operator Postgres/build/keys/webhook/supply-chain sections added | **no** (unprotected) |
| `engineering/runbooks/trust-ci-rollout.md` | Two-file compose merge, `$TRUST_CI_*_IMAGE` inspect, `postgres-integration` exit-code | no (not a protected glob) |

Host tools already present from the earlier “поставь syft/trivy/grype” request: syft `1.51.0`, trivy `0.74.0`, grype present on the host. Tree scanners are **syft / trivy / cosign**. Do not add `grype` to `toolchain.json`. Cosign is still not installed; toolchain fallback is `2.4` / linux pin `v2.4.3`.

Already done on this change (tasks.md, prior reviews on `2865fdc` / rebased `dbace962`):

- Baseline repairs, draft-PR webhook enqueue (`test_draft_pull_request_is_enqueued`; `webhooks.py` does not drop `draft=true`).
- Live PostgreSQL integration 8/8 and restart drill PASS.
- Control-plane code: API/worker split, HMAC webhooks, Checks payload, holdout, isolated runner, app-bound protection payload.
- PR `#2` exists and stays draft until the App-owned check is observed.

Those older review files (`evidence/code-review.md`, `test-review.md`, receipts under route `f771ecaf458d`) are **stale for this resume**. Any docs/graph write invalidates them again. Rerun `grok_verify --mode pr` and the **current** route reviews after the docs tree is final.

---

## A. Finish the crashed docs/graph pass (in-tree)

This is the immediate unfinished work. Acceptance is local and test-locked. It does not create the Trust CI check.

### A1. `README.md` — K16 complete graph

Replace the first (only) mermaid fence. Current fence is still K10 / 45 `---` edges and the caption still says Trust CI is outside the graph. `test_readme_stack_graph_is_complete` will fail until this matches the already-updated test.

Exact vertex IDs (order as in `tests/test_structure.py`):

```text
Route Skills Agents Hooks Policy Verify Packages Contract Decisions Mistakes
TrustAPI TrustWorker Postgres Runner Holdout GitHubApp
```

Rules:

- `C(16,2) = 120` undirected `---` lines, generated from `itertools.combinations(nodes, 2)`.
- No `-->`, no duplicate pairs, no extra `---` lines (count is exact equality).
- Keep every pair **inside** the mermaid fence (the pair scan is whole-file; the count scan is first fence only).
- Caption: local workflow **plus** independently deployed Trust CI applications and PostgreSQL; prompts are still not merge authority.
- Node-role table: all 16 IDs. Oneshots `migrate` / `runner-loader` are footnotes, not extra vertices. DinD is an edge of Runner, not a 17th node.
- H1 stays `# Adaptive Grok Build Pro v2.0.11`. Do not bump `VERSION`.
- Requirements table must match `toolchain.json`: grok built/fallback `1.0.5`; add optional rows docker / syft / trivy / cosign (`required` no). Do not list grype.
- Current-state section already names Trust CI; keep product `2.0.11` vs service `2.1.0` explicit.

### A2. `trust-ci/README.md` — stop teaching commands that fail

Stale today (must change):

```text
docker compose --profile build build api worker runner-image          # compose.yaml has no build:
docker image inspect adaptive-trust-ci-api:2.1.0
docker image inspect adaptive-trust-ci-worker:2.1.0
docker compose -f trust-ci/compose.test.yaml … --exit-code-from tests
docker compose -f trust-ci/compose.yaml build api worker
```

Use the same commands already in QUICKSTART / runbook:

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
# same for WORKER and RUNNER
make trust-ci-postgres-test
# or --exit-code-from postgres-integration
```

### A3. `decisions.md` — K16 ruling

One ≤3-sentence entry: AGENTS.md completeness is over **listed** core nodes; Trust CI API/worker/Postgres/runner/holdout/GitHub App are now listed, so the first fence is K16 / 120 edges; the structure test derives `C(n,2)` instead of a K10 literal.

Do not rewrite the 2026-08-16 K10 entry (history). Do not revive the 2026-08-17 “always push main” decision; `AGENTS.md` forbids direct push to `main`.

### A4. `QUICKSTART.md` polish (no grant)

Fix the landed contradiction: “Draft PRs are ignored” is false. Code and `decisions.md` enqueue opened/synchronize/reopened drafts so PR `#2` can stay draft until the check exists. Keep the rest of the operator split.

Do **not** paste a second 120-edge mermaid into QUICKSTART.

### A5. Local close for slice A

After the three protected files plus QUICKSTART:

1. `PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest tests.test_structure tests.test_toolchain -v`
2. `python3 scripts/grok_verify.py --mode pr`
3. Current-route reviews only: `code_reviewer`, `test_reviewer` on the **final** docs tree.
4. Record `verification`, `code_review`, `test_review` against that fingerprint.

Slice A is **not** “Trust CI activated”. It is “tree docs/graph/pins match the already-landed tests so the dirty working tree is green.”

### A — grant to mint first

```text
scope: protected-path
action: protected-path-write
resources (exact, all in one grant):
  README.md
  trust-ci/README.md
  decisions.md
route_id: 56da62035c35
change: 20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec
git_head / tree_fingerprint: measure immediately before mint; do not copy aa731cb93c12 or d0a1bbb0 from this report
source: explicit-user-consent
reason: resume crashed README/K16 + trust-ci README compose fix + K16 decisions ruling
```

Consent already present for this mint: (1) this user turn (“находи место падения и доделывай задачи”), (2) prior explicit README/QUICKSTART/toolchain refresh, (3) HANDOFF standing operational consent. Wildcard scope is forbidden. Write all three protected files under that one grant without an intervening extra protected write. If any extra protected file is touched, remint.

---

## B. Operational Trust CI steps — standing HANDOFF vs new exact grants

`GROK_BUILD_HANDOFF.md` is user-approved **order**, not a live grant. Local grants never create `adaptive-trust-ci/verified` and never substitute Ed25519 human approvals.

Standing HANDOFF consent **does** cover continuing steps 1–9 as written, including rematerializing exact grants for named in-scope operations when bindings match. It does **not** cover merge, `main` push, GitHub Actions, human private keys, or mutating unrelated host services.

| Handoff / tasks.md item | Status | Standing HANDOFF enough to *intend*? | Live grant still required? | Exact grant / actor |
| --- | --- | --- | --- | --- |
| 1. Reproduce local baseline | Done earlier; **re-run after slice A** (dirty tests now expect K16) | yes | no | in-tree unittest / `grok_verify` |
| 2. Live PostgreSQL 8/8 + restart drill | Done (PASS) | yes | no | do not treat as remaining unless A/B dirty the harness |
| 3. Build API/worker/runner/holdout **locally** and record digests | Unchecked | yes | no for `docker compose … build` / `holdout-digest` | do not commit private keys or filled `env/*.env` |
| 3b. `docker push` / `supply-chain-release.sh --confirm-push` | Unchecked | **no** (registry write) | **yes, new** | `production` + `docker-push`, or `external-write` with explicit registry URL. Mint only if the user names the registry. Local pin in `.env` / `runtime/policy.json` (gitignored) does not need push. |
| 4. Create/install GitHub App | Unchecked | order yes; **execution is human** | no grok_approve action exists | Browser/manifest on GitHub. Permissions: Checks r/w, Contents read, PRs read, Metadata read. Worker-only App RSA key; API-only webhook secret. Agent must not invent App ID / installation ID / key. User supplies those values into **untracked** worker env. |
| 5. Deploy isolated API/worker/postgres/holdout/TLS | Unchecked | HANDOFF step 5 orders isolated deploy | **yes if it is a host deploy** | Not a `production_action` string, but AGENTS.md still forbids production mutation without an exact named operation. Treat `compose up` / systemd enable on this machine as deploy. Architecture residual: `127.0.0.1:8080` is already bound (searxng) — do not steal it; pick a free loopback + reverse proxy. Do not colocate privileged DinD with production workloads. Stop for a named deploy grant/resource if this is not a dedicated CI VM. |
| 6. Register HMAC webhook + prove App-owned check | Unchecked | order yes | **yes** for GitHub mutation | `external-write` resource `github-api` (or the webhook URL) for `gh api` POST. Proof: webhook 2xx → Postgres exact-SHA job → one worker lease → holdout outside checkout → source mutation still fails → signed attestation → Check Run `adaptive-trust-ci/verified@<policy-sha12>` owned by the App. Draft `#2` **does** enqueue (code). Prefer proving on `#2` now that drafts enqueue; a disposable non-draft PR is optional extra, not a replacement for `#2`. |
| 7. Prove approval behavior | Unchecked (handoff; not in tasks.md checkboxes) | yes as sequence | human signs off-box | Disposable `trust-ci/**` diff → `needs_approval`. Agent must **not** generate, read, or submit the human private key. Human runs `adaptive-trust-ci approval-create` on a human machine and submits the envelope to the API. |
| 8. `branch-protect` on `main` | Unchecked | only **after** the App-owned check exists | **yes, new** | Temporary human admin token (`TRUST_CI_GITHUB_ADMIN_TOKEN`). Long-lived App must not have `administration`. Payload binds exact policy-epoch check name + App ID. `gh api` PUT → `external-write`/`github-api`. Do not apply before the check is observed (lockout risk). |
| 9. Commit + update draft PR `#2` | Unchecked | standing operational release + this resume | **yes, new, last** | `git add`/`commit` on `feat/trust-ci-control-plane` is in-tree. `git push origin feat/trust-ci-control-plane` needs `production` + `git-push-branch` bound to the **post-commit** SHA/fingerprint. Resource if named: that branch only. **Never** `origin main`. |
| Mark `#2` ready for review | After external check + evidence on the PR | HANDOFF yes | `gh pr ready` is GitHub write → exact `external-write` | Still not merge. |
| Merge `#2` | Out of this resume | **no** | would need `pull-request-merge` **and** an explicit later user order after they review the App-owned check | Do not mint. |

### What standing HANDOFF consent is *not*

- A currently valid row in `approvals.json`.
- Authority to skip fingerprint/route rebind.
- Authority to push `main`, merge, tag, or `gh release create`.
- Authority to create the GitHub App or to place secrets in git.
- Authority to run `gh workflow`.

### Mint order for B (only after A is green)

1. Local image build + holdout digest (no grant).
2. Human: App create/install; paste IDs into untracked worker env; generate CI attestation key on the CI host (`adaptive-trust-ci keygen` is CI key, not human approval key).
3. If deploying on this host: named deploy/external grant + free port; do not take searxng’s `:8080`.
4. `external-write` for webhook registration.
5. Synchronize `#2` (may need `git-push-branch` if there is a new commit).
6. Observe App-owned check + offline attestation verify.
7. Human approval proof on a disposable governance diff (human-signed envelope).
8. Only then `branch-protect`.
9. Update `#2` body with SHA, digests, App ID (no secrets), check-run ID, attestation output, residual risks. Keep draft until that evidence is on the PR; then ready-for-review if the user still wants HANDOFF step 9 as written.

Each grant is one-shot: any commit or protected write invalidates it. Mint immediately before the named action.

---

## C. Explicit non-goals (this resume)

- No merge of PR `#2`. No `gh pr merge`. HANDOFF: merge only if the user later orders it after reviewing external evidence.
- No `git push origin main`. Direct push to protected/shared branches remains prohibited even with standing consent.
- No `git-push-tag`, no `github-release`, no VERSION bump, no zip rebuild.
- No human Trust CI approval private key: do not generate, read, request, submit, or simulate. `scripts/grok_approve.py` is not `adaptive-trust-ci approval-create`.
- No GitHub Actions, Dependabot, or `.github/workflows/**`. `workflow-dispatch` is unconditionally denied.
- Do **not** commit `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2` (or any `20260817-вычисти*` leftover). Abandoned 2.0.10 cleanup paperwork; mixing it into PR `#2` is out of scope.
- Do not add `grype` to `toolchain.json` or the README pin table. Optional one-liner that it is not a product scanner is already in QUICKSTART; leave it optional or delete it, do not pin it.
- Do not mark docker/syft/trivy/cosign `required: true` (`test_optional_missing_does_not_fail_doctor` / consumer `install_into`).
- Do not add a root `Dockerfile` / `docker-compose.yml` (flips `trivy-config` and `test_this_repo_shaped_tree_omits_bucket_b`).
- Do not replace PostgreSQL with JSON/SQLite.
- Do not invent image digests, App IDs, check-run IDs, or holdout hashes.
- Do not edit Bitrix core; no new service/queue/database.
- Do not treat local receipts, this file, or delegated grants as merge authority.
- Do not use shell redirects/`python` to mutate protected paths when a grant is missing.
- Ignore stale `architecture.md` line “`write_agent` is null”. Current route write-owner is `general_implementer`. Do not spawn a second writer. Do not reopen design.

---

## Acceptance criteria (resume-sized)

### Slice A — docs/graph (this session’s first close)

- [ ] Grant for `README.md` + `trust-ci/README.md` + `decisions.md` is minted on route `56da62035c35` against the **then-current** HEAD and fingerprint (not `6fcd3898`).
- [ ] First README mermaid is the K16 clique: 16 listed IDs, 120 `---` edges, matching node-role table, caption includes Trust CI + PostgreSQL.
- [ ] `tests.test_structure.TestStructure.test_readme_stack_graph_is_complete` passes.
- [ ] README Requirements table lists docker/syft/trivy/cosign as optional and grok built `1.0.5`.
- [ ] `trust-ci/README.md` bootstrap/verification commands match the two-file compose merge, `$TRUST_CI_*_IMAGE` inspect, and `postgres-integration` (no `--exit-code-from tests`).
- [ ] `decisions.md` has a K16 ruling ≤3 sentences.
- [ ] QUICKSTART says drafts enqueue (matches `webhooks.py` / `test_draft_pull_request_is_enqueued`).
- [ ] No grype pin; VERSION `2.0.11`; no `20260817-вычисти*` in the commit set.
- [ ] `python3 scripts/grok_verify.py --mode pr` plus `code_review` and `test_review` recorded on that fingerprint.

### Slice B — activation (HANDOFF 3–9; after A)

These remain the change-package requirements; they are **not** all closable without new named grants and human App/key steps:

- [ ] Built images and holdout referenced as `name@sha256:<64 hex>` in **deployed** env/policy (not committed secrets).
- [ ] GitHub App installed on `Dimkox/adaptive-grok-build-pro` with the permission split above; App key worker-only; webhook secret API-only.
- [ ] Isolated deploy up; `/health/ready` becomes 200 only with Postgres **and** an active human public key in the trust store.
- [ ] Webhook → exact-SHA job → App-owned policy-epoch check on PR `#2` head; attestation verifies offline.
- [ ] `trust-ci/**` approval path proven with a human-signed envelope generated outside the agent environment.
- [ ] Branch protection applied **only after** that check exists; required check bound to App ID; force-push/deletion disabled.
- [ ] `.github/workflows/` still absent.
- [ ] Draft PR `#2` updated with evidence; still not merged by the agent.

---

## Ordered remaining tasks for `general_implementer`

1. Measure `git rev-parse HEAD` and tree fingerprint. Confirm grant `6fcd3898` does not match. Do not read `.env` or keys.
2. `python3 scripts/grok_approve.py protected-path --action protected-path-write --resource README.md --resource trust-ci/README.md --resource decisions.md --source explicit-user-consent --reason "resume crashed K16 README + trust-ci README compose fix + decisions ruling"` (TTL long enough to finish the three writes, not 24h).
3. Apply K16 mermaid + table + caption + requirements rows to `README.md`.
4. Fix `trust-ci/README.md` compose/inspect/test service names.
5. Add the K16 `decisions.md` ruling.
6. Fix QUICKSTART draft-PR sentence (no grant).
7. Run structure/toolchain tests, then `grok_verify --mode pr`.
8. Dispatch only `code_reviewer` and `test_reviewer`; store reports under this change `evidence/`; `grok_review.py` for `code_review` and `test_review`.
9. **Stop** before image registry push, GitHub App creation, compose deploy, webhook POST, `branch-protect`, or `git push`. Report which B steps need a **new** exact grant vs a human App/key action. Standing HANDOFF is the order, not a substitute grant.
10. If the user then names `git-push-branch` for `feat/trust-ci-control-plane`, mint a **post-commit** production grant and push that branch only. Update PR `#2`. Do not push `main`. Do not merge.

---

Route `56da62035c35` analysis complete. Write owner is `general_implementer`. Reviews after implementation: `code_reviewer`, `test_reviewer`. Local receipts and this file are not merge authority.
