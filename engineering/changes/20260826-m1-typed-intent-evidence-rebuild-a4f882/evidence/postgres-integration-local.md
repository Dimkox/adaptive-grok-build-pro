# Local PostgreSQL integration evidence — M1

Date: 2026-08-26

## Boundary and setup

This is local test evidence only. It does not describe or authorize a deployed Trust CI database, worker, holdout, policy, App check, approval, merge, or production operation.

- The ignored repository-root `.env` is mode `0600`. An authorized local setup copied `POSTGRES_USER` and `POSTGRES_PASSWORD` from `/home/pall/app-stack/.env` and added `TRUST_CI_TEST_DATABASE_URL`; no value is recorded here or committed.
- The dedicated database is `adaptive_grok_build_pro_test` in the already-running local `app-stack` container `postgres-db`. No application database was used for the tests.
- The four migration-referenced roles are `trust_ci_api`, `trust_ci_worker`, `trust_ci_migrator`, and `trust_ci_backup`. They were created as `NOLOGIN` roles and granted access only to the dedicated test database and its schema.

Secret-safe setup checks and command shapes:

```bash
stat -c '%a %n' .env
git check-ignore -v .env

# Executed locally with administrative identity and credentials omitted:
docker exec postgres-db psql <redacted-admin-connection> -c \
  'CREATE DATABASE adaptive_grok_build_pro_test'
docker exec postgres-db psql <redacted-admin-connection> \
  -f <redacted-NOLOGIN-role-and-test-database-grant-bootstrap>
```

## Bootstrap failure and correction

The first focused invocation failed during migration setup, before any of the ten test methods ran, because migration `003_database_roles.sql` grants privileges to the four `trust_ci_*` roles and those roles did not yet exist. Creating the four bounded `NOLOGIN` roles and test-database/schema grants fixed that bootstrap-order root cause; no product source change was needed.

## Executed tests

The DSN is intentionally redacted below. The actual invocation supplied it from the ignored mode-0600 local environment.

```bash
cd trust-ci/tests
TRUST_CI_TEST_DATABASE_URL='<redacted-local-DSN>' \
  PYTHONPATH=../src:. \
  /tmp/adaptive-grok-m1-venv-20260826/bin/python \
  -m unittest -v test_postgres_integration

cd ../..
TRUST_CI_TEST_DATABASE_URL='<redacted-local-DSN>' \
  PYTHONPATH=trust-ci/src:trust-ci/tests \
  /tmp/adaptive-grok-m1-venv-20260826/bin/python \
  -m unittest discover -s trust-ci/tests
```

Results:

- Focused PostgreSQL integration: **10/10 PASS**.
- Full Trust CI suite: **200/200 PASS, 0 skipped**.
- The database-backed cases include migration idempotence, concurrent claim exclusion, lease recovery/ownership, attempt exhaustion, webhook idempotency, approval replay rejection, current signed typed-metadata persistence, and exact pre-M1 signed-envelope store/replay compatibility.

## Schema and isolation validation

Catalog queries against only `adaptive_grok_build_pro_test` reported:

- six `trust_ci_*` tables, including the migration registry;
- three applied migrations, versions 1 through 3 (`schema`, operational indexes, database roles);
- all four required `trust_ci_*` roles present with `rolcanlogin = false`;
- role grants bounded to the dedicated test database/schema rather than any application database.

The test fixture truncates only Trust CI tables inside the dedicated database. The run did not alter the repository holdout, worker/policy deployment, PostgreSQL application schemas, or external GitHub state.

## Stop and rollback

- Stop: omit or unset `TRUST_CI_TEST_DATABASE_URL`; the integration class returns to an honest conditional skip and makes no database connection.
- Data rollback: after confirming no active test connection or dependency, a local database administrator may drop only `adaptive_grok_build_pro_test`.
- Role rollback: after the dedicated database is removed and dependency checks are clear, the administrator may drop only the four local `NOLOGIN` test roles listed above.
- Secret cleanup: remove the local DSN/copy from the ignored `.env` only when no further local run needs it. Never commit, print, or copy those values into evidence.
