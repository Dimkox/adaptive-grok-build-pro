# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- Product source identity is `2.0.13`; its tracked zip is a local candidate only. The most recently published GitHub Release remains `v2.0.12`, and no `v2.0.13` tag or publication is claimed.
- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; it requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- M4 PR #21 at exact `571cad7877431ac5ab5779b53fe9f7effd6859ce` failed the App-owned Trust CI `root-unittest` check because package Git commands discarded configured `safe.directory` under the differently owned UID-10001 runner checkout; GitGuardian separately reports FAILURE with contents not inferred. The local command-scoped fix is source `3b1f9a54a964d91f34cee2628374b17e7a42edeb`; rebuilt candidate `9727bc30c82bb44a86db0ef5b62e507b5527207a` has tree `5feb9a74eda6c54cd37539a2c5dda378a5e27853` and archive SHA-256 `57e6e00a6c5281fda33e1317d955dd5ca0e1a6f9467e60daa256a8919b408bcc`. Local verifier 14/14 at fingerprint `b0a230f6…`, root 537/537 and focused different-owner/package tests pass, but this candidate is unpushed, externally unchecked, unmerged, untagged and unreleased; current docs/package changes require another final verifier/review cycle.
- PRs #12/#13 remain old-epoch `ACTION_REQUIRED`; their unique lazy CLI import/tests and repository-scoped Trust CI profiles are absent from `main`. PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`; the cause was not inspected or inferred. Wholesale M1-M3 merge is superseded, while investor demo `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b` and packaging hardening remain unique. Each needs clean successor extraction, and no successor PR is claimed.
- M5 is now a stacked successor program. Successor 04 contract enrollment/comparator is clean and frozen at `27b0ae619cacf0d9ddeed15c60212800ff6009ca` (tree `1a4e3f87da8a12e173a81e66b53f5fc21cb241c6`) on exact predecessor `8a7be8a32132a6e6fb96a5ce730fdb5513c121cd`; independent comparator/security review and exact fitness pass. Successor 05 runtime/recovery/additive-v2 is in progress on `27b0ae6`, with coherent runtime checkpoint `5073fc05013d1d40c99f22d48db5dd3d4d8c4b87` (tree `54c2d08310b03504528e24331c39a94161ae0136`); migrations `014`-`017`, atomic terminal/recovery source and route-identity-safe v2 projection exist, but the actual M5 restart probe and four inert systemd source units/tests remain open. Successor 06 holds inert systemd/installer/final docs if the bounded budget requires it. Every successor must use its immediate predecessor as PR base: cumulative `9727bc3`→`27b0ae6` exceeds the allowed architecture change size and must not be squashed.
- M5 operational activation is **BLOCKED** pending a trusted rootless workspace/snapshot broker and live OS credential/egress isolation. M6-M9 are provisional source only; M6 must begin with migration `018`, M8 still requires at least 30 eligible real human outcomes, and M9 remains conditional. No M5-M9 PR, external check, acceptance, merge, package, release or live activation is claimed.
- M7 `c8b450f494b3d44b580556c6a612b21a3a780368` remains synthetic-only. M8 provisional head `5499c582d403c6955324b935cbb8799b38257f5f` (tree `ef49d8016d0cff15e0b06d8db4201e22656d7c04`) contains contracts, a pure evaluator and demotion; local checks pass, but accepted-M7 restack, at least 30 real eligible human acceptances, profile acceptance and activation remain absent. M9 is still only source contract `000301796ac19c518ede110b97b9de09dc077cbd`; Tasks 2-4 and production evidence/authority are absent. None of M5-M9 is accepted or delivered.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.
- At the 2026-09-03 11:41 UTC+3 observation, about 108 hours remain to the hard deadline **2026-09-08 00:00 UTC+3**. The pending M4 external rerun has compressed the old M5 window; no document claims the remaining dependency, isolation, cohort or external gates automatically fit.

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

1. Preserve local M4 candidate `9727bc30c82bb44a86db0ef5b62e507b5527207a` and its exact historical local evidence. Bring documentation/package parity into a final descendant, rebuild the package if its filtered inventory changes, and rerun exact-head verification and reviews. PR #21 currently contains failed head `571cad7`; only that verified descendant may later receive a separately authorized PR update, fresh App-owned exact-head success and protected merge.
2. Preserve frozen M5 successor 04 `27b0ae619cacf0d9ddeed15c60212800ff6009ca`; finish successor 05 on that exact base, including the actual PostgreSQL restart proof, without treating worktree state as a final SHA.
3. Put inert systemd/installer/final-doc source in successor 06 when needed for the bounded change budget. Keep all M5 PRs stacked on immediate predecessors; never squash the cumulative M4→M5 diff. Final M5 still needs trusted rootless broker/live OS isolation evidence.
4. Keep M6 Task-3 head `f3b2c0d07116686b27feab4b60166e8a7402d672` quarantined until accepted M5; then renumber its first provisional migration to `018`, regenerate checksums plus upgrade/restart evidence, restack/review Tasks 1-3, and continue with untouched Task 4.
5. Restack M7 provisional synthetic source `c8b450f494b3d44b580556c6a612b21a3a780368` only after M6 acceptance; require runtime and real-outcome evidence before any M7 acceptance claim.
6. Continue M8 from provisional head `5499c582d403c6955324b935cbb8799b38257f5f` without treating its pure evaluator or synthetic evidence as a factual accepted profile; accepted M7, at least 30 real eligible human acceptances, profile acceptance and activation remain mandatory.
7. Keep M9 source-only Task-1 head `000301796ac19c518ede110b97b9de09dc077cbd` non-authoritative until later tasks, real signed inputs, an environment, recovery proof and the required human production authority exist.
8. Retain open PRs #12, #13, #15 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; extract unique work through clean successors without claiming those successors exist. PR #17 is a closed exact duplicate of #21, and PR #19 is already delivered with its predecessor staging path archival.
9. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
