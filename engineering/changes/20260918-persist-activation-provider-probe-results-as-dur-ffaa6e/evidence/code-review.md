# Code review: durable activation probes (#121)

Scope: current diff on branch `fix/issue-121-durable-activation-probe`, reviewed read-only. Focused review covered SQLite schema/migration and append-only revisions, at-most-once dispatch and recovery, landing-only operator API, credential/body handling, backup/restore, and architecture ownership.

## Findings

No blocking or non-blocking code findings.

## Evidence

- `git diff --check` passed.
- `python3 -m unittest factory.tests.test_landing_activation_probe -v`: 8 tests passed, including commit-before-provider, one-call same-key retry and concurrent retry behavior, scope/actor/landing-only enforcement, restart ambiguity, and provider error sanitization.
- `python3 -m unittest factory.tests.test_landing_backup factory.tests.test_landing_sqlite_store factory.tests.test_landing_failover_backend -v`: 28 tests passed, including v1/v2 to v3 migration, immutable event revisions, backup/restore preservation, WAL snapshot behavior, and no fabricated historical activation record.

The reviewer confirmed the idempotency digest remains on the original reservation revision when terminal/unknown revisions are appended, so retries can resolve the original probe without dispatching again. The raw key, provider response/body, credentials, and exception text are not stored in the probe event schema; result persistence is allowlisted and provider errors are reduced to bounded category/status fields.
