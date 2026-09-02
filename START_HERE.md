# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; it requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- M4 production is locally complete at `4f75558770f2f332b32b4a47fe6afa61fcc524ec`, with frozen verification and five PASS reports at source head `460a8a01a6394cac710b4e3f9eea3d94d4beef89`. PR #21 presents that source against `main`: its App-owned check succeeded and its GitGuardian check reports FAILURE metadata, which this integration neither inspects nor dismisses. PR #17 is the older stacked M4 path, not current-main delivery authority. Source `460a8a01` is combined with exact `origin/main` on local `integration/m4-main-20260902`; the new merge tree is an unpushed candidate that still needs fresh verification/reviews, PR delivery, exact-head Trust CI and merge.
- M5 is provisional/finalizing at `64d55d4b11533c1da8aadb0c993b5b35926ac927`; review follow-up and a suitable rootless-isolation host proof remain open, and the branch must restack on accepted M4. M6 is provisional and paused at `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6` until accepted M5. M7-M9 are not started.
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
3. Inspect `PROJECT_STATE.json`, then PRs #10, #11, #17 and #21 plus the named M4/M5/M6 local branches with their exact base/head SHAs before continuing milestone delivery. Treat a merge into another milestone branch or a provisional source branch as integration evidence, not delivery to `main`.
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

1. Finish the local M4 merge candidate whose source parent is `460a8a01a6394cac710b4e3f9eea3d94d4beef89` and current-main parent is `78ad2f679d38dc3244e716c586332417e610089c`; preserve every unique `decisions.md` / `mistakes.md` entry and the K22 README graph.
2. Bind fresh verification and all five route-selected reviews to that exact integrated tree. Only after explicit branch/PR authorization may it be pushed as a clean successor; it remains undelivered until `adaptive-trust-ci/verified@06ecf1c875bc` succeeds on the exact PR head and protected merge completes.
3. Return M5 review repairs to its sole writer, prove the rootless-isolation exit gate, and restack provisional head `64d55d4b11533c1da8aadb0c993b5b35926ac927` on accepted M4 before any M5 acceptance claim.
4. Keep M6 `5c5c37136f20404a927fd2ad7621ad0f7fcae8e6` paused until accepted M5; M7-M9 remain dependency-gated roadmap work, not parallel completion claims.
5. Retain open PRs #12, #13, #15, #17 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; integrate, explicitly supersede or abandon them without silently losing unique work. PR #19 is already delivered and its predecessor staging path is archival.
6. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `milestone/a-plus-autopilot` remains design input, not M8 implementation.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
