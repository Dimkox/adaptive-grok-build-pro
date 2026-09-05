# Rollback plan — L5 single-operator live MVP local runtime

## Trigger conditions

Default composition becomes effectful, durable replay diverges, tenant isolation
fails, interrupted work is replayed automatically, or artifact binding is not
exact.

## Application rollback

Disable/remove the optional local runtime configuration and compose the existing
in-memory store plus `UnavailableLandingProvider`/`UnavailableLandingPublisher`.
No live target or published artifact must be rolled back because this route makes
no external change.

## Data recovery / forward-fix

Stop the single local process and retain the private SQLite database/artifact
root for diagnosis. Do not down-migrate or rewrite history; an unknown/corrupt
schema or artifact is a bounded forward-fix with affected jobs kept
`needs_human`.

## Verification after rollback

Focused API tests must show `provider_unavailable`, exact replay, zero executor or
transport calls, `live_url=null`, and unchanged frozen product identities.
