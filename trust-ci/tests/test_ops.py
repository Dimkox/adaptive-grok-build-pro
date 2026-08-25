from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _support import policy_data
from adaptive_trust_ci.github import branch_protection_payload
from adaptive_trust_ci.holdout import bundle_digest
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.sandbox import ContainerExecutor


ROOT = Path(__file__).resolve().parents[2]


class OperationsTests(unittest.TestCase):
    def test_sandbox_uses_daemon_host_paths_and_mounts_holdout_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / 'workspace'
            holdout = Path(directory) / 'holdout'
            (workspace / '.git').mkdir(parents=True)
            holdout.mkdir()
            (holdout / 'validate.py').write_text('print("ok")\n', encoding='utf-8')
            policy = Policy.from_dict(
                policy_data(holdout_path=str(holdout), holdout_digest=bundle_digest(holdout))
            )
            argv = ContainerExecutor(policy.sandbox).build_argv(
                workspace=workspace,
                workspace_host_path=Path('/var/lib/adaptive-trust-ci/workspaces/job-1'),
                command=('python3', '/holdout/validate.py', '/workspace'),
                env={'CI': 'true', 'TRUST_CI_HEAD_SHA': 'b' * 40},
                container_name='trust-ci-test',
                holdout_path=holdout,
                holdout_host_path=Path('/etc/adaptive-trust-ci/holdout'),
            )
        joined = ' '.join(argv)
        self.assertIn('--network none', joined)
        self.assertIn('--cap-drop ALL', joined)
        self.assertIn('no-new-privileges', joined)
        self.assertIn('--read-only', joined)
        self.assertIn('/var/lib/adaptive-trust-ci/workspaces/job-1:/workspace:rw', joined)
        self.assertIn('/var/lib/adaptive-trust-ci/workspaces/job-1/.git:/workspace/.git:ro', joined)
        self.assertIn('/etc/adaptive-trust-ci/holdout:/holdout:ro', joined)
        self.assertNotIn(str(workspace), joined)
        self.assertNotIn('GITHUB_TOKEN', joined)
        self.assertNotIn('TRUST_CI_GITHUB', joined)

    def test_sandbox_exposes_workspace_as_python_package_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / 'workspace'
            (workspace / '.git').mkdir(parents=True)
            policy = Policy.from_dict(policy_data())
            argv = ContainerExecutor(policy.sandbox).build_argv(
                workspace=workspace,
                workspace_host_path=Path('/var/lib/adaptive-trust-ci/workspaces/job-1'),
                command=('python3', '-m', 'unittest', 'discover', '-s', 'tests'),
                env={},
                container_name='trust-ci-test',
            )
        self.assertIn('PYTHONPATH=/workspace', argv)

    def test_sandbox_rejects_relative_daemon_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / 'workspace'
            (workspace / '.git').mkdir(parents=True)
            policy = Policy.from_dict(policy_data())
            with self.assertRaisesRegex(ValueError, 'workspace_host_path'):
                ContainerExecutor(policy.sandbox).build_argv(
                    workspace=workspace,
                    workspace_host_path=Path('relative/workspace'),
                    command=('python3', '--version'),
                    env={},
                    container_name='trust-ci-test',
                )

    def test_postgres_schema_has_durable_lease_and_replay_constraints(self) -> None:
        sql = (ROOT / 'trust-ci/sql/001_schema.sql').read_text(encoding='utf-8')
        self.assertIn('FOR UPDATE SKIP LOCKED', sql)
        self.assertIn('idempotency_key char(64) NOT NULL UNIQUE', sql)
        self.assertIn('nonce text NOT NULL UNIQUE', sql)
        self.assertIn('lease_expires_at', sql)
        self.assertIn('attempts-exhausted-after-worker-loss', sql)

    def test_packaged_migrations_match_deployment_migrations(self) -> None:
        deployment = ROOT / 'trust-ci/sql'
        packaged = ROOT / 'trust-ci/src/adaptive_trust_ci/resources'
        deployment_files = sorted(path.name for path in deployment.glob('[0-9][0-9][0-9]_*.sql'))
        packaged_files = sorted(path.name for path in packaged.glob('[0-9][0-9][0-9]_*.sql'))
        self.assertEqual(deployment_files, packaged_files)
        self.assertGreaterEqual(len(deployment_files), 2)
        for name in deployment_files:
            self.assertEqual((deployment / name).read_bytes(), (packaged / name).read_bytes(), name)

    def test_production_compose_uses_prebuilt_images_and_isolated_dind(self) -> None:
        compose = (ROOT / 'trust-ci/compose.yaml').read_text(encoding='utf-8')
        self.assertNotIn('build:', compose)
        self.assertIn('TRUST_CI_POSTGRES_IMAGE:?', compose)
        self.assertIn('TRUST_CI_API_IMAGE:?', compose)
        self.assertIn('TRUST_CI_WORKER_IMAGE:?', compose)
        self.assertIn('TRUST_CI_DIND_IMAGE:?', compose)
        self.assertIn('  docker-engine:', compose)
        docker_engine = compose.split('  docker-engine:', 1)[1].split('  worker:', 1)[0]
        worker = compose.split('  worker:', 1)[1]
        before_worker = compose.split('  worker:', 1)[0]
        self.assertNotIn('/var/run/docker.sock', compose)
        self.assertIn('privileged: true', docker_engine)
        self.assertIn('trust-ci-docker-data:/home/rootless/.local/share/docker', docker_engine)
        self.assertIn('DOCKER_HOST: tcp://docker-engine:2375', worker)
        self.assertIn('github-app-private-key.pem:/run/secrets', worker)
        self.assertIn('/var/lib/adaptive-trust-ci/workspaces', docker_engine)
        self.assertIn('/etc/adaptive-trust-ci/holdout:ro', docker_engine)
        self.assertNotIn('github-app-private-key.pem:/run/secrets', before_worker)

    def test_build_override_requires_digest_pinned_python_base(self) -> None:
        override = (ROOT / 'trust-ci/compose.build.yaml').read_text(encoding='utf-8')
        self.assertIn('PYTHON_BASE_IMAGE', override)
        self.assertIn('immutable Python base image', override)
        for name in ('Dockerfile.api', 'Dockerfile.worker', 'runner.Dockerfile', 'Dockerfile.test'):
            text = (ROOT / 'trust-ci' / name).read_text(encoding='utf-8')
            self.assertTrue(text.startswith('ARG PYTHON_BASE_IMAGE\nFROM ${PYTHON_BASE_IMAGE}'), name)

    def test_runner_tools_and_build_backend_are_exactly_pinned(self) -> None:
        runner = (ROOT / 'trust-ci/runner.Dockerfile').read_text(encoding='utf-8')
        for pin in ('coverage==7.15.4', 'ruff==0.16.2', 'bandit==1.9.4', 'tomli==2.4.1'):
            self.assertIn(pin, runner)
        pyproject = (ROOT / 'trust-ci/pyproject.toml').read_text(encoding='utf-8')
        self.assertIn('setuptools==84.0.0', pyproject)
        self.assertNotIn('setuptools>=', pyproject)

    def test_example_holdout_digest_matches_example_bundle(self) -> None:
        import json

        policy = json.loads((ROOT / 'trust-ci/config/policy.example.json').read_text(encoding='utf-8'))
        self.assertEqual(policy['holdout']['digest'], bundle_digest(ROOT / 'trust-ci/holdout.example'))
        self.assertEqual(policy['holdout']['path'], '/etc/adaptive-trust-ci/holdout')

    def test_branch_protection_is_app_bound_and_actions_independent(self) -> None:
        payload = branch_protection_payload('adaptive-trust-ci/verified', app_id=12345)
        self.assertEqual(
            payload['required_status_checks']['checks'],
            [{'context': 'adaptive-trust-ci/verified', 'app_id': 12345}],
        )
        self.assertNotIn('actions', str(payload).lower())

    def test_backup_timer_and_restore_drill_are_explicit(self) -> None:
        service = (ROOT / 'trust-ci/systemd/adaptive-trust-ci-backup.service').read_text(encoding='utf-8')
        timer = (ROOT / 'trust-ci/systemd/adaptive-trust-ci-backup.timer').read_text(encoding='utf-8')
        self.assertIn('backup-create', service)
        self.assertIn('TRUST_CI_BACKUP_DIR', service)
        self.assertIn('Persistent=true', timer)
        self.assertIn('OnCalendar=', timer)
        script = (ROOT / 'trust-ci/scripts/restore-drill.sh').read_text(encoding='utf-8')
        self.assertIn('--confirm-disposable', script)
        self.assertIn('backup-verify', script)

    def test_postgres_integration_runner_cleans_up_after_itself(self) -> None:
        script = (ROOT / 'trust-ci/scripts/postgres-integration.sh').read_text(encoding='utf-8')
        self.assertIn('compose.test.yaml', script)
        self.assertIn('down --volumes --remove-orphans', script)
        self.assertIn('trap cleanup EXIT', script)

    def test_postgres_restart_drill_uses_named_volume_and_container_restart(self) -> None:
        compose = (ROOT / 'trust-ci/compose.test.yaml').read_text(encoding='utf-8')
        script = (ROOT / 'trust-ci/scripts/postgres-restart-drill.sh').read_text(encoding='utf-8')
        self.assertIn('trust-ci-pgtest-data:/var/lib/postgresql/data', compose)
        self.assertNotIn('tmpfs:', compose)
        self.assertIn('compose restart postgres-test', script)
        self.assertIn('postgres_restart_probe seed', script)
        self.assertIn('postgres_restart_probe verify', script)

    def test_repository_contains_no_github_actions_workflow(self) -> None:
        workflows = ROOT / '.github' / 'workflows'
        self.assertFalse(workflows.exists(), 'GitHub Actions are forbidden for this project')


if __name__ == '__main__':
    unittest.main()
