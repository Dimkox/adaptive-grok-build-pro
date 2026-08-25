from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DatabaseRoleTests(unittest.TestCase):
    def test_role_specific_environment_files_do_not_share_database_identity(self) -> None:
        common = (ROOT / 'trust-ci/env/common.env.example').read_text(encoding='utf-8')
        api = (ROOT / 'trust-ci/env/api.env.example').read_text(encoding='utf-8')
        worker = (ROOT / 'trust-ci/env/worker.env.example').read_text(encoding='utf-8')
        migration = (ROOT / 'trust-ci/env/migration.env.example').read_text(encoding='utf-8')
        backup = (ROOT / 'trust-ci/env/backup.env.example').read_text(encoding='utf-8')
        self.assertNotIn('TRUST_CI_DATABASE_URL=', common)
        self.assertIn('trust_ci_api', api)
        self.assertIn('trust_ci_worker', worker)
        self.assertIn('trust_ci_migrator', migration)
        self.assertIn('trust_ci_backup', backup)

    def test_postgres_bootstrap_creates_non_superuser_roles_and_no_public_create(self) -> None:
        script = (ROOT / 'trust-ci/postgres/init/001_roles.sh').read_text(encoding='utf-8')
        for role in ('trust_ci_api', 'trust_ci_worker', 'trust_ci_migrator', 'trust_ci_backup'):
            self.assertIn(role, script)
            self.assertIn(f'ALTER ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', script)
        self.assertIn('REVOKE CREATE ON SCHEMA public FROM PUBLIC', script)
        self.assertIn('GRANT CREATE ON SCHEMA public TO trust_ci_migrator', script)

    def test_grant_migration_separates_api_worker_migrator_and_backup_capabilities(self) -> None:
        sql = (ROOT / 'trust-ci/sql/003_database_roles.sql').read_text(encoding='utf-8')
        self.assertIn('GRANT SELECT, INSERT ON trust_ci_approvals TO trust_ci_api', sql)
        self.assertNotIn('GRANT INSERT ON trust_ci_attestations TO trust_ci_api', sql)
        self.assertIn('GRANT SELECT, INSERT ON trust_ci_attestations TO trust_ci_worker', sql)
        self.assertIn('GRANT EXECUTE ON FUNCTION trust_ci_claim_job', sql)
        self.assertIn('GRANT SELECT ON ALL TABLES IN SCHEMA public TO trust_ci_backup', sql)
        self.assertNotIn('GRANT INSERT ON ALL TABLES IN SCHEMA public TO trust_ci_backup', sql)

    def test_compose_uses_role_specific_env_and_initialization(self) -> None:
        compose = (ROOT / 'trust-ci/compose.yaml').read_text(encoding='utf-8')
        self.assertIn('./postgres/init:/docker-entrypoint-initdb.d:ro', compose)
        migrate = compose.split('  migrate:', 1)[1].split('  api:', 1)[0]
        api = compose.split('  api:', 1)[1].split('  docker-engine:', 1)[0]
        worker = compose.split('  worker:', 1)[1]
        self.assertIn('./env/migration.env', migrate)
        self.assertIn('./env/api.env', api)
        self.assertIn('./env/worker.env', worker)

    def test_backup_service_overrides_api_database_role_with_read_only_backup_role(self) -> None:
        service = (ROOT / 'trust-ci/systemd/adaptive-trust-ci-backup.service').read_text(encoding='utf-8')
        self.assertIn('TRUST_CI_BACKUP_DATABASE_URL', service)
        self.assertIn('--env TRUST_CI_DATABASE_URL=', service)


if __name__ == '__main__':
    unittest.main()
