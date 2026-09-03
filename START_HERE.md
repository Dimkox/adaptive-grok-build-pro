# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- Product source identity is `2.0.13`; its tracked ZIP is a stale local artifact, not the current candidate, and must be rebuilt from the clean source/docs freeze. The most recently published GitHub Release remains `v2.0.12`, and no `v2.0.13` tag or publication is claimed.
- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; it requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- M4 production/documentation source is frozen as a local candidate through the data/identity/history/transition/API repair: checksum migrations `001`-`013`, isolated PostgreSQL task/run/attempt/event truth, bounded reconciliation/accounting quarantine, separate complete-intent/semantic-work/transport identities, immutable bounded history, fenced phases, authenticated UDS API/CLI/admin and a sole checked closed-inline 17-operation HTTP contract all exist. At this source/docs freeze the previously tracked `2.0.13` ZIP/sidecar are stale; the immediately following artifact-only commit rebuilds them directly from this clean HEAD. Release-state baseline `56e12b2b394436ee227c66d78b1caba8f7317c78` passed 14/14 local verifier gates, but that receipt predates the current repairs and does not transfer. Exact-head verification and route-selected reviews are receipt-bound gates that must run on the final artifact commit before PR delivery. PR delivery, a new external exact-SHA Trust CI result and merge remain absent. PR #17 closed at `2026-09-02T10:08:38Z` as an exact duplicate of open PR #21 at source head `460a8a01`; PR #21's GitGuardian FAILURE metadata remains unresolved and is neither inspected nor dismissed. M4 is not delivered or accepted.
- PRs #12/#13 remain old-epoch `ACTION_REQUIRED`; their unique lazy CLI import/tests and repository-scoped Trust CI profiles are absent from `main`. PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`; the cause was not inspected or inferred. Wholesale M1-M3 merge is superseded, while investor demo `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b` and packaging hardening remain unique. Each needs clean successor extraction, and no successor PR is claimed.
- M5 source status and accepted dependency status are separate: clean provisional Tasks 1-6 source exists at `141e51e75b2bb337fa3bb1544639c6c46c287309`, while acceptance remains blocked on accepted M4, rootless live-host isolation and restack/reviews. M6 Task 3 is provisional at `f3b2c0d07116686b27feab4b60166e8a7402d672`, persisting deterministic semantic verdicts on Task-2 migration/publish/read source. Task-3 evidence is focused 67/67, legacy 40/40, dedicated PostgreSQL 17 1/1 and architecture PASS; it is quarantined until accepted-M5 restack/renumbering, and Task 4 is untouched.
- M7 `c8b450f494b3d44b580556c6a612b21a3a780368` remains synthetic-only. M8 Task 1 is `5735e762b8d7571887f6fa4ac9cf10cd1fad1954`; Tasks 2-3 and factual cohort/activation gates remain absent. M9 Task 1 is source-only at `000301796ac19c518ede110b97b9de09dc077cbd`, without real signed input, environment/recovery proof or production authority. None of M5-M9 is accepted or delivered.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.
- The current 2026-09-03 work is M4's local-ready target. T0 is still unknown and means the recorded external acceptance of an exact M4 SHA after a separately authorized PR, App-owned exact-SHA Trust CI, required signed scopes and protected merge; M5-M7 then advance only after predecessor acceptance, M8 remains calendar-indeterminate until its >=30-human-accepted-task cohort exists, and M9 requires accepted M8 plus signed artifact/environment/recovery evidence. The former **2026-09-08 00:00 UTC+3** date is a superseded, unachievable historical target and never a waiver.

Machine-readable handoff: [`PROJECT_STATE.json`](PROJECT_STATE.json).

## Bootstrap from a clean clone

1. Start on the default branch and read, in order:
   - `START_HERE.md`
   - `PROJECT_STATE.json`
   - `AGENTS.md`
   - `decisions.md`
   - `mistakes.md`
   - `DARK_FACTORY_ROADMAP.md`
   - `README.md`
2. Run `git fetch --all --prune` before reasoning about active branches or pull requests.
3. Inspect `PROJECT_STATE.json`, then PRs #10, #11, #17 and #21 plus the named M4-M9 local branches with their exact base/head SHAs before continuing milestone delivery. Treat a merge into another milestone branch or a provisional source branch as integration evidence, not delivery to `main`.
4. If starting a different software-development task, create/resolve the local route first. `.grok-stack/runtime/active-route.json` is runtime state and may legitimately be absent in a fresh clone; do not fabricate it.
5. Follow `AGENTS.md`: one write owner, route-selected analysis/review agents, local verification as evidence, pull-request-only delivery, and external Trust CI as merge authority.
6. Never add GitHub Actions.
7. Never bypass the exact-SHA App-owned Trust CI check.

## What is intentionally not in Git

A clean clone contains all source, contracts, roadmap, durable change artifacts, runbooks, public operational facts, and agent handoff needed to understand and continue development. It intentionally does **not** contain secrets or machine-local runtime material, including:

- `.env` files and credentials;
- GitHub App private keys;
- human approval private keys;
- Trust CI signing keys or trust-store private material;
- PostgreSQL runtime state;
- temporary approvals/receipts under runtime directories;
- host-local Docker/socket overlays and other machine-specific deployment scratch.

Do not try to reconstruct missing secrets from repository history or chat. Public/operator-safe deployment facts belong in `engineering/runbooks/`; secrets remain outside Git.

## Live Trust CI orientation

The source and runbooks for the independent merge authority are under `trust-ci/` and `engineering/runbooks/`. The live CI host is `claw`; its public inbound GitHub App webhook reaches the service through the documented Tailscale Funnel, while the API listener itself is loopback-bound on the host. These are operator-safe facts only; credentials are not repository content.

Before changing Trust CI behavior, read the current deployed-policy/holdout constraints in `AGENTS.md` and the activation/rollout runbooks. Repository code cannot itself alter deployed trust material.

## Current milestone delivery handoff

Use one repository-level delivery ledger and one consolidated continuation route. Existing branches are evidence and integration inputs; their names, local `ready` files and GitHub `MERGED` labels do not prove protected-main delivery.

1. Treat the frozen source/docs commit and its immediately following artifact-only `2.0.13` rebuild as the current local M4 candidate only. Baseline `56e12b2b394436ee227c66d78b1caba8f7317c78` has a 14/14 local verifier receipt, but the current repair supersedes that fingerprint; bind a fresh verifier run and all route-selected review reports/receipts to the final artifact commit.
2. Only after explicit branch/PR authorization may M4 be pushed as a clean successor; it remains undelivered until `adaptive-trust-ci/verified@06ecf1c875bc` succeeds on the exact PR head and protected merge completes. Preserve PR #21's unresolved GitGuardian FAILURE metadata without inspecting or dismissing the finding.
3. Prove M5 rootless live-host isolation and restack/review clean provisional Tasks 1-6 head `141e51e75b2bb337fa3bb1544639c6c46c287309` only after M4 acceptance; renumber provisional `013_execution_plane` to the next free migration and regenerate checksums plus upgrade/restart evidence.
4. Keep M6 Task-3 head `f3b2c0d07116686b27feab4b60166e8a7402d672` quarantined until accepted M5; then renumber provisional migration `014` after M5, regenerate checksums plus upgrade/restart evidence, restack/review Tasks 1-3, and continue with untouched Task 4.
5. Restack M7 provisional synthetic source `c8b450f494b3d44b580556c6a612b21a3a780368` only after M6 acceptance; require runtime and real-outcome evidence before any M7 acceptance claim.
6. Continue M8 from provisional Task-1 head `5735e762b8d7571887f6fa4ac9cf10cd1fad1954` without treating synthetic fixtures as a factual trust profile or 30-real-task cohort; Tasks 2-3, activation and acceptance remain gated by accepted M7.
7. Keep M9 source-only Task-1 head `000301796ac19c518ede110b97b9de09dc077cbd` non-authoritative until later tasks, real signed inputs, an environment, recovery proof and the required human production authority exist.
8. Retain open PRs #12, #13, #15 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; extract unique work through clean successors without claiming those successors exist. PR #17 is a closed exact duplicate of #21, and PR #19 is already delivered with its predecessor staging path archival.
9. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
