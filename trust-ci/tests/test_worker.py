from __future__ import annotations

import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from _support import now, policy_data, sha
from adaptive_trust_ci.models import JobRequest
from adaptive_trust_ci.policy import PolicyCatalog
from adaptive_trust_ci.settings import CommonSettings, WorkerSettings
from adaptive_trust_ci.store import MemoryStore
from adaptive_trust_ci.worker import Worker


class RecordingRunner:
    def __init__(self, policy, calls):
        self.policy = policy
        self.calls = calls

    def process(self, job, worker_id):
        self.calls.append((job.job_id, worker_id, self.policy))


class WorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        common = policy_data()
        common.pop('allowed_repositories')
        common.pop('commands')
        common.pop('holdout')
        data = {
            **common,
            'repository_profiles': [
                {
                    'repository': 'Dimkox/adaptive-grok-build-pro',
                    'commands': policy_data()['commands'],
                    'holdout': {**policy_data(holdout_digest='a' * 64)['holdout'], 'host_path': '/srv/holdouts/adaptive-grok-build-pro'},
                },
                {
                    'repository': 'Dimkox/ii-tonya-platform',
                    'commands': [{'name': 'platform-unit', 'argv': ['pytest'], 'timeout_seconds': 120, 'required': True}],
                    'holdout': {**policy_data(holdout_digest='b' * 64)['holdout'], 'host_path': '/srv/holdouts/ii-tonya-platform'},
                },
            ],
        }
        self.catalog = PolicyCatalog.from_dict(data)
        self.settings = WorkerSettings(
            common=CommonSettings('postgresql://unused', Path('/tmp/policy'), 'https://ci.example.com', Path('/tmp/stop')),
            ci_signing_key_path=Path('/tmp/signing'), github_app_id=1, github_installation_id=2,
            github_app_private_key_path=Path('/tmp/app'), runner_image='runner@sha256:' + 'a' * 64,
            workspace_root=Path('/tmp/workspaces'), workspace_host_root=Path('/tmp/host'),
            holdout_host_path=Path('/tmp/holdout'), holdout_path=Path('/tmp/holdout'), worker_id='worker', poll_interval_seconds=0.1,
        )

    def _job(self, repository: str, digest: str):
        store = MemoryStore()
        request = JobRequest(repository, 15, sha('a'), sha('b'), 'feat/x', 'main')
        job, _ = store.enqueue(request, digest, 3, now=now())
        return store, job

    def test_dispatches_each_job_to_its_bound_profile(self) -> None:
        calls = []
        factory = lambda policy: RecordingRunner(policy, calls)
        store = MemoryStore()
        for index, repository in enumerate(('Dimkox/adaptive-grok-build-pro', 'Dimkox/ii-tonya-platform')):
            request = JobRequest(repository, 15, sha('a'), sha(str(index + 2)), 'feat/x', 'main')
            store.enqueue(request, self.catalog.resolve_repository(repository).digest, 3, now=now())
        worker = Worker(self.settings, store, self.catalog, factory, threading.Event())
        worker.run(once=True)
        worker.run(once=True)
        self.assertEqual([item[2] for item in calls], [
            self.catalog.resolve_repository('Dimkox/adaptive-grok-build-pro'),
            self.catalog.resolve_repository('Dimkox/ii-tonya-platform'),
        ])

    def test_stale_binding_finishes_without_runner_or_retry(self) -> None:
        store, job = self._job('Dimkox/adaptive-grok-build-pro', self.catalog.resolve_repository('Dimkox/adaptive-grok-build-pro').digest)
        changed = policy_data()
        changed['max_attempts'] = 4
        changed_catalog = PolicyCatalog.from_policy(__import__('adaptive_trust_ci.policy', fromlist=['Policy']).Policy.from_dict(changed))
        calls = []
        worker = Worker(self.settings, store, changed_catalog, lambda policy: RecordingRunner(policy, calls), threading.Event())
        worker.run(once=True)
        result = store.get_job(job.job_id)
        self.assertEqual(calls, [])
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure_code, 'policy-binding-unavailable')
        self.assertEqual(result.result['job_policy_digest'], job.policy_digest)

    def test_runner_factory_receives_profile_host_path(self) -> None:
        paths = []
        def factory(policy):
            paths.append(policy.holdout.host_path)
            return RecordingRunner(policy, [])
        store, _ = self._job('Dimkox/ii-tonya-platform', self.catalog.resolve_repository('Dimkox/ii-tonya-platform').digest)
        Worker(self.settings, store, self.catalog, factory, threading.Event()).run(once=True)
        self.assertEqual(paths, [Path('/srv/holdouts/ii-tonya-platform')])

    def test_catalog_holdouts_must_match_strict_paired_trusted_roots(self) -> None:
        settings = SimpleNamespace(
            holdout_path=Path('/srv/local-holdouts'),
            holdout_host_path=Path('/srv/daemon-holdouts'),
        )
        valid = self.catalog_data_with_paths('/srv/local-holdouts/adaptive-grok-build-pro', '/srv/daemon-holdouts/adaptive-grok-build-pro')
        Worker._validate_catalog_paths(settings, valid)
        for local, host in (
            ('/srv/local-holdouts', '/srv/daemon-holdouts/adaptive-grok-build-pro'),
            ('/srv/local-holdouts/../other/adaptive-grok-build-pro', '/srv/daemon-holdouts/adaptive-grok-build-pro'),
            ('/srv/local-holdouts/adaptive-grok-build-pro', '/srv/other/adaptive-grok-build-pro'),
        ):
            with self.assertRaisesRegex(Exception, 'holdout'):
                data = self.catalog_data_with_paths(local, host)
                Worker._validate_catalog_paths(settings, data)

    def catalog_data_with_paths(self, local: str, host: str) -> PolicyCatalog:
        data = {
            'schema_version': 1, 'status_context': 'adaptive-trust-ci/verified', 'pipeline': 'pull_request',
            'checkout_depth': 100, 'lease_seconds': 90, 'max_attempts': 3,
            'max_approval_ttl_seconds': 1800, 'max_output_bytes': 20000, 'allowed_environment': [],
            'sandbox': {'runtime': 'docker', 'image': 'runner@sha256:' + 'a' * 64, 'user': '10001:10001', 'memory_mb': 1024, 'cpus': 1.0, 'pids_limit': 128, 'tmpfs_mb': 256},
            'approval_rules': [], 'repository_profiles': [
                {'repository': 'Dimkox/adaptive-grok-build-pro', 'commands': policy_data()['commands'],
                 'holdout': {**policy_data()['holdout'], 'path': local, 'host_path': host}},
            ],
        }
        return PolicyCatalog.from_dict(data)


if __name__ == '__main__':
    unittest.main()
