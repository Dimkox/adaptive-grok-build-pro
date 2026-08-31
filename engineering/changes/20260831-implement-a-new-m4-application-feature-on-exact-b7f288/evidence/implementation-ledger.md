# M4 implementation ledger

## Gate and base binding

- Exact implementation base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- Clean-base tree fingerprint: `17f8ca8d94a118d02192e5fa0bd9cafc6e219354e390f1d640511d6e6a4fcaa2`, derived by the repository `tree_fingerprint` algorithm before package edits.
- Scope/design: explicitly approved by the user in the active conversation.
- Migration scope: fresh disposable local PostgreSQL only; no external, shared, Trust CI or production write.
- Producer handoff ruling: M2/M3 exact-base/head values remain producer-owned frozen values; M4 validates them and does not replace them with its implementation base.

## TDD cycles

Each vertical records its RED command/result before production source is added, then GREEN/refactor commands. Final real PostgreSQL and root verifier evidence is appended after the last product change.

### Contracts

- RED: `python3 -m unittest factory.tests.test_contracts -v` failed with `ModuleNotFoundError: adaptive_factory`; the package/contract behavior was absent.
- GREEN: the same command passed 5 tests after closed immutable handoffs/intake/limits, canonical digests, M0 freshness/exception and bounds were implemented.
- Focused repair: the first GREEN exposed that a valid App check name contains `@`; the existing failing contract test drove a bounded check-name grammar repair, after which all 5 passed.

### State and retry policy

- RED: `python3 -m unittest factory.tests.test_state -v` failed because `adaptive_factory.state` did not exist.
- GREEN: the same command passed 6 tests covering every state pair, terminality, operator requeue evidence, provider denial, rejected future delivery states and the initial-plus-two closed retry policy.

### Migration foundation

- RED: `python3 -m unittest factory.tests.test_migrations -v` failed because `adaptive_factory.migrations` did not exist.
- GREEN: the same command passed 4 tests for contiguous discovery, immutable checksum planning, drift rejection and factory-only schema markers.
- Ruling: bootstrap creates only `factory.schema_migrations`; all three packaged migrations apply under one factory-specific advisory transaction and never inspect another migration registry.

### Durable intake, leases, capacity and recovery

- RED: `python3 -m unittest factory.tests.test_service -v` failed because the service boundary did not exist; disposable PostgreSQL tests then exposed the four-hour timestamp-boundary check, repository-capacity starvation and expired-grant reconciliation defects.
- GREEN unit: service authorization/bounds passed 3 tests; prior contract/state/migration suite passed 15 tests.
- GREEN PostgreSQL: `FACTORY_TEST_DATABASE_URL=<redacted> ... -m unittest factory.tests.test_postgres_integration -v` passed 4 real PostgreSQL 17 tests in 5.887s after the focused repairs.
- Database-time ruling: task acceptance/deadline, lease expiry and reconciliation use PostgreSQL time. The restart tests expire only the named disposable run row to avoid a 30-second sleep; production callers cannot supply the database clock.
- Restart probe: the bounded subprocess holder/reclaim script passed; one expired lease was repaired, a higher fence issued, and the late heartbeat rejected.
