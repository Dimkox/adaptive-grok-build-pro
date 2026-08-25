# <user_query>
Read AGENTS.md, decisions.md, mistakes.md, README.md, trust-ci/README.md,
engineering/runbooks/trust-ci-rollout.md, and DARK_FACTORY_ROADMAP.md.

Treat main as the product source of truth and DARK_FACTORY_ROADMAP.md as the
program backlog. Do not add GitHub Actions. Do not implement multiple milestones
in one branch. Start with M0 only.

First inspect the current repository and live GitHub state. Verify what parts of
M0 are already operational, especially the adaptive-trust-ci App installation,
installation ID, live Check Runs, deployed worker, webhook deliveries, and main
branch protection. Never print or commit private keys or secrets.

Create milestone/m0-live-trust-authority from the current main. Write or update
the M0 design spec and implementation plan before changing runtime behavior.
Use TDD and real integration drills. Keep reasoning low for ordinary workers and
high only for task analysis, architecture, security, release, and adjudication.
Open a draft PR early and update it with exact-SHA evidence. Stop at M0 exit
criteria; do not begin M1 in the same branch.

</user_query>

Change ID: `20260824-user-query-read-agents-md-decisions-md-mistakes-372269`
Created: 2026-08-24T07:52:00+00:00
Risk: high
Complexity: high-risk
Domains: security, infra, api, integration

## Problem

<user_query>
Read AGENTS.md, decisions.md, mistakes.md, README.md, trust-ci/README.md,
engineering/runbooks/trust-ci-rollout.md, and DARK_FACTORY_ROADMAP.md.

Treat main as the product source of truth and DARK_FACTORY_ROADMAP.md as the
program backlog. Do not add GitHub Actions. Do not implement multiple milestones
in one branch. Start with M0 only.

First inspect the current repository and live GitHub state. Verify what parts of
M0 are already operational, especially the adaptive-trust-ci App installation,
installation ID, live Check Runs, deployed worker, webhook deliveries, and main
branch protection. Never print or commit private keys or secrets.

Create milestone/m0-live-trust-authority from the current main. Write or update
the M0 design spec and implementation plan before changing runtime behavior.
Use TDD and real integration drills. Keep reasoning low for ordinary workers and
high only for task analysis, architecture, security, release, and adjudication.
Open a draft PR early and update it with exact-SHA evidence. Stop at M0 exit
criteria; do not begin M1 in the same branch.

</user_query>

## Outcome

M0 live Trust Authority is **not** operational. Design is frozen for `scope_and_design_approval`. No runtime mutation on this review route.

## Scope

### In scope

- Inspect live GitHub and this host (no secrets)
- Design freeze: M0.0–M0.3 slices, dedicated CI host, spec/plan paths
- Stop at named human gates

### Out of scope

- Creating `milestone/m0-live-trust-authority` or a draft PR on this review route (`write_agent=null`)
- compose-up, webhook, branch-protect, PEM/JWT, GitHub Actions
- M1 (already on main), M2–M9, this laptop as CI host

## Constraints

- Backward compatibility: Trust CI 2.1.0 source stays; product VERSION stays 2.0.12
- Data/privacy: never print or commit PEM, webhook secret, admin token, human approval keys
- Operational: prove App-owned check before protecting `main`; disable leftover Actions workflow 340420982 in M0.3
