# Data review — FAIL

Route: `75aa6daa89b1`
Reviewed fingerprint: `f8d87aa4d8defd71181014278002624bdb751fd3d7ef06ba8435cbc4bb89ea7f`
Reviewer: `data_reviewer`
Scope: final read-only PostgreSQL/data review of the actual working-tree diff.

## Blocking finding

### D1 — Existing PostgreSQL installations cannot apply migration 004

`trust-ci/sql/004_production_promotions.sql` unconditionally grants execution to
`trust_ci_deployer`. The new role is created only by
`trust-ci/postgres/init/001_roles.sh`, which PostgreSQL's container entrypoint runs
only while initializing an empty data directory. An already deployed persistent
database that has migrations 001–003 therefore has no `trust_ci_deployer` role,
and migration 004 stops at the first `GRANT ... TO trust_ci_deployer` with
`role "trust_ci_deployer" does not exist`. The migration transaction rolls back,
so this is recoverable, but rollout cannot proceed.

The populated 003-to-004 integration test does not cover this upgrade condition:
its fresh test cluster runs the modified init script first, so the deployer role
already exists before the test applies migrations 001–003 and then 004.

Required repair: provide and document an idempotent privileged upgrade/preflight
that creates/configures `trust_ci_deployer`, grants database/schema access, and
sets its credential before the migrator runs 004 on an existing cluster. Add an
upgrade-path regression whose cluster begins in the real pre-change state (roles
from the old init script, migrations through 003) and proves the documented
preflight plus migration 004 succeeds. The migrator role is intentionally
`NOCREATEROLE`, so migration 004 itself must not silently broaden that role.

## Passing observations

- Deployment and packaged migration 004 are byte-for-byte identical; historical
  migrations are checksum-locked and migration application is serialized by an
  advisory transaction lock.
- Migration 004 is additive and forward-only. It does not rewrite or destructively
  alter existing tables, and foreign keys use `ON DELETE RESTRICT` for immutable
  provenance, promotions, consumptions and audit history.
- Promotion acceptance is atomic across idempotency reservation, exact protected
  evidence validation, immutable promotion storage and accepted-event append.
  Unique nonce, payload digest, idempotency key and promotion ID constraints close
  replay races; a failed function call rolls the reservation back.
- Consumption is atomic and single-use. The promotion primary key permits one
  consumption, operation ID is globally unique, the exact tuple and current policy
  are rechecked under database locks, and the consumed event is in the same
  transaction. Concurrent losers fail closed.
- Active-policy reads use `FOR SHARE`, serializing acceptance/consumption against
  policy activation and preventing a policy-epoch TOCTOU window.
- Merge-fact claiming uses `FOR UPDATE SKIP LOCKED`, claim IDs and lease/attempt
  fencing. Retry delay is bounded to 5–300 seconds, exhausted transient work moves
  to `dead`, and only constrained exhausted failures can be requeued.
- Runtime roles receive function-level capabilities rather than direct mutation of
  authority tables. PUBLIC table/function access is revoked; the backup identity is
  read-only; no DELETE/TRUNCATE or direct promotion INSERT/UPDATE grant is present.
- Backup creation is custom-format, digest/size manifested, atomically installed
  with private file mode, and retention verifies candidates before deletion. The
  disposable restore drill preserves ACLs, restores into a separate database and
  checks worker/API/deployer access plus persisted single-use promotion state.

## Residual risks after D1 is repaired

- Migration 004 is intentionally irreversible. Rollback is service rollback or a
  forward migration; authority, replay and audit rows must never be deleted.
- The broad `trust_ci_promotions_unconsumed_idx` also indexes consumed rows and may
  accumulate unnecessary write/storage cost. This is not a correctness blocker at
  the documented volume, but production cardinality and index usage should be
  observed before designing a later partial-index cleanup.
- Crash after atomic consume remains fail-closed and requires reconciliation by the
  unique operation ID before any further production action.

## Verdict

**FAIL** until D1 is repaired and its real existing-cluster upgrade path is tested.
No other blocking PostgreSQL/data finding was identified in this review.
