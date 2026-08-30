# Security review closure 2 — PASS

Route: `75aa6daa89b1`
Reviewed fingerprint: `9f4d8d2faa914852c9f71499e7f46caa2b61e3881210d3aaa005144c7667a3af`
Reviewer: `security_reviewer`
Scope: surgical regression review of the prior `BYPASSRLS` / existing-role repair finding only.

## Verdict

**PASS.** The MEDIUM finding from `security-review-closure.md` is closed. No
new findings were sought or recorded outside this regression scope.

## Closure evidence

- `trust-ci/postgres/upgrade/004_deployer_role.sh:20` now restores the complete
  intended security-sensitive role attributes, including explicit
  `NOBYPASSRLS`, while retaining `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`,
  `NOREPLICATION`, `NOINHERIT`, `LOGIN`, and connection limit 5.
- `trust-ci/tests/postgres_upgrade_probe.py:36` now checks the full tuple:
  `(rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
  rolinherit, rolcanlogin, rolconnlimit)` equals
  `(false, false, false, false, false, false, true, 5)`.
- The real persistent-volume upgrade drill creates the missing deployer role,
  then deliberately sets `BYPASSRLS`, reruns the bootstrap, and verifies the
  complete constrained tuple after migration 004. Result: **PASS**
  (`postgres 003-to-004 role upgrade drill: PASS`).
- The bootstrap inspects `pg_auth_members` after constraining the role and raises
  an exception if `trust_ci_deployer` is a member of any role. A disposable
  PostgreSQL 17.6 probe created an unexpected parent role and granted it to the
  deployer; bootstrap exited **3** with
  `trust_ci_deployer must not be a member of any role`. The membership remained
  present for operator investigation, but the nonzero result prevents the
  Compose `service_completed_successfully` dependency from admitting migration.
  This is the required fail-closed behavior.

## Commands run

- `bash -n trust-ci/postgres/upgrade/004_deployer_role.sh trust-ci/scripts/postgres-role-upgrade-drill.sh`: **PASS**.
- `PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest test_database_roles -v`: **7/7 PASS**.
- `trust-ci/scripts/postgres-role-upgrade-drill.sh` with locally present pinned
  Python 3.12 and PostgreSQL 17.6 image digests: **PASS**.
- Disposable unexpected-membership probe: expected failure observed
  (`bootstrap_exit=3`, `membership_count=1`). Cleanup removed its isolated
  container, network, and volume.

No product code, receipt, external system, human signature, or private key was
changed or used. Previous reports remain preserved.
