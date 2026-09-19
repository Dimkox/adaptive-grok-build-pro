# Documentation analysis — issue #128

Route 3822310b0593; read-only.

- `factory/README.md` reports PostgreSQL restart evidence but does not claim cancellation/orphan recovery. Add only a bounded cleanup note if implementation proves it.
- Do not expand the durable Factory DB runbook with harness sweeping; its durable-data protections remain unchanged.
- Package docs should state that only nonce-bound resources past a conservative TTL are reclaimed, ambiguous resources are preserved, and no global cron/prune exists.
- Operator output should include reclaimed count and exact identities; do not claim the host is globally free of orphans.
- The current harness creates an anonymous volume; earlier issue wording about a named volume is inaccurate.
