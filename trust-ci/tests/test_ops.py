from __future__ import annotations

import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from _support import policy_data
from adaptive_trust_ci.github import branch_protection_payload
from adaptive_trust_ci.holdout import bundle_digest
from adaptive_trust_ci.policy import Policy, PolicyCatalog
from adaptive_trust_ci.sandbox import ContainerExecutor, classify_command_abort


ROOT = Path(__file__).resolve().parents[2]

SANDBOX_TIMEOUT_MARKER = 'command timed out after 120s'


class CommandAbortClassificationTests(unittest.TestCase):
    """Issue #103: an externally killed command must be interpretable, not a plain failure."""

    def classify(self, exit_code: int, stderr_tail: str = ''):
        return classify_command_abort(name='repository-verification', exit_code=exit_code, stderr_tail=stderr_tail)

    def test_docker_propagated_sigkill_exit_is_a_signal_abort(self) -> None:
        abort = self.classify(137)
        self.assertIsNotNone(abort)
        assert abort is not None
        self.assertEqual(abort.kind, 'signal')
        self.assertEqual(abort.signal, 'SIGKILL')
        self.assertEqual(abort.signal_number, 9)
        self.assertEqual(abort.exit_code, 137)
        self.assertEqual(abort.command, 'repository-verification')
        self.assertEqual(abort.failure_code, 'aborted-by-signal')

    def test_docker_propagated_sigterm_exit_is_a_signal_abort(self) -> None:
        abort = self.classify(143)
        assert abort is not None
        self.assertEqual(abort.kind, 'signal')
        self.assertEqual(abort.signal, 'SIGTERM')
        self.assertEqual(abort.signal_number, 15)
        self.assertEqual(abort.failure_code, 'aborted-by-signal')

    def test_negative_return_code_of_the_container_client_is_a_signal_abort(self) -> None:
        # subprocess reports death by signal N as return code -N; the sandbox stores that value verbatim.
        for exit_code, signal_name, number in (
            (-9, 'SIGKILL', 9),
            (-15, 'SIGTERM', 15),
            (-2, 'SIGINT', 2),
            (-1, 'SIGHUP', 1),
        ):
            with self.subTest(exit_code=exit_code):
                abort = self.classify(exit_code)
                assert abort is not None
                self.assertEqual(abort.kind, 'signal')
                self.assertEqual(abort.signal, signal_name)
                self.assertEqual(abort.signal_number, number)
                self.assertEqual(abort.failure_code, 'aborted-by-signal')

    def test_sandbox_deadline_exit_with_its_marker_is_a_distinct_timeout_abort(self) -> None:
        abort = self.classify(124, f'ran for a while\n{SANDBOX_TIMEOUT_MARKER}')
        assert abort is not None
        self.assertEqual(abort.kind, 'timeout')
        self.assertIsNone(abort.signal)
        self.assertIsNone(abort.signal_number)
        self.assertEqual(abort.exit_code, 124)
        self.assertEqual(abort.failure_code, 'aborted-by-timeout')

    def test_bare_124_without_the_sandbox_marker_is_not_claimed_as_an_abort(self) -> None:
        self.assertIsNone(self.classify(124, 'the command itself exited 124'))
        self.assertIsNone(self.classify(124))

    def test_ordinary_and_internal_failure_codes_are_never_aborts(self) -> None:
        for exit_code in (0, 1, 96, 97, 125, 126, 127, 128, 193, 255, -65, -1000):
            with self.subTest(exit_code=exit_code):
                self.assertIsNone(self.classify(exit_code, SANDBOX_TIMEOUT_MARKER))

    def test_non_integer_exit_codes_yield_no_claim_instead_of_raising(self) -> None:
        """The classifier is total: recovered JSON can hold anything in exit_code (round-2 review G-1)."""
        for exit_code in (None, '137', '', True, False, 137.0, [], {}, object()):
            with self.subTest(exit_code=repr(exit_code)):
                self.assertIsNone(self.classify(exit_code, SANDBOX_TIMEOUT_MARKER))
                self.assertIsNone(self.classify(exit_code))

    def test_non_string_stderr_tail_yields_no_claim_instead_of_raising(self) -> None:
        """Same totality for the corroborating tail (review round 2 R2-2)."""
        for stderr_tail in (None, ['x'], b'command timed out after 120s', 5, {}, 120.0):
            with self.subTest(stderr_tail=repr(stderr_tail)):
                # A timeout claim needs a real string tail; nothing else may raise.
                self.assertIsNone(classify_command_abort(name='u', exit_code=124, stderr_tail=stderr_tail))
                # Signal death is proven by the exit status alone, so a lost tail must not suppress it.
                abort = classify_command_abort(name='u', exit_code=137, stderr_tail=stderr_tail)
                assert abort is not None
                self.assertEqual((abort.kind, abort.signal, abort.signal_number), ('signal', 'SIGKILL', 9))
        # A bytes tail is not decoded into a claim, even one that spells the marker.
        marker_bytes = b'x\n' + SANDBOX_TIMEOUT_MARKER.encode()
        self.assertIsNone(classify_command_abort(name='u', exit_code=124, stderr_tail=marker_bytes))
        self.assertIsNone(classify_command_abort(name='u', exit_code=124))

        # Nor is any other object coerced with str(): only a real str tail can corroborate a timeout.
        class _MarkerSounding:
            def __str__(self) -> str:
                return SANDBOX_TIMEOUT_MARKER

        self.assertIsNone(classify_command_abort(name='u', exit_code=124, stderr_tail=_MarkerSounding()))
        # The same object still cannot hide a signal kill proven by the exit status.
        abort = classify_command_abort(name='u', exit_code=137, stderr_tail=_MarkerSounding())
        assert abort is not None
        self.assertEqual(abort.signal, 'SIGKILL')

    def test_signal_range_boundaries_are_pinned(self) -> None:
        """129/130 and the 192-vs-193 edge of the interpreted range (round-2 review G-3)."""
        for exit_code, signal_name, number in (
            (129, 'SIGHUP', 1),
            (130, 'SIGINT', 2),
            (137, 'SIGKILL', 9),
            (143, 'SIGTERM', 15),
            (192, 'SIGRTMAX', 64),
        ):
            with self.subTest(exit_code=exit_code):
                abort = self.classify(exit_code)
                assert abort is not None
                self.assertEqual((abort.signal, abort.signal_number), (signal_name, number))
        for exit_code in (128, 193, 194, 255):
            with self.subTest(outside=exit_code):
                self.assertIsNone(self.classify(exit_code))

    def test_timeout_marker_must_end_the_stored_tail(self) -> None:
        """Only our own appended marker counts; a command that merely printed it is not an abort (G-4)."""
        self.assertIsNone(self.classify(124, f'{SANDBOX_TIMEOUT_MARKER}\nAssertionError: 1 != 0'))
        self.assertIsNone(self.classify(124, 'progress line\n' + SANDBOX_TIMEOUT_MARKER + '\nthen a traceback'))
        self.assertIsNone(self.classify(124, 'command timed out after 1200s and then some output'))
        # Trailing whitespace after the marker is still our own ending line.
        for tail in (SANDBOX_TIMEOUT_MARKER, SANDBOX_TIMEOUT_MARKER + '\n', SANDBOX_TIMEOUT_MARKER + '  \n'):
            with self.subTest(tail=repr(tail)):
                abort = self.classify(124, tail)
                assert abort is not None
                self.assertEqual(abort.kind, 'timeout')

    def test_signal_names_fall_back_to_the_number_for_unmapped_signals(self) -> None:
        abort = self.classify(161)
        assert abort is not None
        self.assertEqual(abort.kind, 'signal')
        self.assertEqual(abort.signal_number, 33)
        self.assertEqual(abort.signal, 'SIG33')

    def test_abort_detail_and_stored_member_carry_the_cause(self) -> None:
        abort = self.classify(137)
        assert abort is not None
        self.assertIn('SIGKILL', abort.detail())
        self.assertIn('repository-verification', abort.detail())
        self.assertEqual(
            abort.to_result(),
            {
                'kind': 'signal',
                'command': 'repository-verification',
                'exit_code': 137,
                'signal': 'SIGKILL',
                'signal_number': 9,
                'failure_code': 'aborted-by-signal',
            },
        )

    def test_abort_classes_can_never_read_as_success(self) -> None:
        for exit_code, stderr in ((137, ''), (143, ''), (-9, ''), (124, SANDBOX_TIMEOUT_MARKER)):
            abort = self.classify(exit_code, stderr)
            assert abort is not None
            self.assertTrue(abort.failure_code.endswith('signal') or abort.failure_code.endswith('timeout'))
            self.assertNotIn(abort.failure_code, {'', 'verification-failed', 'passed'})
            self.assertNotIn('passed', abort.failure_code)

    def test_real_signalled_process_return_codes_are_interpreted_on_this_platform(self) -> None:
        """Pin the platform contract: subprocess reports signal death as a negative return code."""
        from adaptive_trust_ci.sandbox import _command_result

        for send, expected_signal in ((lambda p: p.kill(), 'SIGKILL'), (lambda p: p.terminate(), 'SIGTERM')):
            with self.subTest(signal=expected_signal):
                process = subprocess.Popen(['sleep', '30'], start_new_session=True)
                time.sleep(0.15)
                send(process)
                process.wait(timeout=10)
                exit_code = int(process.returncode or 0)
                self.assertLess(exit_code, 0)
                abort = classify_command_abort(name='unit', exit_code=exit_code)
                assert abort is not None
                self.assertEqual(abort.kind, 'signal')
                self.assertEqual(abort.signal, expected_signal)
                self.assertEqual(abort.failure_code, 'aborted-by-signal')
                # The same classification must hold once the result row is built the way the sandbox builds it.
                result = _command_result('unit', exit_code, '', 'killed', 0.2, 20_000)
                self.assertEqual(result.status, 'fail')
                self.assertEqual(
                    classify_command_abort(
                        name=result.name,
                        exit_code=result.exit_code,
                        stderr_tail=result.stderr_tail,
                    ).signal,
                    expected_signal,
                )

    def test_sandbox_timeout_marker_survives_output_truncation(self) -> None:
        """The deadline claim depends on the marker tailing; prove it with a tiny output budget."""
        from adaptive_trust_ci.sandbox import _command_result

        noisy = 'x' * 4000
        result = _command_result(
            'unit',
            124,
            noisy,
            noisy + f'\n{SANDBOX_TIMEOUT_MARKER}',
            0.2,
            100,
        )
        self.assertTrue(result.stderr_tail.endswith(SANDBOX_TIMEOUT_MARKER))
        abort = classify_command_abort(
            name=result.name,
            exit_code=result.exit_code,
            stderr_tail=result.stderr_tail,
        )
        assert abort is not None
        self.assertEqual(abort.kind, 'timeout')
        self.assertEqual(abort.failure_code, 'aborted-by-timeout')


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
        for pin in ('coverage==7.15.4', 'pytest==9.1.1', 'pytest-xdist==3.8.0',
                    'pytest-cov==7.1.0', 'ruff==0.16.2', 'bandit==1.9.4', 'tomli==2.4.1'):
            self.assertIn(pin, runner)
        pyproject = (ROOT / 'trust-ci/pyproject.toml').read_text(encoding='utf-8')
        self.assertIn('setuptools==84.0.0', pyproject)
        self.assertNotIn('setuptools>=', pyproject)

    def test_example_catalog_profiles_have_bound_holdouts(self) -> None:
        import json

        raw = json.loads((ROOT / 'trust-ci/config/policy.example.json').read_text(encoding='utf-8'))
        catalog = PolicyCatalog.from_dict(raw)
        self.assertEqual(catalog.profile_count, 2)
        paths = {profile.holdout.host_path for profile in catalog.profiles}
        self.assertEqual(len(paths), 2)
        for profile in catalog.profiles:
            self.assertTrue(profile.holdout.path.is_absolute())
            self.assertTrue(profile.holdout.host_path.is_absolute())
            self.assertRegex(profile.holdout.digest, r'^[0-9a-f]{64}$')
        adaptive = catalog.resolve_repository('Dimkox/adaptive-grok-build-pro')
        self.assertEqual(adaptive.holdout.digest, bundle_digest(ROOT / 'trust-ci/holdout.example'))

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
