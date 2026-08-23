# Code review — local image build-without-push smoke (frozen docs/toolchain tree)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Route: `d2ba49e0570d` · reviewer: `code_reviewer` (read-only) · write owner: `general_implementer`  
Reviewed: 2026-08-23

HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`.  
Product identity `VERSION` **2.0.11**. Trust CI identity **2.1.0**. Working tree is dirty. No commit, push, merge, or deploy in this review.

Parent stated `python3 scripts/grok_verify.py --mode pr` **PASS** (git-diff-check, secret-scan, ruff, bandit, python-unittest, coverage). This review did not re-run verify or Docker inspect; it inspected the actual `git diff HEAD`, surrounding examples/contracts, and `evidence/implementation-images.md`.

**PASS.** I would not block this tree.

This slice is a daemon compile plus change-package evidence on top of the previously reviewed docs/toolchain delta. It is not HANDOFF §3 pin, GitHub App activation, deploy, or branch protection. Local receipts are not merge authority.

---

## Verdict against the assigned focus

| # | Check | Result |
| --- | --- | --- |
| 1 | No invented image/holdout/policy digest in tracked files (`REPLACE_WITH_*` still in examples) | **PASS.** Diff does not fill any `name@sha256:<64 hex>`. Example env/policy still use `REPLACE_WITH_*`. Example holdout digest is the pre-existing test-locked bundle hash, unchanged. |
| 2 | README first mermaid is K16 complete (120 `---` edges, 0 `-->`) | **PASS.** Independent parse: 16 node IDs, 120 `^\s+\S+ --- \S+\s*$` lines, 0 `-->` in README, unique undirected set is C(16,2). |
| 3 | VERSION/H1 still 2.0.11; Trust CI 2.1.0 not collapsed | **PASS.** `VERSION` = `2.0.11`. README H1 `# Adaptive Grok Build Pro v2.0.11`. Separate sentence: Trust CI **2.1.0** (`trust-ci/pyproject.toml`); it is not product `2.0.11`. |
| 4 | No `.github/workflows` | **PASS.** `.github/` does not exist. Not in the diff. Structure test still asserts absence. |
| 5 | `implementation-images.md` does not format local Ids as deploy pins; RepoDigests==.Id labeled not-a-pin | **PASS.** `.Id` column is `local-image-id, not a registry pin`. RepoDigests JSON is inspect dump; text says Engine 29 `RepoDigests` equalled `.Id`, **local-daemon-descriptor, not a registry pin**, do not copy into examples. |
| 6 | Leftover `20260817-вычисти*` is untracked, not in the product diff | **PASS.** `git status` shows `?? engineering/changes/20260817-user-query-вычисти-…-33e0c2/`. `git diff HEAD --name-only` is 13 paths; leftover is not among them. |
| 7 | Would you block this tree? | Residuals only. **No block.** |

Would I block? **No.**

---

## What was actually inspected

```text
# refs
HEAD                                           → 5915b56db7d6aedcd52a6c023418db84d45dd98f
branch                                         → feat/trust-ci-control-plane
git diff HEAD --name-status                    → 13 modified tracked paths (uncommitted)
git status --untracked-files                   → leftover 20260817-вычисти* + this change evidence/*

# product + paperwork delta vs 5915b56
README.md
QUICKSTART.md
trust-ci/README.md
.grok-stack/config/toolchain.json
tests/test_structure.py
tests/test_toolchain.py
engineering/runbooks/trust-ci-rollout.md
decisions.md
mistakes.md
engineering/changes/…-f771ec/{architecture,tasks,test-plan,state}.md/.json

# this-slice evidence (untracked)
engineering/changes/…-f771ec/evidence/implementation-images.md

# surrounding contracts (not in this delta)
VERSION
trust-ci/pyproject.toml                         version = "2.1.0"
trust-ci/.env.example                           REPLACE_WITH_* still
trust-ci/config/policy.example.json             runner REPLACE_WITH_*; holdout.digest unchanged
trust-ci/env/*.example
trust-ci/config/trust-store.example.json
tests/test_structure.py::test_no_github_actions_workflow_exists
tests/test_structure.py::test_trust_ci_policy_uses_immutable_sandbox_and_external_status
.gitignore                                      .env, *.pem, trust-ci/env/*.env, trust-ci/runtime/*

# absences
.github/          does not exist
.github/workflows does not exist
```

No `.env`, PEM, App key, webhook secret, or human private key was read. `trust-ci/runtime/github-app-private-key.pem` is gitignored and is not in the diff. No push, merge, or deploy.

Independent mermaid check (not the implementer’s report): first (only) README ` ```mermaid ` fence has **120** `\S+ --- \S+` lines, **0** `-->`, 16 IDs (`Route`, `Skills`, `Agents`, `Hooks`, `Policy`, `Verify`, `Packages`, `Contract`, `Decisions`, `Mistakes`, `TrustAPI`, `TrustWorker`, `Postgres`, `Runner`, `Holdout`, `GitHubApp`). C(16,2)=120. Combination order matches the fence; no missing pair, no extra, no duplicate, no self-loop.

---

## 1. No invented image / holdout / policy digest in tracked files

`git diff HEAD` for product files contains **no** `sha256:[0-9a-fA-F]{64}`. README, QUICKSTART, toolchain.json, decisions.md, mistakes.md, tests, and the runbook have none.

Tracked examples (not in this diff; still match HEAD):

| File | Pin field | Current value |
| --- | --- | --- |
| `trust-ci/.env.example` | six `TRUST_CI_*_IMAGE` | `…@sha256:REPLACE_WITH_{BASE,POSTGRES,DIND,API,WORKER,RUNNER}_DIGEST` |
| `trust-ci/config/policy.example.json` | `sandbox.image` | `adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST` |
| same | `holdout.digest` | `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8` (example bundle; already locked by `test_ops.test_example_holdout_digest_matches_example_bundle`; **not** introduced this turn) |

`tests/test_structure.py::test_trust_ci_policy_uses_immutable_sandbox_and_external_status` still allows the placeholder **or** a real `@sha256:[0-9a-f]{64}`. Filling `policy.example.json` with a local Id would pass that test. The working tree did **not** do that.

Measured python Hub digest and local api/worker/runner `.Id` values appear only in untracked `evidence/implementation-images.md` (and, per that file, untracked `/tmp` env). They are labeled not-a-pin / untracked-env-only. That is evidence, not a deployed policy pin.

---

## 2. README first mermaid is K16 complete

Diff adds six Trust CI nodes and the missing clique edges. Current fence:

- 16 node IDs
- 120 undirected `---` edges
- 0 `-->` anywhere in README.md
- node-role table includes TrustAPI, TrustWorker, Postgres, Runner, Holdout, GitHubApp
- oneshot/DinD footnote present

`test_readme_stack_graph_is_complete` now uses `itertools.combinations(nodes, 2)` instead of the old K10 `== 45`. That matches AGENTS.md (“every listed core node is linked to every other with a `---` edge”).

---

## 3. VERSION / H1 2.0.11; Trust CI 2.1.0 not collapsed

| Identity | Evidence |
| --- | --- |
| Product 2.0.11 | `VERSION` file (not in the diff). README H1 unchanged. Current-state bullet Identity **2.0.11**. |
| Trust CI 2.1.0 | `trust-ci/pyproject.toml` `version = "2.1.0"` (not in the diff). README **adds** “Trust CI service identity is **2.1.0** … it is not product `2.0.11`.” |
| Grok CLI 1.0.5 | README table and toolchain.json `built`/`fallback` 1.0.4 → 1.0.5. Not a product-version bump. |

No collapse of 2.1.0 into 2.0.11.

---

## 4. No GitHub Actions

`.github/` is absent on disk. Diff paths do not include workflows. `test_no_github_actions_workflow_exists` is unchanged. Brief still lists `.github/workflows/**` as out of scope.

---

## 5. `implementation-images.md` labeling

Write owner froze product files. This file is untracked change-package evidence.

| Claim in the evidence | Review |
| --- | --- |
| Two-file `--profile build build api worker runner-image`, no `--push`, no `up` | Matches architecture ruling for this turn. |
| Just-built `:2.1.0` Ids vs leftover 18:46Z images | Leftover Ids (`9b957043…`, `ef58751c…`, `8ceb98cd…`) are marked stale; new Ids (`70a80960…`, `bffd013c…`, `900cfaaa…`) are the smoke. |
| `.Id` column header | `` `.Id` (`local-image-id, not a registry pin`) `` |
| RepoDigests JSON | Quoted as inspect output; next paragraph: **RepoDigests equalled `.Id`**, no registry host, **local-daemon-descriptor, not a registry pin**. Do not copy into `policy.example.json` or `.env.example`. Do not format as a deploy pin. |
| Python base `sha256:a116514e…` | Measured after `docker pull`; stated to live **only** in untracked `/tmp/adaptive-trust-ci-build.env`. Not written to tracked examples. |
| Example holdout unittest OK | Command used `PYTHONPATH=…/src:…/tests` (support-module fix). Did not change `policy.example.json`. |
| Product sha256 frozen vs pre-smoke | Matches `git status`: no extra product hunks beyond the prior docs/toolchain slice. |

Architect allowed quoting an Id in the tracked summary **if** labeled `local-image-id, not a registry pin`, and forbade formatting it as a deploy `name@sha256:<id>`. The table’s RepoDigests column is inspect JSON (which on Engine 29 is `name@sha256:<same hex as .Id>`), not a “put this in policy” pin. That satisfies the assigned check.

---

## 6. Leftover `20260817-вычисти*`

Directory exists: `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/`.  
`git status --short` lists it as `??`. It is not in `git diff HEAD`. Architecture now says do not commit it. Residual only: keep it out of any later `git add`.

---

## Product delta still in the dirty tree (docs/toolchain)

This is the previously independently reviewed resume (`code-review-resume.md`), still uncommitted, plus this turn’s paperwork:

- Optional docker / syft / trivy / cosign in toolchain.json, all `required: false`. No grype.
- Two-file compose merge in `trust-ci/README.md` and the rollout runbook; inspect `$TRUST_CI_*_IMAGE`; `make trust-ci-postgres-test` / `--exit-code-from postgres-integration`.
- QUICKSTART operator sections; drafts are not ignored.
- `decisions.md` K16 ruling; `mistakes.md` first protected write consumes grant.

Those hunks do not invent digests or add workflows. They remain coherent with this smoke.

Change-package this turn: architecture freeze/smoke rules, tasks checkbox for local smoke (pin/App/deploy still open), test-plan P1 for build-without-push evidence, `state.json` → `reviewing`.

---

## Residuals (not blocking)

- Operator inspect recipes in QUICKSTART / `trust-ci/README.md` / rollout still print `{{index .RepoDigests 0}}` without the Engine-29 “equals `.Id` ⇒ not a pin” sentence. Architecture for **this** slice records that caveat. Docs slice was already reviewed; do not treat leftover inspect prose as a HANDOFF §3 pin.
- Compose warning `The "resolved" variable is not set` during build: product file, frozen this slice.
- Cosign absent; no `cosign sign`. Out of slice.
- `/tmp` env-file instead of gitignored `trust-ci/runtime/build-smoke/`: hook blocked `trust-ci/**` mutation. Evidence is in the change package, which is the allowed place.
- HANDOFF §3 registry pin, GitHub App, TLS, `compose up`, `branch-protect` remain open tasks. Port `127.0.0.1:8080` is still searxng.
- Dirty tree is expected. Do not stage leftover `20260817-вычисти*` or any `/tmp` env.

---

## Block decision

The tree matches the change-package ruling for this turn: freeze the reviewed docs/toolchain product files, record a local build-without-push, keep `REPLACE_WITH_*` in examples, do not invent a deploy pin, do not add GitHub Actions, do not collapse 2.0.11 / 2.1.0, do not commit the leftover 20260817 package.

I would **not** block this tree.

**PASS.** Would not block.
