from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from _support import ROOT, policy_data, sha
from adaptive_trust_ci import cli
from adaptive_trust_ci.models import ApprovalEnvelope
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.signing import Signer, TrustStore, verify_approval


SERVER_IMPORTS = (
    'adaptive_trust_ci.api',
    'adaptive_trust_ci.backup',
    'adaptive_trust_ci.github',
    'adaptive_trust_ci.github_app',
    'adaptive_trust_ci.holdout',
    'adaptive_trust_ci.migrations',
    'adaptive_trust_ci.settings',
    'adaptive_trust_ci.store',
    'adaptive_trust_ci.worker',
    'fastapi',
    'psycopg',
    'uvicorn',
)


class TrackingModule(types.ModuleType):
    def __init__(self, name: str, imported: set[str]) -> None:
        super().__init__(name)
        self._imported = imported

    def __getattribute__(self, name: str) -> object:
        if not name.startswith('_'):
            imported = types.ModuleType.__getattribute__(self, '_imported')
            imported.add(types.ModuleType.__getattribute__(self, '__name__'))
        return types.ModuleType.__getattribute__(self, name)


class SerializableResult:
    def to_dict(self) -> dict[str, bool]:
        return {'ok': True}


class MigrationPlan:
    applied: tuple[str, ...] = ()
    pending: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, list[str]]:
        return {'applied': [], 'pending': []}


class CommandBranchImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        self.fixture_json = self.workspace / 'fixture.json'
        self.fixture_json.write_text('{}\n', encoding='utf-8')

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_every_relocated_non_human_command_imports_only_its_slice_and_reaches_safe_effect(self) -> None:
        path = str(self.fixture_json)
        cases = (
            ('api', ['api'], {'uvicorn', 'adaptive_trust_ci.api', 'adaptive_trust_ci.settings'}, 'uvicorn.run'),
            ('worker', ['worker', '--once'], {'adaptive_trust_ci.settings', 'adaptive_trust_ci.worker'}, 'worker.run'),
            (
                'migrate',
                ['migrate'],
                {'adaptive_trust_ci.migrations', 'adaptive_trust_ci.settings'},
                'migrator.apply',
            ),
            (
                'migration-status',
                ['migration-status'],
                {'adaptive_trust_ci.migrations', 'adaptive_trust_ci.settings'},
                'migrator.status',
            ),
            (
                'policy-digest',
                ['policy-digest'],
                {'adaptive_trust_ci.policy', 'adaptive_trust_ci.settings'},
                'policy.load',
            ),
            ('holdout-digest', ['holdout-digest', '--path', path], {'adaptive_trust_ci.holdout'}, 'holdout.digest'),
            (
                'doctor',
                ['doctor'],
                {
                    'adaptive_trust_ci.github_app',
                    'adaptive_trust_ci.holdout',
                    'adaptive_trust_ci.migrations',
                    'adaptive_trust_ci.models',
                    'adaptive_trust_ci.policy',
                    'adaptive_trust_ci.settings',
                    'adaptive_trust_ci.signing',
                    'adaptive_trust_ci.store',
                },
                'store.ping',
            ),
            (
                'keygen',
                ['keygen', '--private', str(self.workspace / 'unused-private.pem'), '--public', str(self.workspace / 'unused-public.pem')],
                {'adaptive_trust_ci.signing'},
                'signer.write_keypair',
            ),
            (
                'trust-store-validate',
                ['trust-store-validate', '--trust-store', path],
                {'adaptive_trust_ci.models', 'adaptive_trust_ci.signing'},
                'trust-store.report',
            ),
            (
                'approval-verify',
                [
                    'approval-verify',
                    '--approval',
                    path,
                    '--trust-store',
                    path,
                    '--policy',
                    path,
                    '--repository',
                    'Dimkox/adaptive-grok-build-pro',
                    '--pr-number',
                    '11',
                    '--base-sha',
                    sha('b'),
                    '--head-sha',
                    sha('c'),
                ],
                {'adaptive_trust_ci.models', 'adaptive_trust_ci.policy', 'adaptive_trust_ci.signing'},
                'approval.verify',
            ),
            (
                'attestation-verify',
                ['attestation-verify', '--attestation', path, '--public-key', path],
                {'adaptive_trust_ci.models', 'adaptive_trust_ci.signing'},
                'attestation.verify',
            ),
            (
                'branch-protect',
                [
                    'branch-protect',
                    '--repository',
                    'Dimkox/adaptive-grok-build-pro',
                    '--policy',
                    path,
                    '--app-id',
                    '4694114',
                ],
                {'adaptive_trust_ci.github', 'adaptive_trust_ci.policy'},
                'github.configure_branch_protection',
            ),
            (
                'backup-create',
                ['backup-create', '--output-dir', str(self.workspace), '--database-label', 'test-only'],
                {'adaptive_trust_ci.backup', 'adaptive_trust_ci.settings'},
                'backup.create',
            ),
            (
                'backup-verify',
                ['backup-verify', '--dump', path, '--manifest', path],
                {'adaptive_trust_ci.backup'},
                'backup.verify',
            ),
            (
                'backup-prune',
                ['backup-prune', '--directory', str(self.workspace)],
                {'adaptive_trust_ci.backup'},
                'backup.prune',
            ),
            (
                'restore-drill',
                ['restore-drill', '--dump', path, '--manifest', path, '--confirm-disposable'],
                {'adaptive_trust_ci.backup'},
                'backup.restore',
            ),
            (
                'kill-switch',
                ['kill-switch', 'status'],
                {'adaptive_trust_ci.models', 'adaptive_trust_ci.settings'},
                'settings.common.load',
            ),
        )

        for name, arguments, expected_imports, expected_effect in cases:
            with self.subTest(command=name):
                imported: set[str] = set()
                effects: list[str] = []
                fake_modules = self._fake_modules(imported, effects)
                environment = {
                    'TRUST_CI_ROLE': 'none',
                    'TRUST_CI_GITHUB_ADMIN_TOKEN': 'disposable-test-token',
                    'TRUST_CI_RESTORE_DATABASE_URL': 'postgresql://disposable.invalid/test',
                }
                stdout = StringIO()
                stderr = StringIO()
                with (
                    patch.dict(sys.modules, fake_modules),
                    patch.dict(os.environ, environment, clear=False),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    result = cli.main(arguments)

                self.assertEqual(result, 0, stderr.getvalue())
                self.assertEqual(imported, expected_imports)
                self.assertIn(expected_effect, effects)

        self.assertFalse((self.workspace / 'unused-private.pem').exists())
        self.assertFalse((self.workspace / 'unused-public.pem').exists())

    def _fake_modules(self, imported: set[str], effects: list[str]) -> dict[str, types.ModuleType]:
        def event(name: str, value: object = None) -> object:
            effects.append(name)
            return value

        policy = types.SimpleNamespace(
            digest='d' * 64,
            check_name='adaptive-trust-ci/verified@dddddddddddd',
            max_approval_ttl_seconds=900,
            holdout=types.SimpleNamespace(path=self.workspace, digest='h' * 64),
            sandbox=types.SimpleNamespace(runtime='docker', image='runner@test'),
        )
        common = types.SimpleNamespace(
            database_url='postgresql://disposable.invalid/test',
            policy_path=self.fixture_json,
            kill_switch_path=self.workspace / 'STOP',
            stopped=False,
        )
        worker_settings = types.SimpleNamespace(
            ci_signing_key_path=self.workspace / 'unused-ci-key.pem',
            runner_image='runner@test',
            github_app_id=1,
            github_app_private_key_path=self.workspace / 'unused-github-key.pem',
        )

        class FakeSigner:
            key_id = 'test-key-id'

            def write_keypair(self, private: Path, public: Path) -> None:
                event('signer.write_keypair')

        class FakeWorker:
            def run(self, *, once: bool) -> int:
                return int(event('worker.run', 0))

        class FakeMigrator:
            def apply(self) -> MigrationPlan:
                return event('migrator.apply', MigrationPlan())  # type: ignore[return-value]

            def status(self) -> MigrationPlan:
                return event('migrator.status', MigrationPlan())  # type: ignore[return-value]

        class FakeStore:
            def ping(self) -> None:
                event('store.ping')

        class FakeGitHubClient:
            def configure_branch_protection(self, *args: object, **kwargs: object) -> dict[str, bool]:
                return event('github.configure_branch_protection', {'ok': True})  # type: ignore[return-value]

        class FakeTrustStore:
            def report(self, current: datetime) -> dict[str, object]:
                event('trust-store.report')
                return {'keys': [{'status': 'active'}]}

        backup_result = types.SimpleNamespace(
            dump_path=self.workspace / 'unused.dump',
            manifest_path=self.workspace / 'unused.manifest',
            sha256='a' * 64,
            size_bytes=1,
        )
        modules: dict[str, dict[str, object]] = {
            'uvicorn': {'run': lambda *args, **kwargs: event('uvicorn.run')},
            'adaptive_trust_ci.api': {'create_app': lambda settings: event('api.create_app', object())},
            'adaptive_trust_ci.backup': {
                'create_backup': lambda *args, **kwargs: event('backup.create', backup_result),
                'verify_backup': lambda *args, **kwargs: event('backup.verify', {'ok': True}),
                'prune_backups': lambda *args, **kwargs: event('backup.prune', {'removed': []}),
                'restore_drill': lambda *args, **kwargs: event('backup.restore', {'ok': True}),
            },
            'adaptive_trust_ci.github': {'GitHubClient': lambda **kwargs: FakeGitHubClient()},
            'adaptive_trust_ci.github_app': {'generate_app_jwt': lambda *args, **kwargs: 'unused-test-jwt'},
            'adaptive_trust_ci.holdout': {
                'bundle_digest': lambda path: event('holdout.digest', 'h' * 64),
                'verify_bundle': lambda path, digest: event('holdout.verify', digest),
            },
            'adaptive_trust_ci.migrations': {'PostgresMigrator': lambda database_url: FakeMigrator()},
            'adaptive_trust_ci.models': {
                'ApprovalEnvelope': types.SimpleNamespace(from_dict=lambda data: object()),
                'AttestationEnvelope': types.SimpleNamespace(from_dict=lambda data: object()),
                'utc_now': lambda: datetime.now(timezone.utc),
            },
            'adaptive_trust_ci.policy': {
                'Policy': types.SimpleNamespace(load=lambda path: event('policy.load', policy))
            },
            'adaptive_trust_ci.settings': {
                'ApiSettings': types.SimpleNamespace(load=lambda: event('settings.api.load', object())),
                'CommonSettings': types.SimpleNamespace(load=lambda: event('settings.common.load', common)),
                'WorkerSettings': types.SimpleNamespace(load=lambda: event('settings.worker.load', worker_settings)),
            },
            'adaptive_trust_ci.signing': {
                'Signer': types.SimpleNamespace(
                    generate=lambda: event('signer.generate', FakeSigner()),
                    from_private_file=lambda path: event('signer.from_private_file', FakeSigner()),
                ),
                'TrustStore': types.SimpleNamespace(load=lambda path: event('trust-store.load', FakeTrustStore())),
                'verify_approval': lambda *args, **kwargs: event('approval.verify', SerializableResult()),
                'verify_attestation': lambda *args, **kwargs: event('attestation.verify', SerializableResult()),
            },
            'adaptive_trust_ci.store': {'PostgresStore': lambda database_url: FakeStore()},
            'adaptive_trust_ci.worker': {
                'Worker': types.SimpleNamespace(build=lambda settings: event('worker.build', FakeWorker())),
                'install_signal_handlers': lambda worker: event('worker.install_signal_handlers'),
            },
        }
        fake_modules: dict[str, types.ModuleType] = {}
        for name, attributes in modules.items():
            module = TrackingModule(name, imported)
            for attribute, value in attributes.items():
                setattr(module, attribute, value)
            fake_modules[name] = module
        return fake_modules


class HumanApprovalCliIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        self.guard_directory = self.workspace / 'import-guard'
        self.guard_directory.mkdir()
        (self.guard_directory / 'sitecustomize.py').write_text(
            """\
import importlib.abc
import os
import sys

blocked = tuple(filter(None, os.environ['TRUST_CI_TEST_BLOCKED_IMPORTS'].split(',')))

class BlockedImportFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == prefix or fullname.startswith(prefix + '.') for prefix in blocked):
            raise ImportError(f'blocked server-only import: {fullname}')
        return None

sys.meta_path.insert(0, BlockedImportFinder())
""",
            encoding='utf-8',
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_human_command_help_is_stdlib_only(self) -> None:
        blocked_imports = (*SERVER_IMPORTS, 'cryptography')
        for arguments in (('--help',), ('approval-create', '--help'), ('approval-submit', '--help')):
            with self.subTest(arguments=arguments):
                result = self._run_cli(*arguments, blocked_imports=blocked_imports)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_approval_create_runs_without_server_imports_and_preserves_envelope_contract(self) -> None:
        signer = Signer.generate()
        private_key = self.workspace / 'ephemeral-test-key.pem'
        private_key.write_bytes(signer.private_key_pem())
        os.chmod(private_key, 0o600)
        policy_document = policy_data()
        policy_path = self.workspace / 'policy.json'
        policy_path.write_text(json.dumps(policy_document), encoding='utf-8')
        output_path = self.workspace / 'governance-approval.json'

        result = self._run_cli(
            'approval-create',
            '--private-key',
            str(private_key),
            '--policy',
            str(policy_path),
            '--actor',
            'test-human',
            '--repository',
            'Dimkox/adaptive-grok-build-pro',
            '--pr-number',
            '11',
            '--base-sha',
            sha('b'),
            '--head-sha',
            sha('c'),
            '--scope',
            'governance',
            '--reason',
            'Disposable regression test approval',
            '--ttl',
            '900',
            '--output',
            str(output_path),
            blocked_imports=SERVER_IMPORTS,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(output_path.stat().st_mode), 0o600)
        envelope = ApprovalEnvelope.from_dict(json.loads(output_path.read_text(encoding='utf-8')))
        policy = Policy.from_dict(policy_document)
        verified = verify_approval(
            envelope,
            TrustStore.from_dict(
                {
                    'schema_version': 1,
                    'keys': [
                        {
                            'key_id': signer.key_id,
                            'actor': 'test-human',
                            'public_key_pem': signer.public_key_pem().decode('ascii'),
                            'scopes': ['governance'],
                        }
                    ],
                }
            ),
            expected_repository='Dimkox/adaptive-grok-build-pro',
            expected_pr_number=11,
            expected_base_sha=sha('b'),
            expected_head_sha=sha('c'),
            expected_policy_digest=policy.digest,
            now=datetime.now(timezone.utc),
            max_ttl_seconds=policy.max_approval_ttl_seconds,
        )
        self.assertEqual(verified.scope, 'governance')
        self.assertEqual(verified.policy_digest, policy.digest)

    def test_approval_submit_posts_exact_bytes_without_server_or_crypto_imports(self) -> None:
        approval_bytes = b'{"payload":{"fixture":true},"signature":"not-a-production-signature"}\n'
        approval_path = self.workspace / 'fixture-approval.json'
        approval_path.write_bytes(approval_bytes)
        received: dict[str, object] = {}

        class ApprovalHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                size = int(self.headers['Content-Length'])
                received.update(
                    path=self.path,
                    content_type=self.headers['Content-Type'],
                    user_agent=self.headers['User-Agent'],
                    body=self.rfile.read(size),
                )
                response = b'{"accepted":true,"requeued_jobs":1}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(('127.0.0.1', 0), ApprovalHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            result = self._run_cli(
                'approval-submit',
                '--approval',
                str(approval_path),
                '--url',
                f'http://127.0.0.1:{server.server_port}',
                blocked_imports=(*SERVER_IMPORTS, 'cryptography'),
            )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(received['path'], '/approvals')
        self.assertEqual(received['content_type'], 'application/json')
        self.assertEqual(received['user_agent'], 'adaptive-trust-ci-human/2.1.0')
        self.assertEqual(received['body'], approval_bytes)
        self.assertEqual(json.loads(result.stdout), {'accepted': True, 'requeued_jobs': 1})

    def _run_cli(self, *arguments: str, blocked_imports: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        python_path = [str(self.guard_directory), str(ROOT / 'trust-ci' / 'src')]
        if environment.get('PYTHONPATH'):
            python_path.append(environment['PYTHONPATH'])
        environment['PYTHONPATH'] = os.pathsep.join(python_path)
        environment['TRUST_CI_TEST_BLOCKED_IMPORTS'] = ','.join(blocked_imports)
        for proxy_variable in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
            environment.pop(proxy_variable, None)
        environment['NO_PROXY'] = '127.0.0.1,localhost'
        environment['no_proxy'] = environment['NO_PROXY']
        return subprocess.run(
            [sys.executable, '-m', 'adaptive_trust_ci.cli', *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


if __name__ == '__main__':
    unittest.main()
