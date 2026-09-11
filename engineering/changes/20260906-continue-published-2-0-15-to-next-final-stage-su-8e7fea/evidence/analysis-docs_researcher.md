# Docs research — continuation after published v2.0.15

Read-only recovery from `origin/main`, `origin/docs/v2.0.15-published-handoff`, GitHub PR facts, and this worktree. No APIs invented. This checkout is **not** the published tree.

## Exact published identity

Authoritative machine ledger: `origin/docs/v2.0.15-published-handoff:PROJECT_STATE.json` (`observed_at` `2026-09-05T20:17:20Z`).

| Fact | Value | Source |
| --- | --- | --- |
| Product version | **2.0.15** | `VERSION`, README H1 on origin/main and handoff |
| Latest published release | **v2.0.15** | `PROJECT_STATE.json` `latest_published_release` / `published_release.tag` |
| Tag target / protected merge | `fd51dcfed6b33f4a8707c0db602328146df17cc9` | tag `v2.0.15`, `origin/main`, PR #27 merge |
| PR #27 checked head | `9fcc9d943c74260c02a920a59490143f91cb38b2` | START_HERE / PROJECT_STATE |
| Checked tree (PR #27 / merge) | `f01e9b0d1f80fb6731c68079540fd98e5c1f64ac` | START_HERE, PROJECT_STATE |
| Merged at | `2026-09-05T20:14:37Z` | PROJECT_STATE |
| GitHub Release published | `2026-09-05T20:17:20Z` | START_HERE, CHANGELOG |
| ZIP | `packages/adaptive-grok-build-pro-v2.0.15.zip` SHA-256 `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7` | PROJECT_STATE, CHANGELOG, START_HERE |
| Sidecar SHA-256 | `8f3ed4b8eb96f7984eb38b0c988bd8a8cee8cdc789bca52527084b78fd791c6d` | PROJECT_STATE |
| Trust CI | `adaptive-trust-ci/verified@06ecf1c875bc` SUCCESS, check `101365945968`, attestation `4a13e71c-25e7-4272-80fa-8153590edc84`, signer `0519cf1d47436f2e`, App ID `4694114` | PROJECT_STATE `trust_ci` / `published_release.trust_ci` |
| Policy digest | `06ecf1c875bc12fa696956998983e04b102f28571a586bc3bb7a2fff5083fdb2` | PROJECT_STATE |
| GitGuardian on #27 | `SKIPPED` (operator false-positive on public CSP fixture digest, incident `36975026`) | PROJECT_STATE, CHANGELOG |
| Pilot route | `0ce2d62a018e` on `feature/design-partner-pilot` | START_HERE, README, PROJECT_STATE `active_delivery` |
| `current_unreleased_change` | **null** | PROJECT_STATE |

Immutable prior tags (do not restack):

- **v2.0.14**: PR #24 head `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57`, merge `1751b5855e46782b9a1bfceb6e1ab0102cba03b0`, tree `618df086920c92179aa0e22a8c8d4ad30ebd9230`, ZIP SHA-256 `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`, published `2026-09-04T16:58:48Z`.
- **v2.0.13**: PR #22 head `b5eba759c309a92f92f4d4003d025795c7f8a1f9`, merge `8599d45f4f28285381b05a53feb3059de92eb2a8`, tree `03e122a30fb2dbb59907f4c4c28e17f93cbf0751`, ZIP SHA-256 `3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c`.

Trust CI **service** identity remains **2.1.0**, not product 2.0.15 (`AGENTS.md` / README / PROJECT_STATE).

## What “final stage” can and cannot mean

From `START_HERE.md` (handoff), `DARK_FACTORY_ROADMAP.md` §§3–7.1, CHANGELOG 2.0.15, `engineering/runbooks/design-partner-pilot-v2.0.15.md`, AGENTS.md.

**Can mean (repository product already done):**

- M0–M9 **source** is on `main` via PR #22 (`v2.0.13`); L5 dogfood via PR #24 (`v2.0.14`); disabled-by-default `pilot/` via PR #27 (`v2.0.15`).
- Fresh-agent bootstrap, PR-only delivery, App-owned exact-SHA merge gate.
- Next **repository** work is unique-scope successors for stale PRs (first: #12 lazy CLI), then docs PR #28 merge **by a human after** the App check, then optional later #13/#15 successors.
- Pilot **capability** at pre-pilot Stage 3/5: CLI default-off; no live issue-to-PR demonstration.

**Cannot mean:**

- Merge, tag, GitHub Release, deploy, production mutation, or operational activation of M8/M9/pilot from this agent session (no named delegated grant in this change package; AGENTS.md forbids it).
- M8 “earned autonomy” / auto-merge: still needs an **exact-profile factual cohort of ≥30 human-accepted tasks** plus explicit activation; currently capped at L2 (`DARK_FACTORY_ROADMAP.md` gap table and §7.1).
- M9 operational: needs real signed input, environment/provider deployment, exercised recovery, human production authority; source is sealed/in-memory only.
- First live Codex landing attempt: blocked until trusted **landing profile refresh** for observed `80d6215` (see blockers).
- Wholesale merge of stale PRs #12/#13/#15 or reopening superseded #21.
- GitHub Actions, reading `.env`/keys, mutating deployed Trust CI policy/holdout/images/Postgres/signing keys/App/branch protection.

User phrasing “до финальной стадии” is **not** a grant to merge PR #28, run `--live` pilot, or activate M8/M9. Change package title and `requirements.md` already constrain: leave stale path-aware branch, sync to `origin/main`, extract PR #12 as first unique remaining work; do not merge/deploy/activate.

## Remaining unique PR work

Inventory: `engineering/runbooks/20260905-open-pr-reconciliation.md` and `PROJECT_STATE.json` `work_inventory.open_pull_requests` (handoff). No old PR closed/merged during that audit.

1. **PR #12** `fix/human-approval-cli` head `0f7f508945ccce7dc4f1bffc463247633e9e8f58` — unique: lazy/command-local imports in `trust-ci/src/adaptive_trust_ci/cli.py`, operator docs, `trust-ci/tests/test_cli.py`. Still eagerly imports server/API/worker/DB. **First small successor.** Old-epoch `ACTION_REQUIRED`. Do not read/create human approval keys.
2. **PR #13** `feat/trust-ci-repository-profiles` head `f2fd8a7a00a731fbb7acb90e3c7c7881568c8d80` — unique: `PolicyCatalog`, repo-specific holdout/policy-digest binding. Security-sensitive separate successor; **deployed-policy epoch is separately authorized**; repo source cannot grant it.
3. **PR #15** `mvp/investor-ready` head `165d5dd90a2fc2831a3b85be2562a2bb241c8b14` — unique: loopback investor dashboard (`demo.py`, `demo_http.py`, `.grok-stack/demo/`, `scripts/grok_demo.py`). Current-epoch Trust CI `FAILURE` at `root-unittest` (exit 1), GitGuardian SUCCESS; no method diagnostic. Do not cherry-pick old fingerprint or restore obsolete writable-staging packaging workaround.
4. **PR #14** closed unique production-promotion work — re-evaluate explicitly (`retained_unresolved`).
5. Local-only `feature/workflow-artifact-adapters` `dccaeec2…` — compare before cleanup.
6. `origin/milestone/a-plus-autopilot` `90a5da29…` — design-only; **not** M8 implementation.

**PR #28** (not in that 2026-09-05 inventory because it *is* the handoff): `docs/v2.0.15-published-handoff`, title “docs: synchronize published v2.0.15 and preserve remaining PR work”. Head **`ef7c8faeb5d339c5b4343de61162ea611c130c4d`**, base `main`=`fd51dcf…`, **open, not merged** (`merged=false`, `mergeable_state=clean` as of GitHub read). Two commits: `1a9d809` docs record + `ef7c8fa` align published release structure assertion. GitHub check runs on that head: `adaptive-trust-ci/verified@06ecf1c875bc` **SUCCESS** (`101385984851`), GitGuardian **SUCCESS** (`101385980981`). `mistakes.md` records that an earlier PR #28 App check failed `root-unittest` because `StructureTests.test_version_identity_matches_readme` still pinned unpublished changelog/roadmap wording; the `ef7c8fa` repair exists so agents must **not** treat the failed first check as current. Merge of #28 is a **human** protected-main action after the App check; this route must not merge it.

## Named blockers

| Blocker | Exact fact | Source |
| --- | --- | --- |
| Landing profile `80d6215` | Frozen pilot base is `Dimkox/ai-dark-factory-landing@699010380f4f90a0193a9c22090c35e6aded7d2c` (tree `f7dbbd80…`). Observed landing `main` at `2026-09-05T17:17Z`: **`80d621545938e24c296420d7f685f2d0b2b5785e`**, tree `a1c2eff37ec808a53b2aeec089a5f6d7cb72bd55`. SHA-only substitution is forbidden; refresh must preserve analytics/privacy and source-to-deployment-archive checks. No model turn consumed. | `engineering/runbooks/design-partner-pilot-v2.0.15.md`, START_HERE, CHANGELOG, PROJECT_STATE `next_action` |
| M8 cohort | Exact-profile **≥30** human-accepted tasks + activation record; currently inactive, L2 cap; checkpoint `a937ac8d200a4e143c295fabd482b19bc8cc4286` | ROADMAP §7.1, PROJECT_STATE M8 notes |
| M9 operational | Signed input, operational env/provider, exercised recovery, human production authority absent; source checkpoint `64b10689ce78a0464a494440f3fa981e18789687` | ROADMAP, PROJECT_STATE M9 |
| Merge of PR #28 | Open docs successor; App check now SUCCESS on `ef7c8fa`; **not merged**. Agents cannot merge. `origin/main` still carries **unpublished** wording in START_HERE/README/CHANGELOG while tag `v2.0.15` exists. | GitHub PR #28, `origin/main:START_HERE.md` vs handoff START_HERE |
| Stale PRs #12/#13/#15 | Unique work absent from main; old-epoch ACTION_REQUIRED or current-epoch FAILURE; extract successors, do not merge stale heads | runbook 20260905-open-pr-reconciliation.md |
| Pilot GitHub merge gate on landing | Landing repo has no App-owned Trust CI; proposal honest result is `merge_gate_unavailable` / `merge_eligible=false` | pilot runbook |

## Rules that forbid merge / deploy / key access

From `AGENTS.md` (handoff and local contract, same substance):

- Direct push to protected `main` prohibited; merge only after App-owned `adaptive-trust-ci/verified@<policy-sha12>` on **exact** PR SHA plus required signed scopes.
- Local receipts, change packages, `grok_approve.py` grants are **not** merge authority and never substitute Trust CI or human Ed25519 security approvals.
- Never generate/read/request/submit/simulate human approval private keys; never read `.env`, GitHub App keys, CI signing keys, approval keys, production dumps.
- Never GitHub Actions; never edit deployed Trust CI policy/holdout/images/Postgres/trust stores/branch protection.
- No production writes (1C, Bitrix24, SAP, ERP, WMS, payment, infra) without exact delegated operation.
- Pilot runbook: CLI grants **no** permission to invoke Codex, push, open PR, merge, release, deploy, or read credentials; `--live` is a separate operator command with finite grants; wildcard grants fail closed.

This change package `requirements.md` restates: do not merge, deploy, or activate M8/M9/pilot.

## Contradiction: this stale checkout vs published state

| Axis | This worktree | Published / origin |
| --- | --- | --- |
| Branch | `fix/path-aware-shell-policy-circuit-breaker` at `7c61e3b647924e5667d171d8b286e5d79b8a4efe` (behind origin/fix by 2) | `origin/main` = `fd51dcf…` = tag `v2.0.15` |
| `VERSION` | **2.0.12** | **2.0.15** |
| `START_HERE.md` | **absent** | Present on origin/main (still says 2.0.15 **unreleased**, latest published **v2.0.14**) and corrected on handoff (says **published** v2.0.15) |
| Dirty / untracked | Local `decisions.md`, `trust-ci/compose.yaml` modified; many untracked change packages | Not part of published identity |
| Route vs package | Runtime `active-route.json` currently `c08804e69b66` / task “нет, верни всё взад…” | Assigned package route `8e7fea3efac6` |
| `origin/main` docs vs tag | `origin/main:START_HERE.md` / README Current state / CHANGELOG **2.0.15 — unreleased** still describe unpublished candidate + ZIP child `A` | Tag and GitHub Release exist; handoff branch + PR #28 are the documentation successor |

**Do not continue from this 2.0.12 path-aware tree.** Sync reasoning to `origin/main` (`fd51dcf`) for product source; use `origin/docs/v2.0.15-published-handoff` (`ef7c8fa`) for post-publication documentation facts. Extract PR #12 unique scope onto a **new** branch from current `main` after fetch; do not rebase stale #12 onto main in-place as merge authority.

## Continuation facts for the next write owner

1. Leave this path-aware checkout; work from published `main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`.
2. Treat PR #28 as **docs-only successor already App-green**, merge-blocked for agents.
3. First unique product successor: **lazy Trust CI CLI imports** from PR #12, tests without touching approval keys.
4. Do not run live pilot; landing `80d6215` profile refresh is a separately authorized, separately reviewed change against `Dimkox/ai-dark-factory-landing`.
5. Do not claim M8/M9 operational completion; repository delivery ≠ activation.

## Sources (paths)

- `origin/main:VERSION`, `START_HERE.md`, `README.md`, `CHANGELOG.md`, `PROJECT_STATE.json` (partially stale vs publication)
- `origin/docs/v2.0.15-published-handoff:` same files (authoritative post-publication wording) plus `AGENTS.md`, `DARK_FACTORY_ROADMAP.md`, `decisions.md`, `mistakes.md`
- `engineering/runbooks/20260905-open-pr-reconciliation.md`
- `engineering/runbooks/design-partner-pilot-v2.0.15.md`
- GitHub `Dimkox/adaptive-grok-build-pro` PRs #12, #13, #15, #28
- Local: `VERSION` 2.0.12, missing `START_HERE.md`, `engineering/changes/20260906-continue-published-2-0-15-to-next-final-stage-su-8e7fea/{brief,requirements,route}.md|json`
