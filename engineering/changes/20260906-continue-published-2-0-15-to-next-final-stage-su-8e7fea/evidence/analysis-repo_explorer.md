# repo_explorer — current product vs stale checkout vs PR #12

Change package: `engineering/changes/20260906-continue-published-2-0-15-to-next-final-stage-su-8e7fea`  
Route assigned: `8e7fea3efac6`  
Inspected: 2026-09-06 (read-only; no product edits)  
Remote: `https://github.com/Dimkox/adaptive-grok-build-pro.git`

## Current vs stale identity

| Surface | SHA | Identity | Notes |
|---|---|---|---|
| **Authoritative product `origin/main`** | `fd51dcfed6b33f4a8707c0db602328146df17cc9` | **VERSION 2.0.15**, tree `f01e9b0d1f80fb6731c68079540fd98e5c1f64ac` | Merge of PR #27 (`feat(pilot): bounded Codex issue-to-draft-PR capability`). Trust CI service `trust-ci/pyproject.toml` remains **2.1.0**. |
| **Stale checkout HEAD** | `7c61e3b647924e5667d171d8b286e5d79b8a4efe` | **VERSION 2.0.12** | Branch `fix/path-aware-shell-policy-circuit-breaker` (merged PR #6 era). Local tracking is **behind origin of that branch by 2**. **Do not treat this tree as the product.** |
| `origin/docs/v2.0.15-published-handoff` | `ef7c8faeb5d339c5b4343de61162ea611c130c4d` | 2.0.15 docs | PR **#28**, MERGEABLE (`clean`), Trust CI `adaptive-trust-ci/verified@06ecf1c875bc` **SUCCESS** (run `101385984851`), GitGuardian SUCCESS. Two commits ahead of main (docs only). |
| `origin/fix/human-approval-cli` | `0f7f508945ccce7dc4f1bffc463247633e9e8f58` | old-epoch 2.0.12-line | PR **#12** unique remaining CLI work. Base still `1c06299894279a88b881defa3f19b004fa742223`. |
| `origin/feat/trust-ci-repository-profiles` | (open PR #13) | old epoch | Separate unique Trust CI profiles; not this successor. |
| `origin/mvp/investor-ready` | (open PR #15) | later/old mix | Independent remaining work; not this successor. |

Merge-base of stale HEAD and `origin/main`: `98f0c45c780c9dd8be6b01afe4667f0b4b0b7630`. `origin/main` is **22 commits** ahead of that stale line. Working-tree `VERSION` file reads `2.0.12`.

README on `origin/main` already states that PRs #12 and #13 remain stale old-epoch `ACTION_REQUIRED` work whose unique lazy CLI imports / repository profiles are absent from main.

## PR #12 GitHub status (do not merge as-is)

- URL: https://github.com/Dimkox/adaptive-grok-build-pro/pull/12
- State: **open**, not draft, **not merged**
- `mergeable_state`: **dirty**
- Head: `0f7f508` on `fix/human-approval-cli`
- Base SHA still **`1c062998`**, not `fd51dcf`
- Single unique commit vs main: `0f7f508 fix: isolate human approval CLI imports`
- Checks: GitGuardian **success**; App check **`adaptive-trust-ci/verified@6737355947c2` ACTION_REQUIRED** (old policy epoch, job `e78d0580-…`, 2026-08-29). Current deployed epoch on later PRs is `@06ecf1c875bc`.
- Updating this PR in place would still be old-epoch ancestry. **Extract onto a new branch from `origin/main`.**

## Unique remaining code still absent from `origin/main`

Triple-dot `origin/main...origin/fix/human-approval-cli` is the unique commit (25 files, +2164/−27). Product-relevant unique files:

### Must extract (behavior)

1. **`trust-ci/src/adaptive_trust_ci/cli.py`**
   - Blob on **main == merge-base** `ab289c7a71dc8f27beef977f56cc6d6654c2b149` (421 lines).
   - PR #12 blob `e2c0def2cb40ec7cd9ac9b009ff6e9efb3d34360` (465 lines).
   - **Eager top-level imports of API/worker/Postgres/backup/GitHub still present on `origin/main`.** Human `approval-create` / `approval-submit` still fail on a minimal host with `ModuleNotFoundError: fastapi`.
   - Unique hunks: delete module-scope product imports; import inside each command branch; `approval-submit` stays stdlib; `_doctor()` lazy-imports server graph.
   - Parser command set on main **equals** PR #12 (17 non-human + human approval commands). Later main commits **did not extend `cli.py`**. Cherry-pick of this file onto `fd51dcf` is expected to apply **cleanly**.

2. **`trust-ci/tests/test_cli.py`**
   - **Does not exist on `origin/main`** (`git ls-tree` empty). Main `trust-ci/tests/` has API/store/policy/etc. but no CLI isolation suite.
   - PR #12 adds 517 lines: `CommandBranchImportTests`, `HumanApprovalCliIsolationTests`, `BlockedImportFinder`, `TrackingModule`.
   - Entire file is unique remaining test code.

3. **`trust-ci/README.md` operator path**
   - Blob on **main == merge-base** `3428182380ba82add962cbb1cbf400137ecacaba`.
   - PR #12 unique: +141/−14 (triple-dot). Operator setup, policy digest, exact-SHA review, one envelope per scope, error/replay guidance, `PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli` help without private keys.
   - Main README already mentions `approval-create` in the general human-key section; the **isolation / minimal-host operator flow is still missing**.

### Supporting unique docs (re-home, do not copy old package as authority)

4. **`decisions.md`** unique paragraph: `## 2026-08-28 — Multi-role CLIs import after command dispatch` — **not on `origin/main`**.
5. **`mistakes.md`** unique entries: Human approval CLI imported the server graph; staged diff check did not stop the commit — **not on `origin/main`**.
6. Old change package `engineering/changes/20260828-fix-trust-ci-human-approval-cli-approval-create-1810a9/**` — workflow evidence for the old route. **Do not merge it as the live package.** This successor already has `20260906-continue-published-2-0-15-to-next-final-stage-su-8e7fea`.

## Overlap with later `main` commits

- **`cli.py` and `trust-ci/README.md` product blobs are unchanged from `1c062998` through `fd51dcf`.** No later main commit implemented lazy imports. Low semantic conflict on those two files.
- **`decisions.md` / `mistakes.md`**: `git merge-tree` against `origin/main` reports **changed in both** (append-at-end). Must **manually append** the two 2026-08-28 notes; do not take PR #12 whole files.
- Main already documents claw / `127.0.0.1:18080` and 2026-08-31 / 2026-09-08 deadline history in a **later, more complete** form than the stale working tree.
- Factory, delivery, pilot, SEO, M4–M9, migrations `001`–`018` landed on main **without** touching this CLI graph. Successor must not revert those trees.
- PR #13 unique work (policy catalog, repository profiles, holdout trusted roots) is **orthogonal** and **security-sensitive**; keep out of this PR.
- PR #28 is docs-sync for published 2.0.15; optional follow-on, not required to land CLI isolation. Base CLI files identically on `fd51dcf`.

## Dirty-tree risks (do **not** carry into successor)

Working tree vs stale HEAD:

| Path | Dirty content | Belongs on successor from `origin/main`? |
|---|---|---|
| `trust-ci/compose.yaml` | `127.0.0.1:8080:8080` → **hardcoded** `127.0.0.1:18080:8080` | **No.** `origin/main` already has `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"` (better). Dirty edit is a stale-branch local port hack. Discard. |
| `decisions.md` (unstaged) | 11 lines: 2026-08-31 stack-on-accepted-heads + 2026-09-15 then 2026-09-08 deadline notes | **No as a copy from this dirty file.** Main already has evolved 2026-08-31/09-08 decisions. Only add the **PR #12 Multi-role CLI** note. |
| Untracked `engineering/changes/202608*` and `20260906-…` | local change packages | Keep only the **active** successor package; do not commit unrelated 202608* packages or `error.log` / bogus `trust-ci/C:\\Users\\…` path. |

Also: local `active-route.json` currently shows a **different** session (`c08804e69b66`, task «верни всё взад») than this package (`8e7fea`). Implementer must re-read the route bound to **this** change package after checkout of a clean `origin/main` branch.

## Blockers / implementation constraints

1. **Checkout is stale.** Implementation must start from **`origin/main` (`fd51dcf`)**, not `7c61e3b`, not merging PR #12 as a GitHub merge.
2. **Do not `git merge origin/fix/human-approval-cli`.** That would try to delete later main product (`delivery/`, `factory/`, `pilot/`, `.agents/skills/seo-landing/`, VERSION 2.0.15, etc.). Two-dot diff vs main is a massive **deletion** of post-2.0.12 product.
3. **Cherry-pick `0f7f508` may conflict only on `decisions.md` and `mistakes.md`.** Safer: apply `cli.py`, new `test_cli.py`, and `trust-ci/README.md` hunks from that commit; append the two learning notes; skip the old 20260828 change package.
4. **Do not merge, deploy, activate M8/M9, or run the design-partner pilot.** Brief forbids it. No human approval private keys, no `.env`.
5. **PR #12 cannot become merge authority.** Old policy check name `@6737355947c2` is not the deployed `@06ecf1c875bc` required on current `main`.
6. **Dirty compose/decisions must be left behind** when creating the new branch (`git switch -c … origin/main` with a clean index). Carrying `compose.yaml` would **regress** main’s env-var port mapping.
7. No GitHub Actions. Local `grok_verify --mode pr` is preflight only.

## Recommended implementation base SHA

**`fd51dcfed6b33f4a8707c0db602328146df17cc9`** (`origin/main`, published product **2.0.15**).

Procedure: new isolated branch from that SHA → port unique `cli.py` lazy imports + `trust-ci/tests/test_cli.py` + operator README + append-only decisions/mistakes → PR against `main` → wait for App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the **exact new head SHA**. Do not reuse PR #12 head `0f7f508`.

Optional later: merge or land PR #28 docs independently; then extract PR #13 as its own security-scoped successor.

## Frozen boundaries (from PR #12, still valid)

No changes to `/approvals`, envelope schema, signing verification, deployed policy, trust store, SQL/migrations, branch protection, GitHub App config, or human private keys.
