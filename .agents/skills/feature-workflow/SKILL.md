---
name: feature-workflow
description: Use for new behavior, new subsystems, and architectural changes. Converts outcomes into acceptance criteria, bounded design, vertical tasks, tests, rollout, and rollback.
---

# Feature Workflow

Define what changes for the user before choosing implementation details. Cover:

- primary and alternate flows;
- permissions, empty/loading/error states;
- API/event/data compatibility;
- migration and backfill needs;
- observability and success metrics;
- staged rollout and rollback;
- explicit non-goals.

Prefer a vertical slice and existing architecture. A new service, queue, datastore, framework, or major dependency requires an ADR and named approval.
