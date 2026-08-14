---
name: incident-response
description: Use for production outages, severe regressions, data incidents, or urgent hotfixes where containment and evidence preservation precede repair.
---

# Incident Response

1. Establish impact, start time, affected users, and current risk.
2. Preserve logs, traces, metrics, deploy markers, and data evidence.
3. Contain: stop rollout, disable a flag, isolate integration, or roll back through approved operations.
4. Reproduce and identify root cause.
5. Implement the smallest hotfix with regression evidence.
6. Verify recovery using user-visible and system metrics.
7. Record follow-up prevention as tests, guards, runbooks, or architecture work.

Grok Build prepares actions and evidence; it does not execute production mutation without approval.
