# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; it requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- M4 production source is locally complete, but the current repair candidate is the repository tree containing `PROJECT_STATE.json`, not historical source head `4f75558770f2f332b32b4a47fe6afa61fcc524ec` or intermediate verified head `da7ec8d7d40f52663aba1ff59bf03ccf209395b0`. The current tree repairs roadmap/state parity, claim-terminal races, mutation timeouts, role bootstrap and accepted retry-limit persistence through migration `013`; the latest committed repair checkpoint before this tree is `14cbd542803a57370b7e914f8c06bc56380e89a6`. Full verification, five fresh reviews/reports/receipts, PR delivery, a new external exact-SHA Trust CI result and merge remain pending. PR #21's GitGuardian FAILURE metadata is unresolved and is neither inspected nor dismissed; M4 is not delivered or accepted.
- M5 has clean provisional Tasks 1-6 source at `141e51e75b2bb337fa3bb1544639c6c46c287309`; rootless live-host isolation proof and final accepted-M4 restack/reviews remain open. Its provisional `013_execution_plane` migration now conflicts with M4 `013` and must be renumbered with fresh checksum, upgrade and restart evidence after restack. M6 has a clean provisional Task-1 bridge at `3def83eb915ca68e66379269526ffa64822a1104`; its provisional `014_semantic` migration must then move after M5 (at least `015`) with the same evidence refresh, while service/API behavior, recovery, metrics, restack and reviews remain pending.
- M7 clean provisional source `c8b450f494b3d44b580556c6a612b21a3a780368` has synthetic algorithm evidence only. M8 began at `46a6c8eba6b5bd8e4654f3041e52061cdd1a15d6` and has a first source-only Task-1 contract slice at clean provisional head `5735e762b8d7571887f6fa4ac9cf10cd1fad1954`, with Tasks 2-3, a factual profile, a 30-real-task cohort, activation and acceptance absent. M9 remains design-only at `055051e26e26bf08fa85376523ba6632afcca747`, with no product source, real signed input, environment/recovery proof or production authority. Parallel source work is not acceptance; M7 still needs accepted-M6 restack/runtime/real-outcome evidence, and none of M5-M9 is delivered.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.
- The hard deadline is **2026-09-08 00:00 UTC+3**; it does not waive dependency order, signed scopes, the M8 cohort or external exact-SHA authority.

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

1. Treat the repository tree containing `PROJECT_STATE.json` as the current local M4 repair candidate only. The intermediate 14/14 verifier at `da7ec8d7d40f52663aba1ff59bf03ccf209395b0` predates all repair checkpoints; bind a fresh final verifier run, five route-selected reviews, reports and receipts to the final tree.
2. Only after explicit branch/PR authorization may M4 be pushed as a clean successor; it remains undelivered until `adaptive-trust-ci/verified@06ecf1c875bc` succeeds on the exact PR head and protected merge completes. Preserve PR #21's unresolved GitGuardian FAILURE metadata without inspecting or dismissing the finding.
3. Prove M5 rootless live-host isolation and restack/review clean provisional Tasks 1-6 head `141e51e75b2bb337fa3bb1544639c6c46c287309` only after M4 acceptance; renumber provisional `013_execution_plane` to the next free migration and regenerate checksums plus upgrade/restart evidence.
4. After accepted M5, renumber M6 provisional `014_semantic` after M5 (at least `015`), regenerate checksums plus upgrade/restart evidence, and complete service/API behavior, recovery and metrics from Task-1 bridge `3def83eb915ca68e66379269526ffa64822a1104` before restack/review.
5. Restack M7 provisional synthetic source `c8b450f494b3d44b580556c6a612b21a3a780368` only after M6 acceptance; require runtime and real-outcome evidence before any M7 acceptance claim.
6. Continue M8 from provisional Task-1 head `5735e762b8d7571887f6fa4ac9cf10cd1fad1954` without treating synthetic fixtures as a factual trust profile or 30-real-task cohort; Tasks 2-3, activation and acceptance remain gated by accepted M7.
7. Keep M9 design head `055051e26e26bf08fa85376523ba6632afcca747` non-authoritative until source, real signed inputs, an environment, recovery proof and the required human production authority exist.
8. Retain open PRs #12, #13, #15, #17 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; integrate, explicitly supersede or abandon them without silently losing unique work. PR #19 is already delivered and its predecessor staging path is archival.
9. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
