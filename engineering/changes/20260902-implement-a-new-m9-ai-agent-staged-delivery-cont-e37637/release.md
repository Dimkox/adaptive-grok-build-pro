# Release Plan — M9 Staged Delivery and Recovery

This commit releases nothing. It is a documentation/design checkpoint only.

Future source go/no-go is dependency ordered: accepted M4→M8 exact chain; exact M8 profile/cohort; TDD source; final local verification and four route-selected independent reviews; separately authorized PR; App-owned policy-epoch Trust CI on exact head; required external signed scopes. Activation additionally requires exact merged SHA and externally verified artifact/SBOM/provenance/manifest/image, bound prior signed artifact, authorized nonproduction resources and exercised recovery.

Rollout, if separately approved, remains dry-run first: preview, staging, each bounded-canary exposure, then `needs_human`. There is no production adapter. Metric completeness/freshness/consistency and all five gates must pass at every step. Any missing fact is no-go.

The hard deadline **2026-09-08 00:00 UTC+3** cannot turn source, a fixture, documentation or a local receipt into accepted M8, signed authority, environment proof or production permission. See [schedule](schedule.md), [connectivity](connectivity.md), [ledger](ledger.md) and [rollback](rollback.md).
