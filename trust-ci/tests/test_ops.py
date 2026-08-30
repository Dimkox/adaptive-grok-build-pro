from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import stat
import tempfile
import tomllib
import unittest
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from _support import policy_data
import adaptive_trust_ci.cli as cli_module
from adaptive_trust_ci.github import branch_protection_payload
from adaptive_trust_ci.holdout import bundle_digest
from adaptive_trust_ci.cli import NoPromotionRedirects, main
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.sandbox import ContainerExecutor
from adaptive_trust_ci.signing import Signer


ROOT = Path(__file__).resolve().parents[2]


class OperationsTests(unittest.TestCase):
    def promotion_fixture(self, directory: Path) -> tuple[list[str], Path, Path, dict]:
        signer = Signer.generate()
        private_key = directory / 'ephemeral-fixture-private.pem'
        public_key = directory / 'ephemeral-fixture-public.pem'
        signer.write_keypair(private_key, public_key)
        trust_store = directory / 'fixture-trust-store.json'
        trust_store.write_text(
            json.dumps(
                {
                    'schema_version': 1,
                    'keys': [{
                        'key_id': signer.key_id,
                        'actor': 'fixture-human',
                        'scopes': ['promotion:production'],
                        'public_key_pem': public_key.read_text(encoding='utf-8'),
                    }],
                }
            ),
            encoding='utf-8',
        )
        current = datetime.now(timezone.utc).replace(microsecond=0)
        values = {
            'schema_version': 1,
            'promotion_id': str(uuid.uuid4()),
            'nonce': base64.urlsafe_b64encode(b't' * 32).decode().rstrip('='),
            'actor': 'fixture-human',
            'key_id': signer.key_id,
            'repository': 'dimkox/adaptive-grok-build-pro',
            'merged_commit_sha': 'a' * 40,
            'artifact_sha256': 'b' * 64,
            'target_environment': 'production',
            'policy_epoch': 'c' * 64,
            'source_attestation_id': str(uuid.uuid4()),
            'reason': 'Ephemeral CLI regression fixture',
            'issued_at': current.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'expires_at': (current + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        output = directory / 'promotion-envelope.json'
        argv = ['promotion-create', '--private-key', str(private_key), '--output', str(output)]
        for key, value in values.items():
            argv.extend(('--' + key.replace('_', '-'), str(value)))
        return argv, output, trust_store, values

    def test_promotion_create_and_verify_are_offline_file_only_and_secret_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            create_argv, envelope_path, trust_store, values = self.promotion_fixture(directory)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch('adaptive_trust_ci.cli.urllib.request.urlopen') as network, \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(create_argv), 0)
            network.assert_not_called()
            self.assertEqual(stat.S_IMODE(envelope_path.stat().st_mode), 0o600)
            envelope = json.loads(envelope_path.read_text(encoding='utf-8'))
            self.assertNotIn(envelope['signature'], stdout.getvalue())
            self.assertNotIn('PRIVATE KEY', stdout.getvalue() + stderr.getvalue())

            verify_argv = [
                'promotion-verify', '--promotion', str(envelope_path),
                '--trust-store', str(trust_store), '--max-ttl-seconds', '900',
            ]
            for key in (
                'repository', 'merged_commit_sha', 'artifact_sha256',
                'target_environment', 'policy_epoch', 'source_attestation_id',
            ):
                verify_argv.extend(('--' + key.replace('_', '-'), values[key]))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(verify_argv), 0)
            self.assertNotIn(envelope['signature'], stdout.getvalue())

    def test_promotion_create_rejects_environment_or_literal_private_keys(self) -> None:
        literal = '-----BEGIN ' + 'PRIVATE KEY-----fixture-secret-----END PRIVATE KEY-----'
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            argv, _, _, _ = self.promotion_fixture(directory)
            private_index = argv.index('--private-key') + 1
            argv[private_index] = literal
            stderr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(argv), 2)
            self.assertNotIn('fixture-secret', stderr.getvalue())
            without_key = argv[:private_index - 1] + argv[private_index + 1:]
            with mock.patch.dict(os.environ, {'TRUST_CI_PROMOTION_PRIVATE_KEY': literal}), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(without_key)
            self.assertEqual(caught.exception.code, 2)

    def test_promotion_create_requires_owned_0600_nonsymlink_private_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            argv, output, _, _ = self.promotion_fixture(directory)
            key_index = argv.index('--private-key') + 1
            private_key = Path(argv[key_index])

            private_key.chmod(0o644)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(argv), 2)
            self.assertFalse(output.exists())

            private_key.chmod(0o600)
            symlink = directory / 'private-key-link.pem'
            symlink.symlink_to(private_key)
            argv[key_index] = str(symlink)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(argv), 2)
            self.assertFalse(output.exists())

    def test_promotion_create_rejects_expired_or_overlong_authority(self) -> None:
        current = datetime.now(timezone.utc).replace(microsecond=0)
        invalid_windows = (
            (
                (current - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                (current - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            ),
            (
                current.strftime('%Y-%m-%dT%H:%M:%SZ'),
                (current + timedelta(seconds=3601)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            ),
        )
        for issued_at, expires_at in invalid_windows:
            with self.subTest(issued_at=issued_at, expires_at=expires_at), \
                    tempfile.TemporaryDirectory() as directory_name:
                argv, envelope_path, _, _ = self.promotion_fixture(Path(directory_name))
                argv[argv.index('--issued-at') + 1] = issued_at
                argv[argv.index('--expires-at') + 1] = expires_at
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(argv), 2)
                self.assertFalse(envelope_path.exists())

    def test_promotion_submit_has_stable_exit_mapping_and_bounded_request(self) -> None:
        class Response:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, amount=-1):
                body = json.dumps(
                    {
                        'promotion_id': 'fixture',
                        'correlation_id': 'corr',
                        'consumed': False,
                        'token': 'server-' + 'secret',
                        'signature': 'signed-envelope-secret',
                        'envelope': 'raw-envelope-secret',
                    },
                    separators=(',', ':'),
                ).encode('utf-8')
                return body if amount < 0 else body[:amount]

        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            create_argv, envelope_path, _, _ = self.promotion_fixture(directory)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(create_argv), 0)
            submit = [
                'promotion-submit', '--promotion', str(envelope_path),
                '--url', 'https://ci.example.com',
                '--idempotency-key', 'explicit-idempotency-0001',
                '--correlation-id', 'explicit-correlation-0001',
                '--timeout-seconds', '5',
            ]
            stdout = io.StringIO()
            with mock.patch('adaptive_trust_ci.cli._open_promotion_request', return_value=Response()) as opened, \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(submit), 0)
            request = opened.call_args.args[0]
            self.assertEqual(request.get_header('Idempotency-key'), 'explicit-idempotency-0001')
            self.assertEqual(request.get_header('X-correlation-id'), 'explicit-correlation-0001')
            self.assertEqual(opened.call_args.kwargs['timeout'], 5)
            self.assertEqual(request.data, envelope_path.read_bytes())
            self.assertNotIn('server-secret', stdout.getvalue())
            self.assertNotIn('signed-envelope-secret', stdout.getvalue())
            self.assertNotIn('raw-envelope-secret', stdout.getvalue())

            for failure, expected in (
                (urllib.error.HTTPError(submit[4], 403, 'forbidden', {}, io.BytesIO(b'{"code":"signature_invalid"}')), 3),
                (urllib.error.HTTPError(submit[4], 409, 'conflict', {}, io.BytesIO(b'{"code":"promotion_replay"}')), 4),
                (urllib.error.HTTPError(submit[4], 503, 'unavailable', {}, io.BytesIO(b'{"code":"authorization_unavailable"}')), 5),
                (urllib.error.URLError('network unavailable'), 5),
            ):
                with self.subTest(expected=expected), \
                        mock.patch('adaptive_trust_ci.cli._open_promotion_request', side_effect=failure), \
                        contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(submit), expected)
            insecure = [*submit]
            insecure[insecure.index('https://ci.example.com')] = 'http://ci.example.com'
            with mock.patch('adaptive_trust_ci.cli._open_promotion_request') as opened, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(insecure), 2)
            opened.assert_not_called()

            class OversizeResponse(Response):
                def read(self, amount=-1):
                    return b'x' * amount

            with mock.patch(
                'adaptive_trust_ci.cli._open_promotion_request', return_value=OversizeResponse()
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(submit), 5)

    def test_promotion_submit_rejects_duplicate_envelope_fields_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            create_argv, envelope_path, _, _ = self.promotion_fixture(directory)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(create_argv), 0)
            raw = envelope_path.read_text(encoding='utf-8')
            envelope_path.write_text(raw.replace('{', '{"algorithm":"Ed25519",', 1), encoding='utf-8')
            submit = [
                'promotion-submit', '--promotion', str(envelope_path),
                '--url', 'https://ci.example.com',
                '--idempotency-key', 'explicit-idempotency-0001',
                '--correlation-id', 'explicit-correlation-0001',
            ]
            with mock.patch('adaptive_trust_ci.cli._open_promotion_request') as opened, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(submit), 2)
            opened.assert_not_called()

    def test_promotion_envelope_inputs_reject_symlink_fifo_device_and_oversize(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            create_argv, envelope_path, trust_store, values = self.promotion_fixture(directory)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(create_argv), 0)
            symlink = directory / 'promotion-link.json'
            symlink.symlink_to(envelope_path)
            fifo = directory / 'promotion.fifo'
            os.mkfifo(fifo)
            oversized = directory / 'oversized.json'
            oversized.write_bytes(b'x' * (16 * 1024 + 1))

            verify = [
                'promotion-verify', '--promotion', str(symlink),
                '--trust-store', str(trust_store), '--max-ttl-seconds', '900',
            ]
            for key in (
                'repository', 'merged_commit_sha', 'artifact_sha256',
                'target_environment', 'policy_epoch', 'source_attestation_id',
            ):
                verify.extend(('--' + key.replace('_', '-'), values[key]))
            submit = [
                'promotion-submit', '--promotion', str(symlink),
                '--url', 'https://ci.example.com',
                '--idempotency-key', 'explicit-idempotency-0001',
                '--correlation-id', 'explicit-correlation-0001',
            ]
            with mock.patch('adaptive_trust_ci.cli._open_promotion_request') as opened:
                for candidate in (symlink, fifo, Path('/dev/null'), oversized):
                    with self.subTest(candidate=candidate), \
                            contextlib.redirect_stdout(io.StringIO()), \
                            contextlib.redirect_stderr(io.StringIO()):
                        submit[submit.index('--promotion') + 1] = str(candidate)
                        self.assertEqual(main(submit), 2)
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(verify), 2)
            opened.assert_not_called()

    def test_descriptor_read_remains_bound_when_path_is_replaced_after_open(self) -> None:
        self.assertTrue(hasattr(cli_module, '_read_secure_regular_file'))
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / 'envelope.json'
            replacement = Path(directory_name) / 'replacement.json'
            path.write_bytes(b'original-envelope')
            replacement.write_bytes(b'replaced-path')
            real_open = os.open

            def open_then_replace(candidate, flags):
                descriptor = real_open(candidate, flags)
                if Path(candidate) == path:
                    os.replace(replacement, path)
                return descriptor

            with mock.patch('adaptive_trust_ci.cli.os.open', side_effect=open_then_replace):
                self.assertEqual(
                    cli_module._read_secure_regular_file(path, 1024),
                    b'original-envelope',
                )

    def test_promotion_submit_never_forwards_envelope_through_redirect(self) -> None:
        redirect = NoPromotionRedirects()
        request = urllib.request.Request(
            'https://ci.example.com/promotions',
            data=b'bounded-envelope',
            method='POST',
        )
        self.assertIsNone(
            redirect.redirect_request(
                request,
                io.BytesIO(),
                307,
                'temporary redirect',
                {},
                'http://attacker.example/promotions',
            )
        )

    def test_promotion_submit_is_https_only_and_disables_environment_proxies(self) -> None:
        class Response:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, amount=-1):
                return b'{"status":"accepted"}'

        class Opener:
            def open(self, _request, *, timeout):
                self.timeout = timeout
                return Response()

        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            create_argv, envelope_path, _, _ = self.promotion_fixture(directory)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(create_argv), 0)
            submit = [
                'promotion-submit', '--promotion', str(envelope_path),
                '--url', 'https://ci.example.com',
                '--idempotency-key', 'explicit-idempotency-0001',
                '--correlation-id', 'explicit-correlation-0001',
            ]
            captured_handlers = []

            def build_opener(*handlers):
                captured_handlers.extend(handlers)
                return Opener()

            proxy_env = {
                'HTTP_PROXY': 'http://proxy.invalid:8080',
                'HTTPS_PROXY': 'http://proxy.invalid:8080',
                'NO_PROXY': '',
            }
            with mock.patch.dict(os.environ, proxy_env, clear=False), \
                    mock.patch(
                        'adaptive_trust_ci.cli.urllib.request.build_opener',
                        side_effect=build_opener,
                    ), contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(submit), 0)
            explicit_proxy_handlers = [
                handler for handler in captured_handlers
                if isinstance(handler, urllib.request.ProxyHandler)
            ]
            self.assertEqual(len(explicit_proxy_handlers), 1)
            self.assertEqual(explicit_proxy_handlers[0].proxies, {})

            plaintext = [*submit]
            plaintext[plaintext.index('https://ci.example.com')] = 'http://localhost:8080'
            with mock.patch('adaptive_trust_ci.cli._open_promotion_request') as opened, \
                    mock.patch('socket.getaddrinfo') as resolved, \
                    contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(plaintext), 2)
            opened.assert_not_called()
            resolved.assert_not_called()

            with contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as caught:
                main([*plaintext, '--allow-http-localhost'])
            self.assertEqual(caught.exception.code, 2)

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
        self.assertIn('/run/trust-ci-tmp:rw,exec,nosuid,nodev,size=128m', joined)
        self.assertIn('TMPDIR=/run/trust-ci-tmp', argv)
        self.assertIn('PYTHONPYCACHEPREFIX=/run/trust-ci-tmp/pycache', argv)
        self.assertIn('COVERAGE_FILE=/run/trust-ci-tmp/.coverage', argv)
        self.assertIn('RUFF_CACHE_DIR=/run/trust-ci-tmp/ruff-cache', argv)
        self.assertIn('GIT_CONFIG_COUNT=1', argv)
        self.assertIn('GIT_CONFIG_KEY_0=safe.directory', argv)
        self.assertIn('GIT_CONFIG_VALUE_0=/workspace', argv)
        self.assertIn('TMPDIR=/run/trust-ci-tmp', argv)
        self.assertIn('/var/lib/adaptive-trust-ci/workspaces/job-1:/workspace:ro', joined)
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
        self.assertIn('GROK_VERIFY_CAPABILITY=repository-sandbox', argv)
        self.assertNotIn('/var/run/docker.sock', ' '.join(argv))

    def test_branch_protect_cutover_cli_requires_pair_and_delegates_exact_values(self) -> None:
        policy = mock.Mock(check_name='adaptive-trust-ci/verified@new000000000')
        command = [
            'branch-protect', '--repository', 'dimkox/adaptive-grok-build-pro',
            '--branch', 'main', '--policy', '/tmp/deployed-policy.json',
            '--app-id', '222', '--previous-context', 'adaptive-trust-ci/verified@old000000000',
            '--previous-app-id', '111',
        ]
        client = mock.Mock()
        client.cutover_branch_protection.return_value = {'ok': True}
        with mock.patch.object(Path, 'is_file', return_value=True), \
                mock.patch.object(cli_module.Policy, 'load', return_value=policy), \
                mock.patch.object(cli_module, 'GitHubClient', return_value=client), \
                mock.patch.dict(os.environ, {'TRUST_CI_GITHUB_ADMIN_TOKEN': 'short-fixture'}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(command), 0)
        client.cutover_branch_protection.assert_called_once_with(
            'dimkox/adaptive-grok-build-pro', 'main',
            old_check_name='adaptive-trust-ci/verified@old000000000', old_app_id=111,
            new_check_name='adaptive-trust-ci/verified@new000000000', new_app_id=222,
            required_reviews=0,
        )
        with mock.patch.object(Path, 'is_file', return_value=True), \
                mock.patch.object(cli_module.Policy, 'load', return_value=policy), \
                mock.patch.dict(os.environ, {'TRUST_CI_GITHUB_ADMIN_TOKEN': 'short-fixture'}), \
                self.assertRaisesRegex(SystemExit, 'provided together'):
            main(command[:-2])

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

    def test_promotion_schema_has_exact_tuple_indexes_and_append_only_retention(self) -> None:
        sql = (ROOT / 'trust-ci/sql/004_production_promotions.sql').read_text(encoding='utf-8')
        self.assertIn('ON DELETE RESTRICT', sql)
        self.assertIn('trust_ci_promotions_consume_idx', sql)
        self.assertIn('trust_ci_promotions_unconsumed_idx', sql)
        self.assertIn('trust_ci_promotion_events_order_idx', sql)
        self.assertNotRegex(sql, r'WHERE[^;]*now\s*\(')
        self.assertNotIn('WHERE promotion_id IS NOT NULL', sql)
        self.assertIn(
            'ON trust_ci_promotions (target_environment, expires_at, promotion_id)',
            sql,
        )
        self.assertNotIn('DELETE FROM trust_ci_promotion', sql)
        self.assertNotIn('TRUNCATE trust_ci_promotion', sql)

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

    def test_test_extra_declares_contract_test_runtime_dependencies(self) -> None:
        project = tomllib.loads(
            (ROOT / 'trust-ci/pyproject.toml').read_text(encoding='utf-8')
        )
        self.assertIn(
            'jsonschema==4.25.1',
            project['project']['optional-dependencies']['test'],
        )

    def test_example_holdout_digest_matches_example_bundle(self) -> None:
        import json

        policy = json.loads((ROOT / 'trust-ci/config/policy.example.json').read_text(encoding='utf-8'))
        self.assertEqual(policy['holdout']['digest'], bundle_digest(ROOT / 'trust-ci/holdout.example'))
        self.assertEqual(policy['holdout']['path'], '/etc/adaptive-trust-ci/holdout')
        self.assertEqual(policy['approval_rules'], [])
        self.assertEqual(
            policy['promotion'],
            {'environments': ['production'], 'max_ttl_seconds': 900},
        )
        self.assertTrue(all(command['required'] is True for command in policy['commands']))
        self.assertTrue(
            all(command['required'] is True for command in policy['holdout']['commands'])
        )

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
        self.assertIn('accept_promotion', probe := (ROOT / 'trust-ci/tests/postgres_restart_probe.py').read_text(encoding='utf-8'))
        self.assertIn('consume_promotion', probe)
        self.assertIn('list_promotion_events', probe)

    def test_repository_contains_no_github_actions_workflow(self) -> None:
        workflows = ROOT / '.github' / 'workflows'
        self.assertFalse(workflows.exists(), 'GitHub Actions are forbidden for this project')


if __name__ == '__main__':
    unittest.main()
