---
name: release-readiness
description: Use for release, deployment, migration rollout, canary, rollback, or final go/no-go preparation.
---

# Release Readiness

Bind the final tree/commit to current verification and review receipts. Check:

- immutable build artifact and provenance;
- migrations and compatibility window;
- feature flags and staged rollout;
- smoke/E2E/contract evidence;
- SLI/SLO, dashboards, alerts, and support visibility;
- rollback/forward-fix and data recovery;
- ownership, runbook, and go/no-go criteria.

Do not deploy or merge. Produce a release decision report for the human owner.

After go/no-go, run `python3 scripts/grok_deploy.py`. Use `--record` only with a valid production approval. Humans run the printed commands. Do not deploy from this skill.
