# Security review closure — FAIL

Route: `75aa6daa89b1`
Reviewed fingerprint: `0e059501206c9ae185af36dac238d1576852a82328277e97edbf7896646d93e8`
Reviewer: `security_reviewer`
Scope: only the new privileged PostgreSQL role-bootstrap and Compose upgrade path added after the prior security PASS.

## Verdict

**FAIL.** The normal migration-003-to-004 path and an ordinary idempotent rerun
work, but the bootstrap does not restore the documented exact least-privilege
state of an existing deployer role. One MEDIUM security finding remains.

## Finding

### MEDIUM — role repair preserves `BYPASSRLS` instead of failing closed

- File: `trust-ci/postgres/upgrade/004_deployer_role.sh:20`
- Test gap: `trust-ci/tests/postgres_upgrade_probe.py:36`

The bootstrap describes the existing-role path as a repair and explicitly resets
`NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`, and `NOINHERIT`, but
it does not set `NOBYPASSRLS`. PostgreSQL keeps an existing role's omitted
attribute unchanged. Consequently, a pre-existing `trust_ci_deployer` with
`BYPASSRLS` survives the privileged bootstrap, the script exits successfully,
and Compose permits migration and service startup. This is not an exact or
fail-closed repair of the runtime identity.

The upgrade probe asserts only `(rolsuper, rolcreatedb, rolcreaterole,
rolreplication) == (false, false, false, false)` and therefore cannot detect the
surviving privilege. It also does not assert `rolinherit`, `rolcanlogin`, or the
connection limit.

Reproduction against disposable PostgreSQL 17.6:

1. Initialize the test database and its normal roles.
2. Run `ALTER ROLE trust_ci_deployer BYPASSRLS` as the test administrator.
3. Run `postgres/upgrade/004_deployer_role.sh` successfully.
4. Query `pg_roles.rolbypassrls`; observed result: `t`.

Required closure: include `NOBYPASSRLS` in the repair statement and make the
upgrade probe assert the full intended attribute tuple. Because role membership
is separate from role attributes, either reject unexpected memberships or
explicitly constrain the supported upgrade precondition and verify it before
success; otherwise an unexpectedly pre-existing role may retain inherited
capabilities despite `NOINHERIT` being reversible later.

## Controls that passed

- The bootstrap target is fixed to `trust_ci_deployer`; no environment-controlled
  role name or SQL identifier is accepted.
- Missing administrator/deployer credentials and every `psql`/SQL error terminate
  the one-shot nonzero. `migrate` requires `service_completed_successfully`, so a
  bootstrap failure prevents migration, API, and worker startup.
- Administrator authentication uses `PGPASSWORD`; the deployer password is read
  through `psql` `\getenv` and quoted as a SQL literal, not placed in command-line
  arguments. The script does not read or handle any human signing key.
- The bootstrap grants only database `CONNECT` and schema `USAGE`; migration 004
  remains responsible for the narrow deployer functions. It grants no table DML
  and no role-management capability.
- Fresh initialization keeps API, worker, migrator, backup, and deployer roles
  `NOCREATEROLE`. The upgrade script grants `CREATEROLE` to neither migrator nor
  any runtime role.
- The administrator operation is idempotent for the expected state: the real
  003-to-004 drill ran the bootstrap twice and passed migration 004.

## Verification evidence

- `bash -n trust-ci/postgres/upgrade/004_deployer_role.sh trust-ci/scripts/postgres-role-upgrade-drill.sh`: **PASS**.
- `PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest test_database_roles -v`: **7/7 PASS**.
- `trust-ci/scripts/postgres-role-upgrade-drill.sh` with locally present immutable
  Python/PostgreSQL image digests: **PASS** (`postgres 003-to-004 role upgrade drill: PASS`).
- Disposable hostile-state probe described above: bootstrap exited zero and
  returned `rolbypassrls = t`, confirming the finding.

The first drill invocation without required immutable-image environment values
failed before container startup as designed; it was rerun with explicit pinned
digests already present locally.

## Residual risks

- `role-bootstrap` receives the whole `postgres.env`, so its one-shot container
  also sees API, worker, migrator, and backup database passwords it does not use.
  The administrator credential already dominates database authority, and the
  same pinned PostgreSQL image receives these variables for fresh initialization,
  so this is recorded as exposure to minimize rather than a separate blocker.
- The one-shot service is not hardened with the read-only/cap-drop/no-new-
  privileges controls used by API and worker. Its only bind mount is read-only and
  its image is digest-pinned, but operators should minimize its lifetime and
  protect Docker inspection access because it carries the database administrator
  credential.

No product/application code, receipt, human signature, private key, deployment,
or external system was changed by this review. Earlier security reports are
preserved unchanged.
