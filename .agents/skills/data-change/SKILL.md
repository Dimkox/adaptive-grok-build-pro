---
name: data-change
description: Use for SQL schema changes, migrations, indexes, backfills, Elasticsearch/OpenSearch mappings, ClickHouse pipelines, and data-quality work.
---

# Data Change

Produce evidence for:

- schema before and after;
- volume and distribution assumptions;
- query plan and index impact;
- lock and downtime risk;
- bounded/resumable backfill design;
- validation queries and stop conditions;
- rollback or forward recovery;
- tenant isolation and sensitive data;
- metrics, alerts, and reconciliation.

Never run destructive production SQL. Operational state, search projections, and analytical stores must have explicit sources of truth and replay/rebuild strategies.
