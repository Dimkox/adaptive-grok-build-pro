# Release review — M0.0 design freeze (draft PR only)

Reviewer: `release_reviewer` (read-only except this report). Write owner: **none** (`write_agent=null`).
Change: `engineering/changes/20260824-user-query-read-agents-md-decisions-md-mistakes-372269`
Route: `3722694830f7` · intent=`review` · risk=`high` · profiles=`base,contracts,integration,infra`
Skills: `/adaptive-delivery`, `release-readiness`, `verification-evidence`, `api-event-change`, `enterprise-integration`, `security-sensitive-change`.

Assigned: go/no-go for a **draft PR of M0.0 only**. M0.0 is design freeze: spec, plan, activation-report template, invariant tests. **No** VERSION bump, tag, GitHub Release, compose-up, merge, or `branch-protect`. Host-activation **intent** is approved; the host is still **unnamed**, so M0.1 stays gated on `migration_or_external_write_approval` plus a hostname. Did not run `grok_review.py`. Did not push.

Fetched: 2026-08-24 (local tree + GitHub PR list). Did not read `.env`, PEMs, pin hex, or credential stores. Did not push, merge, tag, deploy, compose-up, webhook, or protect `main`.

**PASS** for the M0.0 freeze tree. **GO** to open a **draft** PR from `milestone/m0-live-trust-authority` after an explicit commit of the four product files and a fresh delegated grant. **no-go** to merge, mark ready, protect `main`, compose-up, bump identity, or start M0.1.

| Check (assigned) | Result |
| --- | --- |
| M0.0 artifacts only (spec, plan, activation-report template, invariant tests) | **PASS** — four product files present; no runtime mutation |
| Product identity stays 2.0.12; Trust CI stays 2.1.0 | **PASS** — `VERSION`, README H1, CHANGELOG, `trust-ci/pyproject.toml` untouched |
| No tag / GitHub Release / compose-up | **PASS** — none executed; plan M0.0 STOP honored |
| Draft PR of M0.0 (not merge, not protect `main`) | **GO** after grant + explicit add/commit/push of named paths |
| Host unnamed → M0.1 gated | **PASS / no-go M0.1** — activation-report host field `UNKNOWN` |
| Rollback of a docs+test draft | **PASS** — close draft + delete remote branch; `main` unchanged |
| Observability for this slice | **PASS** — local 6 OK + `grok_verify` preflight; live Check Run **absent** and not required |
| Leftover Actions workflow `340420982` | **PASS** as residual — named for M0.3 only; not executed |
| No GitHub Actions added | **PASS** — `.github/workflows` absent; tests assert that |
| This reviewer push/merge/deploy | **no-go** |

## Verdict

| Gate | Result |
| --- | --- |
| Identity surfaces | **PASS.** Working and committed `VERSION` = `2.0.12`. README H1 = `# Adaptive Grok Build Pro v2.0.12`. CHANGELOG top = `## 2.0.12 — 2026-08-23`. Trust CI `pyproject.toml` / `__version__` = `2.1.0`. No identity file in the M0.0 diff. |
| M0.0 freeze vs live M0 | **PASS.** Spec baseline SHA `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` matches `HEAD` and `origin/main`. Live gap remains: `main` unprotected, webhooks empty, 0 Check Runs, App installation ID `UNKNOWN`. This slice does not claim M0 exit. |
| Scope creep | **PASS.** No M1 re-implementation, no `factory/`, no `.github/workflows/**`, no compose bind change, no VERSION bump. |
| Quality gate (preflight) | **PASS** with stale receipt. `grok_verify --mode pr` **pass** at fingerprint `8767069ea5464604bf667c0d5d89dea057b3a7f8bcfb520d96dd65965e387369` (194 tests, coverage 75%). Independently re-ran `python3 -m unittest trust-ci.tests.test_m0_invariants` → **6 OK**. Receipt is already stale vs `last-fingerprint` `be1349a3…` because review reports landed after verify. Local receipts are **not** merge authority. |
| Rollback | **PASS** for draft-PR rollback. Change-package `rollback.md` is an empty template; adequate because M0.0 has no runtime. Live-host rollback remains `engineering/runbooks/trust-ci-rollout.md` and is **out of this slice**. |
| Observability | **PASS** for a docs+characterization PR. Activation-report live fields stay `UNKNOWN` until M0.2/M0.3. No APM, no `/health/ready`, no App-owned check expected. |
| Merge of this branch | **no-go.** Assigned scope is draft PR only. `main` is unprotected; a rebase-merge would skip the still-absent App-owned check. Do not reuse the M1 bootstrap exception. |
| Protect `main` | **no-go.** Spec forbids protection before a live App-owned Check Run. |
| M0.1 host compose | **no-go.** Host unnamed. Laptop `:8080` is SearXNG. |
| Product mutation by this agent | **PASS / empty.** Wrote only this report. |

## 1. Identity and tree

| Surface | Value |
| --- | --- |
| Working `VERSION` | `2.0.12` (unchanged) |
| `HEAD` | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` `milestone/m0-live-trust-authority` |
| `origin/main` | same SHA — branch tracks `origin/main`, **no upstream of its own** |
| Remote `origin/milestone/m0-live-trust-authority` | **absent** (not pushed) |
| Open PRs on `Dimkox/adaptive-grok-build-pro` | **none** (`github__list_pull_requests` state=open → `[]`) |
| Trust CI service | **2.1.0** |
| Activation-report product base SHA | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |

M0.0 product files (untracked, not yet committed):

- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`
- `engineering/runbooks/trust-ci-activation-report.md`
- `trust-ci/tests/test_m0_invariants.py`

Do **not** ship identity, K16, or runtime compose in this PR. Do **not** treat the change package as the product spec (architect ruling).

## 2. Verification

`.grok-stack/runtime/receipts/3722694830f7/verification.json` (fingerprint `8767069e…`, 2026-08-24T08:10:56Z, **stale** after later tool use):

| Check | Status |
| --- | --- |
| git-diff-check | pass |
| secret-scan | pass (0 potential secrets) |
| contract-structure | pass (0 contracts) |
| sql-safety | pass |
| ruff | pass |
| bandit | pass |
| python-unittest | **pass** — Ran **194** tests in 48.140s — OK (`discover -s tests` only) |
| coverage | pass (75%) |
| overall | **pass** |

`grok_verify` does **not** execute `trust-ci/tests`. M0 invariants were run separately here:

```text
python3 -m unittest trust-ci.tests.test_m0_invariants
Ran 6 tests in 0.001s
OK
```

Peer reviews on disk:

| Review | Verdict |
| --- | --- |
| `evidence/code-review.md` | **pass** — M0-only freeze, no secrets, no Actions, no compose/webhook/protect |
| `evidence/test-review.md` | **pass** with residual characterization gaps (PEM header variants, substring API/worker, example holdout) |
| `evidence/security-review.md` | **absent** at write time; `security_reviewer` was started 2026-08-24T08:11:12Z. This GO is contingent on that report not finding a blocker in the four files. |

Writing this report further stale-dates the verification fingerprint. Parent must re-run `grok_verify --mode pr` **after the ship commit**, not treat `8767069e…` as the PR-head receipt.

## 3. Rollback — adequate for a draft docs PR; not a live-host rollback

Change-package `rollback.md` / `release.md` are empty templates. That is **not** a no-go for M0.0 because nothing is deployed, tagged, or bound on `main`.

### M0.0 (this slice)

Trigger: wrong files in the draft, leftover change packages accidentally staged, or a decision to abandon the freeze.

1. Leave the PR **draft**. Do not mark ready. Do not merge.
2. If the branch was pushed: `gh pr close <n> --delete-branch` (or close + delete `origin/milestone/m0-live-trust-authority`).
3. If never pushed: discard or keep the untracked files; `main` stays `48cb973`.
4. Never `git push origin main`. Never force-push `main`. Never delete `v2.0.12`.

Verification after rollback: `git rev-parse origin/main` still `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`; open PR list empty or the M0.0 PR closed; product `VERSION` still `2.0.12`.

### M0.1–M0.3 (out of scope; recorded so they are not improvised)

Authority: [`engineering/runbooks/trust-ci-rollout.md`](../../../../engineering/runbooks/trust-ci-rollout.md) and spec rollout order.

- Host compose rollback: previous reviewed images + holdout + policy; epoch change requires a fresh observed Check Run before re-protecting.
- Early protection lock: kill switch → human admin token removes **only** the exact `adaptive-trust-ci/verified@<epoch>` required check → restore service → prove disposable PR → re-PUT protection with name **and** App ID.
- Never substitute local receipts, delegated grants, GitGuardian, or leftover Actions workflow `340420982`.

Those steps are **no-go now**. Host is unnamed. `main` is still unprotected (protection API 404 at design freeze). There is nothing live to roll back.

## 4. Observability

No production SLI is in play for M0.0. Success/failure for this slice:

| Signal | Expected now | Expected after draft PR |
| --- | --- | --- |
| Product `VERSION` | `2.0.12` | still `2.0.12` |
| Trust CI identity | `2.1.0` | still `2.1.0` |
| Local M0 invariants | 6 OK | 6 OK on the PR tree |
| `grok_verify --mode pr` | pass (preflight) | re-run on committed fingerprint |
| Draft PR | **absent** | open, `draft=true`, head = milestone branch, base = `main` |
| `adaptive-trust-ci/verified@*` | **absent** (correct) | still absent; do not forge |
| `/health/ready` on this laptop | SearXNG, not Trust CI | unchanged; do not compose-up |
| Activation report live fields | `UNKNOWN` | still `UNKNOWN` until M0.2/M0.3 |
| `main` protected | false | false |
| Workflow `340420982` | leftover **active** in Actions catalog | still leftover until M0.3 |

Support visibility after the draft exists is the PR URL plus the spec live-gap table. Trust CI Prometheus/`metrics.py` stay in-tree and **not live**. Filling activation-report IDs is M0.2/M0.3 operator work, not this PR.

Drafts **do** enqueue Trust CI jobs once a webhook exists (`decisions.md` 2026-08-23). That is why keeping this PR draft is compatible with later M0.2 proof; it is not a reason to register a webhook now.

## 5. Remaining risk (do not expand scope)

1. **Draft PR does not exist yet.** Branch has no upstream. Open PRs = none. GO is for creating it, not a claim that it is already open.
2. **Untracked leftovers on disk.** `engineering/changes/20260817-вычисти*` and `engineering/changes/20260824-да-user-query-37bf04/` plus a dirty `20260823-…9d97f8/state.json`. Fail-closed if those names appear in `git diff --cached`. **Never `git add -A`.**
3. **Stale protected-path grant.** `runtime/approvals.json` grant `64619a8caa8216fc` is `protected-path-write` for `trust-ci/tests/test_m0_invariants.py` bound to git HEAD `5a63d1c` (the old `milestone/m1-typed-intent` SHA) and an old fingerprint. Current HEAD is `48cb973`. That grant **cannot** authorize push or `gh pr create`. Need a new exact grant: `git-push-branch` on `milestone/m0-live-trust-authority` and `external-write` `gh pr create` (draft). Wildcard `*` forbidden. First mutation invalidates the grant (`mistakes.md` 2026-08-23).
4. **Verification receipt is stale.** Reviews and this report dirty the tree. Re-verify after the ship commit. Do not record `grok_review.py` receipts (assigned: none).
5. **Security review not on disk.** Stop if `security_reviewer` fails the four files (PEM leak, Actions, runtime mutation). This release review does not substitute that report.
6. **`main` is unprotected.** A later merge of this draft would land without an App-owned check. That is why merge is **no-go** even if the docs look fine. Do not reuse PR #2/#4 bootstrap exceptions.
7. **Host unnamed.** User approved host-activation **intent** only. Activation-report `Dedicated CI host` = `UNKNOWN`. M0.1 compose/webhook/PEM/install-ID lookup stay behind `migration_or_external_write_approval` + a hostname. This laptop is disqualified (SearXNG `:8080`, shared Docker, agent-readable leftover PEM filename).
8. **App installation ID unverified** (gh 401/403). Operator-safe IDs belong in the activation report after M0.1, never next to PEM in git.
9. **Leftover Actions catalog entry `340420982`** (`trusted-ci.yml`, state=active, file absent from git). Disable only in M0.3. Do not revive `.github/workflows/`.
10. **Invariant tests are static characterization**, not live drills. Gaps (PKCS8/EC PEM headers, substring API/worker, example holdout, port 8080 only) are acceptable for M0.0; they do not prove merge authority.
11. **Plan checkboxes** for spec/plan/report/tests are still `[ ]` while files exist. Operator hygiene; not a scope breach. Parent may tick them in a follow-up edit on the same branch.
12. **Change-spec.yaml / release.md / rollback.md** in this package are templates. They are route evidence, not the product spec. Optional to include the change package in the draft; required product set is the four files above.
13. **`grok_verify` 194 tests do not include Trust CI unittest.** Keep the explicit `unittest trust-ci.tests.test_m0_invariants` in the PR evidence comment.
14. **No root packaging markers.** Keep absent. Do not add `pyproject.toml` / `requirements.txt` / `setup.py`.
15. **Coverage 75%** is the product ratchet on `tests/`; it is not Trust CI host coverage.

## 6. GO / NO-GO

| Act | Decision |
| --- | --- |
| Draft PR of M0.0 from `milestone/m0-live-trust-authority` after explicit commit of the four product files | **GO** |
| Include this change package (optional, route evidence) | **GO** if listed explicitly |
| `git add -A` / leftover `20260817-` / `37bf04` / `9d97f8` state.json | **no-go** |
| Mark PR ready / merge / rebase-merge / squash | **no-go** |
| `git push origin main` | **no-go** |
| Protect `main` / `adaptive-trust-ci branch-protect` | **no-go** |
| `docker compose up` on this laptop or any unnamed host | **no-go** |
| VERSION bump / tag `v2.0.13` / GitHub Release | **no-go** |
| Disable leftover workflow `340420982` | **no-go** (M0.3) |
| Register webhook / read PEM / mint JWT / fill App ID in git | **no-go** |
| Start M0.1 / M1 / M2–M9 / `factory/` / GitHub Actions | **no-go** |
| Forge `adaptive-trust-ci/verified@*` | **no-go** |
| Treat local receipts or this report as merge authority | **no-go** |
| This reviewer executing push or `gh pr create` | **no-go** |
| M0.1 after **named** dedicated host + `migration_or_external_write_approval` | **deferred** — not this GO |

Parent sequence (controller/human only; not this agent). Requires a **fresh** delegated grant bound to repository, route, change, current HEAD after commit, tree fingerprint, actions `git-push-branch` + `external-write` (`gh pr create`), resource `milestone/m0-live-trust-authority`, TTL. Commit first, then mint the grant against that SHA.

```bash
# never git add -A. fail-closed if cached names match 20260817|37bf04|9d97f8|pin.env|.pem|trust-ci/runtime|trust-ci/env/[^. ]|.github/workflows
git add \
  docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md \
  docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md \
  engineering/runbooks/trust-ci-activation-report.md \
  trust-ci/tests/test_m0_invariants.py
# optional: git add engineering/changes/20260824-user-query-read-agents-md-decisions-md-mistakes-372269
git commit -m "docs: freeze M0 live Trust Authority design (spec, plan, invariants)"

python3 -m unittest trust-ci.tests.test_m0_invariants
python3 scripts/grok_verify.py --mode pr

# after exact grant:
git push origin milestone/m0-live-trust-authority
gh pr create --draft --base main --head milestone/m0-live-trust-authority \
  --title "M0.0: live Trust Authority design freeze" \
  --body "Design freeze only. Not merge. Not protect main. Not M0.1."
```

Keep the PR draft. Update it with exact-SHA local evidence. Stop.

## What this review is not

- Not merge authority and not a Trust CI Check Run.
- Not a security review (parallel; report not on disk at write time).
- Not `grok_review.py` receipt recording.
- Not host activation, webhook, branch-protect, or leftover-Actions disable.
- Not a VERSION/tag/GitHub Release decision.
- Did not read `.env` or PEM bodies. Did not push, merge, or deploy.

## Stop

**PASS** for M0.0 design freeze.

- Spec, plan, operator-safe activation-report template, and six invariant tests are in the working tree on `milestone/m0-live-trust-authority` @ `48cb973`. Product **2.0.12** / Trust CI **2.1.0** unchanged. Invariants **6 OK**. `grok_verify` previously **pass** (stale after reviews). Rollback of a draft is close+delete. Live authority remains absent by design.
- **GO** to open a **draft** PR of those four files (optional change package) after commit + a fresh push/`gh pr create` grant.
- **no-go:** merge, mark ready, protect `main`, compose-up, VERSION/tag/release, M0.1 on an unnamed host, this laptop as CI host, GitHub Actions, forged App check, `git add -A`, this agent publishing.
