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
                workspace_host_path=Path('/srv/adaptive-trust-ci/workspaces/job-1'),
                command=('python3', '/holdout/validate.py', '/workspace'),
                env={'CI': 'true', 'TRUST_CI_HEAD_SHA': 'b' * 40},
                container_name='trust-ci-test',
                holdout_path=holdout,
                holdout_host_path=Path('/srv/adaptive-trust-ci/holdout'),
            )
        joined = ' '.join(argv)
        self.assertIn('--network none', joined)
        self.assertIn('--cap-drop ALL', joined)
        self.assertIn('no-new-privileges', joined)
        self.assertIn('--read-only', joined)
        self.assertIn('/srv/adaptive-trust-ci/workspaces/job-1:/workspace:rw', joined)
        self.assertIn('/srv/adaptive-trust-ci/workspaces/job-1/.git:/workspace/.git:ro', joined)
        self.assertIn('/srv/adaptive-trust-ci/holdout:/holdout:ro', joined)
        self.assertNotIn(str(workspace), joined)
        self.assertNotIn('GITHUB_TOKEN', joined)
        self.assertNotIn('TRUST_CI_GITHUB', joined)

    def test_sandbox_rejects_relative_daemon_host_paths(self) -> None:
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

    def test_packaged_schema_matches_deployment_schema(self) -> None:
        deployment = (ROOT / 'trust-ci/sql/001_schema.sql').read_bytes()
        packaged = (ROOT / 'trust-ci/src/adaptive_trust_ci/resources/001_schema.sql').read_bytes()
        self.assertEqual(deployment, packaged)

    def test_production_compose_uses_prebuilt_images_and_explicit_host_binds(self) -> None:
        compose = (ROOT / 'trust-ci/compose.yaml').read_text(encoding='utf-8')
        self.assertNotIn('build:', compose)
        self.assertIn('TRUST_CI_POSTGRES_IMAGE:?', compose)
        self.assertIn('TRUST_CI_API_IMAGE:?', compose)
        self.assertIn('TRUST_CI_WORKER_IMAGE:?', compose)
        worker = compose.split('  worker:', 1)[1]
        before_worker = compose.split('  worker:', 1)[0]
        self.assertIn('github-app-private-key.pem:/run/secrets', worker)
        self.assertIn('TRUST_CI_HOLDOUT_HOST_PATH:?', worker)
        self.assertIn('TRUST_CI_WORKSPACE_HOST_ROOT:?', worker)
        self.assertIn('docker.sock', worker)
        self.assertNotIn('trust-ci-workspaces:', compose)
        self.assertNotIn('github-app-private-key.pem:/run/secrets', before_worker)
        self.assertNotIn('docker.sock', before_worker)

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
        self.assertEqual(
            policy['holdout']['digest'],
            bundle_digest(ROOT / 'trust-ci/holdout.example'),
        )
        self.assertEqual(policy['holdout']['path'], '/etc/adaptive-trust-ci/holdout')

    def test_branch_protection_is_app_bound_and_actions_independent(self) -> None:
        payload = branch_protection_payload('adaptive-trust-ci/verified', app_id=12345)
        self.assertEqual(
            payload['required_status_checks']['checks'],
            [{'context': 'adaptive-trust-ci/verified', 'app_id': 12345}],
        )
        self.assertNotIn('actions', str(payload).lower())

    def test_repository_contains_no_github_actions_workflow(self) -> None:
        workflows = ROOT / '.github' / 'workflows'
        self.assertFalse(workflows.exists(), 'GitHub Actions are forbidden for this project')


if __name__ == '__main__':
    unittest.main()
