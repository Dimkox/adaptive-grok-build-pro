# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- As observed on 2026-09-01 at protected `main` `8ab4e57038dec2e07f01aaa0b207813a387358f4`, the branch strictly requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- M4 is implemented locally, but PR #17 remains open with failed exact-head checks and its local branch is two commits ahead of the published head. Its latest local head therefore has stale review/external evidence.
- M5-M9 are not started. The current work is consolidated delivery reconciliation for M1-M4; do not start M5 merely because a milestone branch exists.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.

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
3. Inspect `PROJECT_STATE.json`, then PRs #10, #11 and #17 with their exact base/head SHAs before continuing milestone delivery. Treat a merge into another milestone branch as stack integration, not delivery to `main`; do not start M5.
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

1. Preserve and deliver the accepted M2+M3 aggregate `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` through a clean current-main integration PR; this also carries the complete M1 source that is absent from `main`.
2. Rebuild M4 as a clean successor from the delivered predecessor stack, using local `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06` only as source evidence. Do not claim PR #17 fixed or accepted: its published head is `8e6504168462bbabad359fec3d23838c87f5ba22` and its exact-head gates failed.
3. Retain open PRs #12, #13, #15 and #17 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; integrate, explicitly supersede or abandon them without silently losing unique work. PR #19 is already delivered and its predecessor staging path is archival.
4. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for any branch made stale by the base change.
5. Begin M5 only after M1-M4 delivery state is reconciled and observable on `origin/main`. `milestone/a-plus-autopilot` is design input, not M8 implementation.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
