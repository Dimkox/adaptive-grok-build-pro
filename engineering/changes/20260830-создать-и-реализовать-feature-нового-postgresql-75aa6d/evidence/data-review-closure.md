# Data review closure — PASS

Route: `75aa6daa89b1`
Reviewed fingerprint: `0e059501206c9ae185af36dac238d1576852a82328277e97edbf7896646d93e8`
Reviewer: `data_reviewer`
Scope: targeted closure of D1 from `data-review.md`; no broader product review.

## D1 closure

**PASS.** Existing persistent PostgreSQL installations now have an explicit
privileged pre-migration path:

- `trust-ci/postgres/upgrade/004_deployer_role.sh` connects with the PostgreSQL
  administrator identity, fails fast when required administrator/deployer
  credentials are absent, creates `trust_ci_deployer` only when missing, and can
  be rerun safely.
- Each run restores the intended login password and constrained role attributes:
  `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`, `NOINHERIT`, a
  connection limit of 5, and bounded statement/idle transaction timeouts. It
  grants only database `CONNECT` and schema `USAGE` before migration 004 grants
  the narrow `SECURITY DEFINER` consume/query/terminal functions. The migrator
  remains `NOCREATEROLE` and receives no role-management capability.
- Production Compose makes `migrate` depend on successful completion of the
  isolated `role-bootstrap` one-shot, which itself waits for healthy PostgreSQL.
  Therefore migration 004 cannot reach its unconditional deployer grants before
  the role exists; bootstrap failure prevents migration/API/worker startup.
- The upgrade drill constructs the relevant pre-change state on one persistent
  database: it removes the deployer role, applies only migrations 001–003,
  verifies the role is absent, runs the privileged bootstrap twice, and then
  applies/validates migration 004. This covers both existing-volume upgrade and
  bootstrap rerun behavior instead of relying on fresh-volume init alone.
- Operator and change-package documentation now state the ordering, failure
  recovery and rollback: fix administrator configuration, rerun the idempotent
  bootstrap, then rerun migration; retain the additive role/schema on service
  rollback and never compensate by granting `CREATEROLE` to the migrator.

## Evidence checked

- `bash trust-ci/scripts/postgres-role-upgrade-drill.sh` with the verified pinned
  Python/PostgreSQL image digests: **PASS** (`postgres 003-to-004 role upgrade
  drill: PASS`). The drill's trap removed its disposable containers, network and
  volume.
- The drill emitted one `CREATE ROLE` across two bootstrap invocations and two
  successful constrained `ALTER ROLE`/access sequences, then migration 004
  completed through `PostgresMigrator`.
- `PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest
  test_database_roles -v`: **7/7 PASS**.
- Static inspection confirmed the Compose dependency chain
  `postgres healthy -> role-bootstrap success -> migrate success -> api/worker`
  and no direct table mutation privilege was added to the deployer.

## Residual risk

The bootstrap is intentionally an administrator operation and receives the
administrator/deployer database credentials for its short one-shot lifetime.
Operators must keep `postgres.env` private and use the pinned PostgreSQL image.
An unexpected pre-existing `trust_ci_deployer` identity should be investigated
before rollout rather than treated as ordinary application state. This does not
block the documented upgrade from the known migration-003 state, where that role
does not exist.

## Verdict

**PASS. D1 is closed on fingerprint
`0e059501206c9ae185af36dac238d1576852a82328277e97edbf7896646d93e8`.**
The original `data-review.md` remains preserved as the finding history.
