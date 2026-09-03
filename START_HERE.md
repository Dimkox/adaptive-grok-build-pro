# Fresh-agent bootstrap

This file is the zero-context entrypoint for any new agent, human, Codex/Grok/Claude session, or clean clone of this repository. Do not depend on chat history to continue the project.

## Current project state

- Mutable current SHA, PR, Check Run and delivery state are intentionally absent from this prose. Use the [External Observer runbook](engineering/runbooks/external-observer.md) for a coherent exact-subject `PUBLIC_STATUS.v1`; use the [latest release page](https://github.com/Dimkox/adaptive-grok-build-pro/releases/latest) for human discovery.
- `PROJECT_STATE.json` is a historical claim snapshot. Its embedded facts and local receipts remain claims until exact equality and freshness are independently observed.
- External Observer closeout precedes accepted M5; accepted M4 remains M5's delivery predecessor. The hard program deadline is 2026-09-04 23:59 UTC+3, but no schedule promotes provisional source into reviewed, delivered or released status.

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
2. Run the Observer with operator-owned config before reasoning about mutable branches or pull requests; do not copy a returned SHA back into prose as permanent current truth.
3. Inspect `PROJECT_STATE.json` only as typed historical claims. Treat stack integration, protected-main delivery and release as separate stages; do not accept M5 before Observer closeout and accepted M4.
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

Use the typed historical ledger as evidence input and the External Observer as the freshness projection. Branch names, local `ready` files, README prose and GitHub labels do not prove protected-main delivery.

1. Supply one operator-owned exact repository/main/current-PR/check/App configuration outside Git.
2. Run `scripts/grok_observer.py observe`; retain `STALE`, `UNAVAILABLE`, `REFERENCED_NOT_VERIFIED` and `ATTESTATION_UNOBSERVABLE` exactly as emitted.
3. Reconcile each historical claim against the returned exact subject without rewriting this bootstrap file with mutable values.
4. After any head/main/check movement, rerun the Observer and obtain fresh exact-head Trust CI/approval evidence through the independently operated delivery path.
5. Begin accepted M5 only after Observer closeout and accepted M4. Provisional source preparation remains non-acceptance.

## No chat dependency

A new agent must be able to continue from GitHub alone. If a future decision, blocker, milestone handoff, or non-secret operational fact matters to the next agent, commit it to the repository or the active pull request before ending the session. Chat is the lowest-priority source of truth.
