from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import psycopg

from adaptive_trust_ci.migrations import PostgresMigrator


def main() -> None:
    phase = sys.argv[1]
    migrator_url = os.environ['TRUST_CI_TEST_DATABASE_URL']
    admin_url = os.environ['TRUST_CI_TEST_ADMIN_DATABASE_URL']
    root = Path(__file__).resolve().parents[1] / 'sql'
    if phase == 'prepare':
        with tempfile.TemporaryDirectory() as directory:
            partial = Path(directory)
            for version in ('001', '002', '003'):
                source = next(root.glob(f'{version}_*.sql'))
                shutil.copyfile(source, partial / source.name)
            PostgresMigrator(migrator_url, partial).apply()
        with psycopg.connect(admin_url) as connection:
            assert connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = 'trust_ci_deployer'"
            ).fetchone() is None
        return
    if phase != 'verify':
        raise SystemExit('expected prepare or verify')
    plan = PostgresMigrator(migrator_url).apply()
    assert plan.pending == () and plan.applied[-1].version == 4
    with psycopg.connect(admin_url) as connection:
        row = connection.execute(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
            "rolbypassrls, rolinherit, rolcanlogin, rolconnlimit "
            "FROM pg_roles WHERE rolname = 'trust_ci_deployer'"
        ).fetchone()
        assert row == (False, False, False, False, False, False, True, 5)


if __name__ == '__main__':
    main()
