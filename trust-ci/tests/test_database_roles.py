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
        self.assertIn('TRUST_CI_DEPLOYER_DATABASE_URL=postgresql://trust_ci_deployer:', api)
        self.assertIn('trust_ci_worker', worker)
        self.assertIn('trust_ci_migrator', migration)
        self.assertIn('trust_ci_backup', backup)

    def test_postgres_bootstrap_creates_non_superuser_roles_and_no_public_create(self) -> None:
        script = (ROOT / 'trust-ci/postgres/init/001_roles.sh').read_text(encoding='utf-8')
        for role in ('trust_ci_api', 'trust_ci_worker', 'trust_ci_migrator', 'trust_ci_backup', 'trust_ci_deployer'):
            self.assertIn(role, script)
            self.assertIn(f'ALTER ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', script)
        self.assertIn('REVOKE CREATE ON SCHEMA public FROM PUBLIC', script)
        self.assertIn('GRANT CREATE ON SCHEMA public TO trust_ci_migrator', script)
        self.assertIn('GRANT USAGE ON SCHEMA public TO trust_ci_deployer', script)
        self.assertIn('TRUST_CI_DEPLOYER_DB_PASSWORD', script)
        self.assertNotIn("PASSWORD :'", script)
        self.assertIn("PASSWORD %L', :'deployer_pw'", script)

    def test_upgrade_bootstrap_passes_password_as_a_quoted_runtime_parameter(self) -> None:
        script = (ROOT / 'trust-ci/postgres/upgrade/004_deployer_role.sh').read_text(
            encoding='utf-8'
        )
        self.assertNotIn("PASSWORD :'", script)
        self.assertIn("PASSWORD %L', :'deployer_pw'", script)

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
        self.assertIn('/opt/adaptive-trust-ci/supply-chain:ro', api)
        self.assertIn('./env/worker.env', worker)

    def test_backup_service_overrides_api_database_role_with_read_only_backup_role(self) -> None:
        service = (ROOT / 'trust-ci/systemd/adaptive-trust-ci-backup.service').read_text(encoding='utf-8')
        self.assertIn('TRUST_CI_BACKUP_DATABASE_URL', service)
        self.assertIn('--env TRUST_CI_DATABASE_URL=', service)

    def test_promotion_migration_uses_only_constrained_runtime_functions(self) -> None:
        sql = (ROOT / 'trust-ci/sql/004_production_promotions.sql').read_text(encoding='utf-8')
        current_accept_signature = (
            'trust_ci_accept_promotion(uuid, text, text, text, text, text, text, text, '
            'text, uuid, text, timestamptz, timestamptz, jsonb, jsonb, text, '
            'text, text, text, text, uuid, timestamptz)'
        )
        api_epoch_accept_signature = (
            'trust_ci_accept_promotion(uuid, text, text, text, text, text, text, text, '
            'text, text, uuid, text, timestamptz, timestamptz, jsonb, jsonb, text, text, '
            'text, text, text, uuid, timestamptz)'
        )
        for table in (
            'trust_ci_merge_facts',
            'trust_ci_protected_branch_evidence',
            'trust_ci_promotions',
            'trust_ci_promotion_idempotency',
            'trust_ci_promotion_consumptions',
            'trust_ci_promotion_events',
            'trust_ci_active_policy',
        ):
            self.assertIn(f'REVOKE ALL ON {table} FROM PUBLIC', sql)
        self.assertIn('SECURITY DEFINER', sql)
        self.assertIn('SET search_path = pg_catalog, public', sql)
        self.assertIn('GRANT EXECUTE ON FUNCTION trust_ci_record_merge_fact', sql)
        self.assertIn('GRANT EXECUTE ON FUNCTION trust_ci_record_protected_branch_evidence', sql)
        self.assertIn('GRANT EXECUTE ON FUNCTION trust_ci_record_promotion_rejection', sql)
        self.assertIn(f'REVOKE ALL ON FUNCTION {current_accept_signature} FROM PUBLIC', sql)
        self.assertIn(f'GRANT EXECUTE ON FUNCTION {current_accept_signature} TO trust_ci_api', sql)
        self.assertNotIn(f'GRANT EXECUTE ON FUNCTION {api_epoch_accept_signature}', sql)
        self.assertIn('GRANT EXECUTE ON FUNCTION trust_ci_activate_policy(text) TO trust_ci_migrator', sql)
        self.assertNotIn('GRANT EXECUTE ON FUNCTION trust_ci_activate_policy(text) TO trust_ci_api', sql)
        self.assertNotIn('GRANT EXECUTE ON FUNCTION trust_ci_activate_policy(text) TO trust_ci_deployer', sql)
        self.assertNotIn('GRANT DELETE', sql)
        self.assertNotIn('GRANT TRUNCATE', sql)
        self.assertNotIn('GRANT UPDATE ON trust_ci_promotions', sql)
        self.assertNotIn('GRANT INSERT ON trust_ci_promotions', sql)
        self.assertIn('TO trust_ci_deployer', sql)
        self.assertNotIn("IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'trust_ci_deployer')", sql)

    def test_deployer_has_an_isolated_database_example_identity(self) -> None:
        postgres = (ROOT / 'trust-ci/env/postgres.env.example').read_text(encoding='utf-8')
        deployer = (ROOT / 'trust-ci/env/deployer.env.example').read_text(encoding='utf-8')
        self.assertIn('TRUST_CI_DEPLOYER_DB_PASSWORD' + '=', postgres)
        self.assertIn('postgresql://trust_ci_deployer:', deployer)
        self.assertIn('TRUST_CI_ROLE=deployer', deployer)


if __name__ == '__main__':
    unittest.main()
