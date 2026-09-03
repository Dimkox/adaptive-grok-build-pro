# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- Stable synthesis is an implementing local candidate under route `c893098ede04`: deterministic typed readiness plus a fixed weekly read-only GitHub review queue for three pinned official sources, covering newest stable releases and bounded post-pin changes/bugfix candidates. It is inert by default, does not advance pins/source, and has no release/external/merge/production authority.
- A separate direct unsandboxed `grok --continue` pilot was observed in `google-ads-automation`; no adaptive-factory process/unit was observed. Do not equate that pilot with M5 broker isolation, and do not let stable synthesis touch it.

- Product source identity is `2.0.13`; its tracked zip is a local candidate only. The most recently published GitHub Release remains `v2.0.12`, and no `v2.0.13` tag or publication is claimed.
- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; it requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- M4 PR #21 at exact `571cad7877431ac5ab5779b53fe9f7effd6859ce` failed the App-owned Trust CI `root-unittest` check because package Git commands discarded configured `safe.directory` under the differently owned UID-10001 runner checkout; GitGuardian separately reports FAILURE with contents not inferred. The local command-scoped fix is source `3b1f9a54a964d91f34cee2628374b17e7a42edeb`; rebuilt candidate `9727bc30c82bb44a86db0ef5b62e507b5527207a` has tree `5feb9a74eda6c54cd37539a2c5dda378a5e27853` and archive SHA-256 `57e6e00a6c5281fda33e1317d955dd5ca0e1a6f9467e60daa256a8919b408bcc`. Local verifier 14/14 at fingerprint `b0a230f6…`, root 537/537 and focused different-owner/package tests pass, but this candidate is unpushed, externally unchecked, unmerged, untagged and unreleased; current docs/package changes require another final verifier/review cycle.
- PRs #12/#13 remain old-epoch `ACTION_REQUIRED`; PR #12's command-local lazy Trust CI CLI imports/regression and PR #13's `PolicyCatalog` repository binding plus fail-closed profile/holdout validation/tests are absent from `main`. PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`; the cause was not inspected or inferred. Its wholesale M1-M3 aggregate and packaging-stage hardening are superseded, while investor demo `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b` remains a unique clean-successor candidate. No successor PR is claimed.
- M5 is a stacked successor program. Successor 04 contract enrollment/comparator is clean and frozen at `27b0ae619cacf0d9ddeed15c60212800ff6009ca` (tree `1a4e3f87da8a12e173a81e66b53f5fc21cb241c6`) on exact predecessor `8a7be8a32132a6e6fb96a5ce730fdb5513c121cd`; exact fitness passes. Successor 05 product/restart checkpoint `3940267ac5754ad07a047894102015d33eb759b1` (tree `4646582a7c5ff6f08ee7e8462687da400459b08d`) on `27b0ae6` contains migrations `014`-`017`, compatible v1 plus additive v2, atomic terminal/recovery source and a self-contained PostgreSQL-17 harness. Its final run executed 273 tests: 272 passed and one fresh-cluster-only test was expectedly skipped in 221.516 seconds, followed by two actual restart/recovery PASS results. Session-level comparator/test/security feedback reported no open P0/P1, but final exact-head verification and checked-in reviews/route receipts remain pending for both successors. Successor 06 holds four inert systemd sources/tests plus installer/configuration/final-doc parity. Every successor must use its immediate predecessor as PR base: cumulative `9727bc3`→`27b0ae6` exceeds the allowed architecture change size and must not be squashed.
- M5 operational activation is **BLOCKED** pending a trusted rootless workspace/snapshot broker and live OS credential/egress isolation. M6-M9 are provisional source only; M6 `2d2360c` has Phase-A-aligned repair-lifecycle source but accepted dependency integration has not begun and its migration must become `018`. M7 `4df2516` remains blocked pending durable lookup and real outcomes. M8 `2cee9b9` remains L2 recommendation-only and still requires at least 30 eligible real human outcomes. M9 `6b42ba6` has Tasks 1-4 source but Task 5 and all operational inputs/authority remain blocked. No M5-M9 PR, external check, acceptance, merge, package, release or live activation is claimed.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.
- At the 2026-09-03 16:00 UTC+3 observation, about 32 hours remain to the superseding whole-program deadline **2026-09-04 23:59 UTC+3**. Stable-synthesis exact-SHA evidence/reviews close in parallel with the M4 final descendant, then accepted M4 → M5 → M6 → M7 → M8 → M9 proceeds in dependency order. Source-complete work is not externally accepted work; the M5 isolation proof, M8 real-human cohort, signed inputs and external exact-SHA gates make the deadline explicitly at risk.

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
2. Preserve frozen M5 successor 04 `27b0ae619cacf0d9ddeed15c60212800ff6009ca` and successor-05 product/restart checkpoint `3940267ac5754ad07a047894102015d33eb759b1` on that exact base; record final exact-head verification/reviews without treating the local restart proof as delivery authority.
3. Put exactly four inert systemd sources/tests plus installer/configuration/final-doc parity in successor 06. Keep all M5 PRs stacked on immediate predecessors; never squash the cumulative M4→M5 diff. Final M5 still needs trusted rootless broker/live OS isolation evidence.
4. Keep M6 repair-lifecycle head `2d2360cd6f2a19ad3328d468073a52927691b112` quarantined until accepted M5. A provisional Phase-A alignment exists, but accepted dependency integration has not begun; renumber migration `014` to `018`, remove temporary adapters, regenerate checksums plus upgrade/restart evidence, and perform exact-head verification/reviews.
5. Restack M7 provisional shadow-bundle source `4df2516fa3a137fa730d08733fb9e338768232fb` only after M6 acceptance; implement durable lookup and require runtime plus real-outcome evidence before any M7 acceptance claim.
6. Continue M8 from provisional head `2cee9b93c161b6c76f4fee877e6d19eacee5a271`, deleting its temporary reader during accepted-M7 restack; at least 30 real eligible human acceptances, profile acceptance and activation remain mandatory.
7. Keep M9 provisional Tasks-1-4 head `6b42ba6d6c1ab02fe5c1c7a2ecfd762014a4d420` non-authoritative until Task 5, accepted predecessors, real signed inputs, an environment, recovery proof and the required human production authority exist.
8. Retain open PRs #12, #13, #15 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; extract unique work through clean successors without claiming those successors exist. PR #17 is a closed exact duplicate of #21, and PR #19 is already delivered with its predecessor staging path archival.
9. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
