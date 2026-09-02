# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- Product source identity is `2.0.13`; its tracked zip is a local candidate only. The most recently published GitHub Release remains `v2.0.12`, and no `v2.0.13` tag or publication is claimed.
- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; it requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- M4 has completed its local gate at exact head `571cad7877431ac5ab5779b53fe9f7effd6859ce` (tree `9d29f25d3af4fc9f97bbb8b3d4970906b69338fd`): verifier 14/14, fingerprint `2f9b3ec2dd6f73e887bf375a02870dd91b8a322807e9383e6bd171e2113dba1b`, five local reviews/receipts PASS with 0 Critical/Important and two Minor test-review gaps, and tracked `2.0.13` artifact digest `5b29b7e8e439d1409c3f72757199d20de8f6f4c62bd1df972a37d13f615d9d0e`. No external exact-SHA result, protected merge, acceptance, tag, or release follows from that local evidence.
- PRs #12/#13 remain old-epoch `ACTION_REQUIRED`; their unique lazy CLI import/tests and repository-scoped Trust CI profiles are absent from `main`. PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`; the cause was not inspected or inferred. Wholesale M1-M3 merge is superseded, while investor demo `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b` and packaging hardening remain unique. Each needs clean successor extraction, and no successor PR is claimed.
- M5 is split into four bounded successor slices rooted at `571cad7`. This tree is slice 01: checkpoint `9ba284eeeb21b36e8b484c9f25a5f7c8ea8077c1`, tree `177112f6a862d88cb867f92235b30ea6bad890ec`, containing execution contracts/protocol, fixture adapters, proposal/workspace brokers and their architecture ownership. Exact-predecessor fitness and focused architecture/factory checks pass; it has no migration, HTTP execution contract, package, external gate, acceptance, or delivery. Slice 02 will add persistence/API as migration `014`; slice 03 adds security/recovery/systemd; slice 04 closes integration/state. Rootless live-host isolation and trusted live Git snapshot evidence remain blocked final-M5 gates. Later milestones cannot skip accepted dependency order.
- M7 `c8b450f494b3d44b580556c6a612b21a3a780368` remains synthetic-only. M8 provisional head `5499c582d403c6955324b935cbb8799b38257f5f` (tree `ef49d8016d0cff15e0b06d8db4201e22656d7c04`) contains contracts, a pure evaluator and demotion; local checks pass, but accepted-M7 restack, at least 30 real eligible human acceptances, profile acceptance and activation remain absent. M9 is still only source contract `000301796ac19c518ede110b97b9de09dc077cbd`; Tasks 2-4 and production evidence/authority are absent. None of M5-M9 is accepted or delivered.
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

1. Preserve final local M4 `571cad7877431ac5ab5779b53fe9f7effd6859ce` and its exact local evidence. PR #21 exists at historical head `460a8a01` but does not contain this candidate; it remains undelivered until an authorized exact-head PR earns `adaptive-trust-ci/verified@06ecf1c875bc` and a protected merge.
2. Treat M5 slice 01 checkpoint `9ba284eeeb21b36e8b484c9f25a5f7c8ea8077c1` as contracts/adapters/brokers source only. It creates no migration, package, external check, acceptance, or delivery.
3. Continue bounded successors in order: slice 02 persistence/API with migration `014`, slice 03 security/recovery/systemd, then slice 04 final integration/state. Each must pass fitness against its immediate predecessor; final M5 still needs rootless live-host isolation and a trusted live Git snapshot.
4. Keep M6 Task-3 head `f3b2c0d07116686b27feab4b60166e8a7402d672` quarantined until accepted M5; then renumber its provisional migration to `015`, regenerate checksums plus upgrade/restart evidence, restack/review Tasks 1-3, and continue with untouched Task 4.
5. Restack M7 provisional synthetic source `c8b450f494b3d44b580556c6a612b21a3a780368` only after M6 acceptance; require runtime and real-outcome evidence before any M7 acceptance claim.
6. Continue M8 from provisional head `5499c582d403c6955324b935cbb8799b38257f5f` without treating its pure evaluator or synthetic evidence as a factual accepted profile; accepted M7, at least 30 real eligible human acceptances, profile acceptance and activation remain mandatory.
7. Keep M9 source-only Task-1 head `000301796ac19c518ede110b97b9de09dc077cbd` non-authoritative until later tasks, real signed inputs, an environment, recovery proof and the required human production authority exist.
8. Retain open PRs #12, #13, #15 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; extract unique work through clean successors without claiming those successors exist. PR #17 is a closed exact duplicate of #21, and PR #19 is already delivered with its predecessor staging path archival.
9. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
