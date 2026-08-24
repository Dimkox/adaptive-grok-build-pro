# Rollback plan — <user_query>
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

## Trigger conditions

## Application rollback

## Data recovery / forward-fix

## Verification after rollback
