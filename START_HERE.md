# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- Product source identity is `2.0.13`; validate the tracked ZIP/sidecar against exact source HEAD and rebuild an artifact-only child only if parity fails. The most recently published GitHub Release remains `v2.0.12`, and no `v2.0.13` tag or publication is claimed.
- M0 (Live Trust Authority) is delivered to `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The current integration base is protected `origin/main` `78ad2f679d38dc3244e716c586332417e610089c`; it requires `adaptive-trust-ci/verified@06ecf1c875bc` from GitHub App ID `4694114` on the exact up-to-date pull-request head.
- M1 is implemented/reviewed in the accepted stack, but only its early slice and design/plan are on `main`; complete M1 delivery is partial. M2 and M3 are implemented/reviewed and merged into predecessor milestone branches by PRs #10 and #11, not delivered to `main`.
- The local source line integrates M4 durable control (`67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4`), M5 bounded execution (`85cd4343143915ce9342634e7fe81886b6394871`), M6 semantic validation (`c6d48ffd8594b3baab1a575021452ea5dfa2a98b`), M7 shadow handoff (`00e0e4f9a6f50844bf9e0ffc7139d3283dda889f`), corrected M8 earned-autonomy evaluation (`a937ac8d200a4e143c295fabd482b19bc8cc4286`), and M9 staged-delivery code (`64b10689ce78a0464a494440f3fa981e18789687`) combined in the current candidate tree. Migrations `001`-`018` are preserved. Execution and delivery remain disabled by default, and no operational provider, persistence, network, systemd, merge, or production authority is present.
- PRs #12/#13 remain old-epoch `ACTION_REQUIRED`; their unique lazy CLI import/tests and repository-scoped Trust CI profiles are absent from `main`. PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`; the cause was not inspected or inferred. Wholesale M1-M3 merge is superseded, while investor demo `9dcdf5880b619f29c01dbe76e0f598ff1fad9f9b` and packaging hardening remain unique. Each needs clean successor extraction, and no successor PR is claimed.
- PR #22 is open for the current M9 integration branch at the stable code checkpoint; it is not merged or delivered. M8 still lacks the required factual 30-task human-accepted cohort and activation. M9 still lacks real signed input, an operational environment, exercised recovery proof, and production authority.
- PR #19 delivered the optional SEO side project to `main` as `8ab4e57038dec2e07f01aaa0b207813a387358f4`; it is non-milestone work and is no longer an open continuation item.
- Current work finalizes truthful tracked M9/2.0.13 source, then rebuilds the artifact and binds one exact-head verifier plus all five selected reviews. Local source integration does not waive App-owned Trust CI, protected merge, factual autonomy evidence, signed delivery inputs, or human production authority.

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

1. Treat the exact local M4-M9 lineage named above as integrated source, not external acceptance or production delivery.
2. Treat the corrected M8 checkpoint `a937ac8d200a4e143c295fabd482b19bc8cc4286` as the exact M9 predecessor; it restores the frozen M4 control contract and separates the additive M6 semantic API without changing migrations `001`-`018`.
3. Rebuild the tracked `2.0.13` ZIP and sidecar from the exact clean M9 source in isolated private clones, then bind one exact-head verifier and all five route-selected reviews to the final artifact commit.
4. Keep PR #22 open/unmerged until the exact-head App-owned Trust CI and all required approval scopes succeed; local receipts do not supply merge authority.
5. Do not describe M8 as active until the exact-profile factual cohort and activation record exist, and do not describe M9 as operational until signed inputs, an environment, exercised recovery and human production authority exist.
8. Retain open PRs #12, #13, #15 and #21 plus the unresolved PR #14/local work identified in `PROJECT_STATE.json`; extract unique work through clean successors without claiming those successors exist. PR #17 is a closed exact duplicate of #21, and PR #19 is already delivered with its predecessor staging path archival.
9. After every protected-main merge, fetch remote refs, update the one state model, and obtain fresh exact-head verification/approvals for every branch made stale by the base change. `origin/milestone/a-plus-autopilot` remains design input, not the current M8 source branch.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
