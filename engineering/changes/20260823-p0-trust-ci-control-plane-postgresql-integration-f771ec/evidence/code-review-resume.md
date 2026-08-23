# Code review — README / QUICKSTART / toolchain resume (K16, two-file compose)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Route: `56da62035c35` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-23

HEAD still `5915b56db7d6aedcd52a6c023418db84d45dd98f`. Product identity `VERSION` **2.0.11**. Working tree is dirty (docs/toolchain/tests + change-package evidence). No commit, push, merge, or deploy in this review.

**PASS.** I would not block this slice.

This resume is documentation, toolchain pins, and structure/toolchain tests. It is not GitHub App activation, image pin, deploy, or branch protection. Local receipts are not merge authority.

---

## Verdict against the assigned focus

| # | Check | Result |
| --- | --- | --- |
| 1 | README mermaid K16: 16 IDs, C(16,2)=120 `---` edges, no `-->` | **PASS.** Independent parse: 16 nodes, 120 unique undirected edges, 0 missing, 0 extra, 0 duplicates, 0 arrows. |
| 2 | Trust CI nodes in the node-role table + oneshot/DinD footnote | **PASS.** TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp. |
| 3 | Grok CLI built/fallback `1.0.5`; H1 matches VERSION `2.0.11` | **PASS.** H1 `# Adaptive Grok Build Pro v2.0.11`. No leftover `1.0.4` in README/toolchain. Trust CI **2.1.0** is a separate identity sentence. |
| 4 | Optional docker / syft / trivy / cosign; no required docker; no grype pin | **PASS.** All four `required: false`. Only python3/git/grok are `required: true`. No `grype` tool id. |
| 5 | `trust-ci/README.md` two-file compose merge, inspect `$TRUST_CI_*_IMAGE`, `make trust-ci-postgres-test` / `--exit-code-from postgres-integration` | **PASS.** Matches `compose.build.yaml` and `compose.test.yaml` service names. |
| 6 | QUICKSTART operator sections; disposable docs PR first (draft or not); drafts are not ignored | **PASS.** Matches `webhooks.py` (no draft skip) and `test_draft_pull_request_is_enqueued`. |
| 7 | `engineering/runbooks/trust-ci-rollout.md` two-file merge | **PASS.** Build/inspect/harness commands updated. |
| 8 | Tests: `test_readme_stack_graph_is_complete` (16 nodes, C(n,2)); four toolchain ids `required: false` | **PASS.** Re-ran 5 focused tests, OK. |
| 9 | `decisions.md` K16 ruling (3 sentences); `mistakes.md` first protected write consumes grant | **PASS.** Historical K10 entry kept. |
| 10 | VERSION still 2.0.11; no `.github/workflows`; no invented digests | **PASS.** `.github/` absent. Example pins stay `REPLACE_WITH_*`. |
| 11 | Do not commit `20260817-вычисти*` leftover | Residual only: package is untracked, not in the product diff. |
| 12 | Residual risk / would you block? | Residuals only. **No block.** |

Would I block? **No.**

---

## What was actually inspected

```text
# refs
HEAD                                           → 5915b56db7d6aedcd52a6c023418db84d45dd98f
git diff --name-status HEAD                    → 10 modified paths (uncommitted)

# product delta vs 5915b56
README.md
trust-ci/README.md
QUICKSTART.md
.grok-stack/config/toolchain.json
tests/test_structure.py
tests/test_toolchain.py
engineering/runbooks/trust-ci-rollout.md
decisions.md
mistakes.md
engineering/changes/…-f771ec/tasks.md

# surrounding implementation (not in this delta; contracts)
trust-ci/{compose.yaml,compose.build.yaml,compose.test.yaml}
trust-ci/scripts/postgres-integration.sh
Makefile  (trust-ci-postgres-test)
trust-ci/src/adaptive_trust_ci/webhooks.py
trust-ci/tests/test_webhooks_github.py
trust-ci/.env.example
VERSION
.gitignore
AGENTS.md stack-graph rule

# absences
.github/          does not exist
.github/workflows does not exist
grype             not in toolchain.json
```

No `.env`, PEM, App key, webhook secret, or human private key was read. `trust-ci/runtime/github-app-private-key.pem` is gitignored (`trust-ci/runtime/*` + `*.pem`) and is not in the diff. No push, merge, or deploy.

Independent mermaid check (not the implementer’s report): first README fence has 120 `\S+ --- \S+` lines, 0 `-->`, unique undirected set equals `itertools.combinations` of the 16 IDs.

Focused tests re-run here:

```text
python3 -m unittest \
  tests.test_structure.StructureTests.test_readme_stack_graph_is_complete \
  tests.test_structure.StructureTests.test_version_identity_matches_readme \
  tests.test_structure.StructureTests.test_no_github_actions_workflow_exists \
  tests.test_toolchain.ToolchainTests.test_real_toolchain_json_required_and_optional_sets \
  tests.test_toolchain.ToolchainTests.test_optional_missing_does_not_fail_doctor -q
```

`Ran 5 tests in 0.748s` — **OK**.

`python3 scripts/grok_verify.py --mode pr` is reported already PASS on this tree. This review did not re-run the full suite. Local receipts remain preflight, not the App-owned Check Run.

---

## 1. README K16 graph

Caption no longer claims Trust CI is outside the graph. The listed set is the local workflow plus Trust CI applications and PostgreSQL. Prompts/receipts/grants are still not merge authority.

Declared mermaid IDs: Route, Skills, Agents, Hooks, Policy, Verify, Packages, Contract, Decisions, Mistakes, TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp.

C(16,2) = 120. The working-tree fence contains exactly those 120 undirected pairs, each as `A --- B`, none as `A --> B`. Node-role table has all 16 rows. Footnote correctly treats `migrate` / `runner-loader` as oneshots reusing API/worker images and DinD as an execution edge of Runner, not extra clique members.

`tests/test_structure.py` renamed `test_readme_local_stack_graph_is_complete_k10` → `test_readme_stack_graph_is_complete`, extended the node list by the six Trust CI IDs, and asserts `len(edge_lines) == len(list(itertools.combinations(nodes, 2)))` instead of a hardcoded 45.

H1 `# Adaptive Grok Build Pro v2.0.11` matches `VERSION`. Grok row is 1.0.0 / 1.0.5 / 1.0.5. Docker/Syft/Trivy/Cosign rows are optional; Cosign built is `—`, matching toolchain (no `built` key).

---

## 2. Two-file compose docs vs the tree

Production `compose.yaml` has **no** `build:` keys. Images are `${TRUST_CI_*_IMAGE:?…}`. `compose.build.yaml` adds build for `migrate`/`api`/`worker`/`runner-image`; only `runner-image` sets a local tag (`adaptive-trust-ci-runner:2.1.0`).

Product docs now use:

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" …
```

Stale `docker compose --profile build build` against `compose.yaml` alone and inspect of `adaptive-trust-ci-api:2.1.0` are gone as commands. Remaining mentions of that tag are explicit **do not inspect** warnings. That matches the compose files.

`compose.test.yaml` services are `postgres-test` and `postgres-integration` (no `tests`). Makefile and `postgres-integration.sh` use `--exit-code-from postgres-integration`. README/QUICKSTART/runbook now say `make trust-ci-postgres-test` or the postgres-integration exit-code form. No product-doc `--exit-code-from tests` remains (only historical evidence reports).

---

## 3. Toolchain and tests

`.grok-stack/config/toolchain.json` grok `built`/`fallback` `1.0.5`. Appended:

| id | profile | required | built / fallback |
| --- | --- | --- | --- |
| docker | trust-ci | false | 29.7.2 / 29 |
| syft | supply-chain | false | 1.51.0 / 1.51 |
| trivy | supply-chain | false | 0.74.0 / 0.74 |
| cosign | supply-chain | false | (none) / 2.4 |

No `grype`. No standalone `docker-compose` tool id. Optional missing docker cannot fail `grok_verify` / doctor (`check_tool` → `info` when `required` is false; `test_optional_missing_does_not_fail_doctor` still passes). QUICKSTART may mention grype as “not a product pin”; that is not a pin.

`toolchain.py` already treats missing `built` as empty string, so cosign without `built` is valid.

---

## 4. QUICKSTART vs webhook behavior

Operator sections cover PostgreSQL roles, template copy (including `.env` / `migration.env` / `backup.env`), live harness, two-file build, keys split, start/health, webhook-then-prove-then-branch-protect, backup/kill-switch/supply-chain.

Proof order: disposable docs PR **(draft or not)** before `branch-protect`. “Draft PRs are ignored” is absent. Surrounding parser in `webhooks.py` has no draft filter; `test_draft_pull_request_is_enqueued` requires a non-None, non-closed event for `draft=true`.

---

## 5. Self-learning logs

`decisions.md` 2026-08-23 K16 entry is three sentences: Trust CI nodes are listed, first mermaid is a K16 of 120 `---` edges, missing pair = stale map, receipts still not merge authority. Historical 2026-08-16 K10 entry remains.

`mistakes.md` records the actual crash cause: a fingerprint-bound protected-path grant is consumed by the first successful tree mutation; remaining listed resources need a fresh grant or one parallel batch.

---

## Change-package / contract fit

In scope for this resume (tasks.md now checked): K16 graph, two-file compose docs, optional docker/syft/trivy/cosign pins.

Out of scope and still open (do not treat this dirty tree as activation complete):

- digest-pinned API/worker/runner images in deployed env (no invented git digests)
- GitHub App create/install
- isolated deploy, HMAC webhook, App-owned check on the exact SHA
- app-bound `branch-protect`
- merge of draft PR `#2`

`.env.example` still uses `REPLACE_WITH_*` placeholders, not fabricated 64-hex digests. Correct for this slice.

---

## Residuals (non-blocking)

1. `engineering/runbooks/trust-ci-rollout.md` bootstrap copy list still omits `.env.example`, `migration.env.example`, and `backup.env.example`. QUICKSTART and `trust-ci/README.md` include them. `compose.yaml` `migrate` requires `env/migration.env`. Copy-paste of the runbook-only bootstrap is incomplete; the two-file merge itself is correct.
2. `test_readme_stack_graph_is_complete` does not assert absence of `-->`. The working mermaid has zero arrows; a later `-->` plus 120 `---` lines would still pass the count.
3. `test_toolchain.py` does not lock grok `built`/`fallback` `1.0.5`. README and `toolchain.json` do.
4. Untracked leftover `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` is still on disk. **Do not add it to the commit set.**
5. `docker image inspect "$TRUST_CI_*_IMAGE" … RepoDigests` is empty until a registry push. Docs do not invent a digest to paper over that. Build-without-push remains a later operational step.
6. `trust-ci/README.md` `chmod 600` no longer covers `runtime/*` (now `env/*.env .env`). Public trust-store JSON is not a secret; filled env files are. Acceptable.
7. Activation (App, deploy, branch protection) is not in this diff. Do not merge `#2` on this evidence.

---

## Ruling

The uncommitted product delta vs `5915b56` finishes the crashed README/QUICKSTART/toolchain/docs pass: a real K16 clique, compose commands that match the two-file build and `postgres-integration` service, optional supply-chain/Docker pins without making docker required or adding grype, VERSION/H1 still 2.0.11, no GitHub Actions, no invented digests. Surrounding compose, Makefile, webhook parser, and `.env.example` placeholders are consistent with that delta.

**PASS.**
