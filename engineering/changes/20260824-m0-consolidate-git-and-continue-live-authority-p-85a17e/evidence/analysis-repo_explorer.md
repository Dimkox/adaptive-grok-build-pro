# repo_explorer — actual git + live Trust CI (M0 continuation)

Observed 2026-08-24. No `.env` / PEM / `glider.conf` read. No push/merge/deploy.

## 1. Branches, HEAD, tracking, tag, dirty tree

| Ref | SHA (short) | Tracking |
| --- | --- | --- |
| `HEAD` / `milestone/m0-live-trust-authority` | `1fc942065a124ce75659bd082519d8ebc37774e8` | `origin/milestone/m0-live-trust-authority` **in sync** (same SHA) |
| `main` (local) | `c54fd01588eb343eeecde7302fee514bf3e6090d` | `origin/main`: **behind 207** |
| `origin/main` | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` | tip: `feat: add M1 typed change-spec…` |
| HEAD vs `origin/main` | `git rev-list --left-right --count` → `4 0` | branch is **4 commits ahead** of `origin/main`, 0 behind |

Other local branches (not used for this PR): `docs/dark-factory-roadmap`, `feat/trust-ci-control-plane` (ahead 201 / behind 202 vs its origin), `milestone/m1-typed-intent`, `publish-2012`.

**Tag `v2.0.12` peeling:** annotated tag object `cd5c9d109d1e9c42f71cf4fc187cc15f1f007116`; peeled commit `73e4ae7c68a95d3a7440378964b8cc1879df9b89` (`Merge pull request #2 from Dimkox/feat/trust-ci-control-plane`). Tag SHA ≠ commit SHA.

**Dirty (tracked `M`):**

- `decisions.md` — workflow log
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` — ops plan
- `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8/state.json` — leftover change-package state
- `engineering/runbooks/trust-ci-activation-report.md` — runbook

Diffstat those four: 33 insertions, 13 deletions. **No product/runtime/source under `trust-ci/` code, scripts, VERSION, or compose in the tracked dirty set.**

**Untracked (`??`):** four change-package dirs, including this one `20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e/` plus `20260817-…33e0c2/`, `20260824-the-user-sent-…-3e6166/`, `20260824-user-query-да-user-query-37bf04/`.

## 2. PR #5

- Number: **5**
- URL: https://github.com/Dimkox/adaptive-grok-build-pro/pull/5
- Title: `M0.0: live Trust Authority on host claw (no runtime)`
- State: **OPEN**, **draft** (`isDraft: true`)
- Base: `main` / Head: `milestone/m0-live-trust-authority`
- Head SHA: **`1fc942065a124ce75659bd082519d8ebc37774e8`** (equals local HEAD / origin milestone; **does not include** working-tree dirty files)

Checks on that SHA:

| name | conclusion | status | app | app_id | external_id |
| --- | --- | --- | --- | --- | --- |
| `adaptive-trust-ci/verified@6737355947c2` | **action_required** | completed | `adaptive-trust-ci` | 4694114 | `1b63d10b-90c1-498a-97b8-7b5e0ea76aec` |
| `GitGuardian Security Checks` | **success** | completed | `gitguardian` | 46505 | empty |

Trust CI details URL: `http://127.0.0.1:18080/jobs/1b63d10b-90c1-498a-97b8-7b5e0ea76aec`. Completed 2026-08-24T09:52:05Z.

## 3. Live compose project `adaptive-trust-ci`

Project files: `trust-ci/compose.yaml` plus host overlay (worker).

| service | state | health |
| --- | --- | --- |
| `api` | running ~1h | **healthy**; `127.0.0.1:18080->8080/tcp` |
| `postgres` | running ~1h | **healthy**; 5432 internal |
| `worker` | running ~25m | no health field in compose ps |
| `migrate` | exited 0 ~49m ago | one-shot |
| `runner-loader` | exited 0 ~26m ago | one-shot |

`GET http://127.0.0.1:18080/health/ready` (direct, no HTTP proxy): **200** JSON `status=ready`, `policy_digest=6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5`, `status_context=adaptive-trust-ci/verified`, `active_approval_keys=1`, `status_publisher=worker-github-app`. Server: uvicorn.

**Host `:8080` is SearXNG**, not Trust CI. Container `searxng-instance` maps `127.0.0.1:8080->8080`. Direct GET: 200 HTML generator `searxng/2026.6.11+4dd0bf4`, server granian. Unrelated: `postgres-db`, `backup-postgres`.

Note: default HTTP proxy (tinyproxy) intercepts `127.0.0.1` unless bypassed; probes must be direct.

## 4. Untracked host overlay

`/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` **exists**. Mode **0600** (`-rw-------`, owner pall). Contents not dumped. Service names only: `docker-engine`, `runner-loader`, `worker`. Worker container labels include this overlay path.

## 5. What a commit of the current dirty tree would touch

Tracked modifications only: the four files in §1 (decisions, M0 plan, leftover `state.json` from 20260823 package, activation runbook). That is **docs/workflow paperwork**, not Trust CI product code.

A commit that also `git add`s untracked paths would add **new `engineering/changes/**` packages** (including this M0 consolidate package and three other leftovers). Still paperwork unless those packages later include product diffs.

Current this-package `state.json`: status `draft`, title “M0 consolidate git and continue live authority proof”, route `85a17ed2e935`. Untracked; committing it is leftover/workflow state, not product.

## 6. Is `engineering/changes/**` gitignored?

**No.** `.gitignore` does not mention `engineering/changes`. `git check-ignore` does not match these packages. Many historical packages are **tracked** (`git ls-files` ~732 paths under `engineering/changes/`, plus `.gitkeep`). New session packages show as **untracked**, not ignored.

---

**dirty-tree classification:** no-op paperwork (docs + change-package state). **No product files** in the tracked dirty set.

**current PR SHA vs working tree:** PR/head/origin milestone = `1fc942065a124ce75659bd082519d8ebc37774e8`; working tree is that SHA **plus** uncommitted paperwork/untracked packages. Committing dirty files would move HEAD off the PR SHA.

**live listener status:** Trust CI API **ready** on `127.0.0.1:18080`; policy digest matches check name `@6737355947c2`; worker up; postgres healthy. Check on PR #5 remains **action_required**. Host `:8080` is **SearXNG**, not the Trust CI listener.
