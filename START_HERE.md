# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- M0 (Live Trust Authority) is complete and merged into `main`.
- M0 runtime repair and policy-loop fixes are also merged into `main` through PR #7 and PR #6.
- The independent App-owned merge gate is live as `adaptive-trust-ci/verified@6737355947c2` and protected `main` binds that check to GitHub App ID `4694114`.
- The current source identity is v2.1.0. M1, M2, and M3 plus the investor demo MVP are locally complete source candidates on PR #15, branch `mvp/investor-ready`, targeting `main`.
- PR #15 is open; it is not merged or deployed. No repository prose, local test, receipt, or bundled demo evidence claims that the App-owned Trust CI check passed for its current exact SHA.
- The pre-fix merge head was `3af0e803c8d763f227f0669e3c614806a90fc75b`. This bootstrap correction creates a newer head, so that SHA is context only and cannot be reused as current verification or approval evidence.
- The next action is the App-owned exact-SHA external Trust CI check for the new PR #15 head and all required approvals. Merge and deployment remain human/operator-controlled actions after those gates succeed.

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
3. If continuing the current product candidate, inspect PR #15 and branch `mvp/investor-ready`, then read the v2.1.0 current-state section in `README.md`, the investor demo [design](docs/superpowers/specs/2026-08-30-investor-demo-mvp-design.md), and its [plan](docs/superpowers/plans/2026-08-30-investor-demo-mvp.md) before changing code.
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

## Current candidate handoff

PR #15 contains the locally complete v2.1.0 source candidates for M1 typed intent, M2 executable architecture, M3 controlled knowledge and debt, and the investor demo MVP. Local completion means the implementations and their focused evidence exist in the branch; it is not external merge authority and does not prove that the current PR SHA passed Trust CI.

The next action is delivery verification, not restarting an obsolete early implementation task:

1. use the actual current PR #15 head SHA, not the pre-fix `3af0e803c8d763f227f0669e3c614806a90fc75b` context SHA;
2. require the App-owned `adaptive-trust-ci/verified@6737355947c2` check for that exact SHA;
3. obtain every required human-signed approval scope outside the agent environment;
4. merge or deploy only through the separately authorized human/operator workflow after all gates succeed.

If the PR head moves again, use the branch/PR as source of truth and require fresh exact-SHA evidence rather than copying an older SHA from documentation.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
