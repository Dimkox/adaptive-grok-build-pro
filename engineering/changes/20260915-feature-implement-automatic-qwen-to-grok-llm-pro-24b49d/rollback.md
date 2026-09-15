# Rollback and recovery

1. Disable the shared failover entrypoint for new work and return callers to the unchanged direct primary socket.
2. Preserve the routing journal and backend observations; reconcile existing dispatch intents without resubmitting them.
3. Use a compatible reader for new attempt evidence, or a reviewed forward repair. Do not downgrade a state store to a reader that cannot interpret its version.

No rollback deletes jobs, artifacts, credentials, PRs or published content. A selected artifact is never automatically published.
