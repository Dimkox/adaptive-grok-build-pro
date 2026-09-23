from __future__ import annotations

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = ROOT / 'trust-ci/scripts/smoke.sh'

_PIPE_TO_GREP = re.compile(r'\|\s*grep\b(?P<arguments>[^;\n|]*)')
_QUIET_GREP_OPTION = re.compile(
    r'(?<!\S)(?:--quiet|-[A-Za-z]*q[A-Za-z]*)(?=\s|$)'
)
_ASSIGNMENT_BEFORE_CONTROL = re.compile(
    r'(?m)(?:^|[;&|]\s*|\bthen\s+|\bdo\s+)'
    r'(?:[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|\'[^\']*\'|[^\s;]+)\s+)+'
    r'(?:break|continue|return|exit)\b'
)
_GREP_LF = re.compile(r'(?<!\S)grep\s+(?:--[^\s]+\s+)*-[A-Za-z]*lf[A-Za-z]*(?=\s|$)')


def _contains_pipe_to_quiet_grep(source: str) -> bool:
    """Detect a live grep quiet-consumer pipeline, including split commands."""

    normalized = re.sub(r'\\[ \t]*\n', ' ', source)
    normalized = re.sub(r'\|\s*\n\s*', ' | ', normalized)
    return any(
        _QUIET_GREP_OPTION.search(match.group('arguments'))
        for match in _PIPE_TO_GREP.finditer(normalized)
    )


def _contains_assignment_before_control_builtin(source: str) -> bool:
    return bool(_ASSIGNMENT_BEFORE_CONTROL.search(source))


def _contains_grep_lf(source: str) -> bool:
    return bool(_GREP_LF.search(source))


class FakeSmokeRuntime:
    """A no-network, no-Docker-daemon runtime for the smoke script."""

    _REQUIRED_FILES = (
        'trust-ci/sql/001_schema.sql',
        'trust-ci/sql/002_operational_indexes.sql',
        'trust-ci/config/policy.example.json',
        'trust-ci/compose.yaml',
        'trust-ci/scripts/postgres-integration.sh',
        'trust-ci/scripts/postgres-restart-drill.sh',
        'trust-ci/scripts/restore-drill.sh',
    )
    _VALID_RENDERED_COMPOSE = textwrap.dedent(
        '''\
        services:
          docker-engine:
            image: fake-docker-engine
          worker:
            environment:
              DOCKER_HOST: tcp://docker-engine:2375
        '''
    )
    _AUTH_VALUE = 'smoke-test-read-value'

    def __init__(self, root: Path) -> None:
        self.root = root
        self.bin_dir = root / 'bin'
        self.log_path = root / 'runtime.log'
        self.compose_file = root / 'trust-ci/compose.yaml'
        self.bin_dir.mkdir(parents=True)
        self._write_required_files()
        self._write_fake_curl()
        self._write_fake_docker()

    def _write_required_files(self) -> None:
        for relative in self._REQUIRED_FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n', encoding='utf-8')

    def _write_executable(self, name: str, body: str) -> None:
        path = self.bin_dir / name
        path.write_text(textwrap.dedent(body), encoding='utf-8')
        path.chmod(0o700)

    def _write_fake_curl(self) -> None:
        self._write_executable(
            'curl',
            '''
            #!/usr/bin/env bash
            set -euo pipefail

            endpoint="${!#}"
            case "$endpoint" in
              */health/live)
                label='health/live'
                response="${FAKE_CURL_HEALTH_LIVE-}"
                ;;
              */health/ready)
                label='health/ready'
                response="${FAKE_CURL_HEALTH_READY-}"
                ;;
              */metrics)
                authorized=false
                for argument in "$@"; do
                  if [[ "$argument" == "Authorization: Bearer ${FAKE_EXPECTED_AUTH}" ]]; then
                    authorized=true
                  fi
                done
                if [[ "$authorized" != true ]]; then
                  printf 'fake curl: metrics authorization mismatch\n' >&2
                  exit 2
                fi
                label='metrics'
                response="${FAKE_CURL_METRICS-}"
                ;;
              *)
                printf 'fake curl: unexpected endpoint\n' >&2
                exit 2
                ;;
            esac

            printf 'curl %s\n' "$label" >>"$FAKE_RUNTIME_LOG"
            printf '%s' "$response"
            ''',
        )

    def _write_fake_docker(self) -> None:
        self._write_executable(
            'docker',
            '''
            #!/usr/bin/env bash
            set -euo pipefail

            if [[ "${1-}" != compose || "${2-}" != -f ]]; then
              printf 'fake docker: unexpected command shape\n' >&2
              exit 2
            fi
            compose_file="${3-}"
            if [[ ! -f "$compose_file" ]]; then
              printf 'fake docker: compose file missing\n' >&2
              exit 2
            fi
            shift 3

            case "${1-}" in
              config)
                if [[ "$*" != config ]]; then
                  printf 'fake docker: unexpected config arguments\n' >&2
                  exit 2
                fi
                printf 'docker compose config\n' >>"$FAKE_RUNTIME_LOG"
                printf '%s' "${FAKE_DOCKER_CONFIG-}"
                ;;
              run)
                if [[ "$*" != 'run --rm --no-deps api migration-status' ]]; then
                  printf 'fake docker: unexpected migration arguments\n' >&2
                  exit 2
                fi
                printf 'docker compose run migration-status\n' >>"$FAKE_RUNTIME_LOG"
                if [[ "${FAKE_MIGRATION_STATUS_EXIT:-0}" != 0 ]]; then
                  printf 'fake docker: migration-status failed\n' >&2
                  exit "$FAKE_MIGRATION_STATUS_EXIT"
                fi
                ;;
              ps)
                if [[ "$*" != ps ]]; then
                  printf 'fake docker: unexpected ps arguments\n' >&2
                  exit 2
                fi
                printf 'docker compose ps\n' >>"$FAKE_RUNTIME_LOG"
                if [[ "${FAKE_COMPOSE_PS_EXIT:-0}" != 0 ]]; then
                  printf 'fake docker: compose ps failed\n' >&2
                  exit "$FAKE_COMPOSE_PS_EXIT"
                fi
                ;;
              *)
                printf 'fake docker: unexpected compose subcommand\n' >&2
                exit 2
                ;;
            esac
            ''',
        )

    def run(
        self,
        *,
        health_live: str = 'live-ok',
        health_ready: str = 'ready-ok',
        metrics: str = '# HELP adaptive_trust_ci_policy_info policy\nadaptive_trust_ci_policy_info 1\n',
        rendered: str | None = None,
        migration_status_exit: int = 0,
        compose_ps_exit: int = 0,
        discover_fakes_from_path: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                'PATH': (
                    f'{self.bin_dir}:{environment.get("PATH", "")}'
                    if discover_fakes_from_path
                    else '/usr/bin:/bin'
                ),
                'TRUST_CI_TOOL_PATHS': str(self.bin_dir),
                'TRUST_CI_PUBLIC_BASE_URL': 'http://smoke-test.invalid',
                'TRUST_CI_COMPOSE_FILE': str(self.compose_file),
                'TRUST_CI_READ_TOKEN': self._AUTH_VALUE,
                'FAKE_EXPECTED_AUTH': self._AUTH_VALUE,
                'FAKE_CURL_HEALTH_LIVE': health_live,
                'FAKE_CURL_HEALTH_READY': health_ready,
                'FAKE_CURL_METRICS': metrics,
                'FAKE_DOCKER_CONFIG': (
                    self._VALID_RENDERED_COMPOSE if rendered is None else rendered
                ),
                'FAKE_MIGRATION_STATUS_EXIT': str(migration_status_exit),
                'FAKE_COMPOSE_PS_EXIT': str(compose_ps_exit),
                'FAKE_RUNTIME_LOG': str(self.log_path),
            }
        )
        return subprocess.run(
            ['bash', str(SMOKE_SCRIPT)],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def log_lines(self) -> list[str]:
        return self.log_path.read_text(encoding='utf-8').splitlines()


class SmokeScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.script = SMOKE_SCRIPT.read_text(encoding='utf-8')

    def test_smoke_does_not_pipe_live_output_into_grep_q(self) -> None:
        self.assertFalse(
            _contains_pipe_to_quiet_grep(self.script),
            'quiet grep must consume captured output, not a live producer pipeline',
        )

    def test_pipeline_contract_rejects_all_quiet_grep_forms(self) -> None:
        for pipeline in (
            "curl ... | grep -q '^needle'",
            "curl ... | grep --quiet '^needle'",
            "curl ... | grep '^needle' -q",
            "curl ... | grep '^needle' --quiet",
            "curl ... | grep -qE '^needle'",
            "curl ... | grep -E '^needle' -q",
        ):
            with self.subTest(pipeline=pipeline):
                self.assertTrue(_contains_pipe_to_quiet_grep(pipeline))

    def test_smoke_requires_non_empty_captured_observations(self) -> None:
        for name in ('health_live', 'health_ready', 'metrics', 'rendered'):
            self.assertRegex(
                self.script,
                rf'\[\[\s+-n\s+"\${name}"\s+\]\]',
                f'{name} must be asserted non-empty before it is treated as an observation',
            )

    def test_smoke_has_no_assignment_before_control_builtin(self) -> None:
        self.assertFalse(
            _contains_assignment_before_control_builtin(self.script),
            'assignments before break/continue/return/exit do not persist',
        )

    def test_assignment_contract_rejects_control_builtin_forms(self) -> None:
        for source in (
            'root="$candidate" chunk="$found" break',
            'if ready; then result=value return 0; fi',
            'do item=next continue; done',
            'status=failed exit 1',
        ):
            with self.subTest(source=source):
                self.assertTrue(_contains_assignment_before_control_builtin(source))

    def test_smoke_has_no_grep_lf_typo(self) -> None:
        self.assertFalse(
            _contains_grep_lf(self.script),
            'grep -lf reads patterns from a file; fixed-string file discovery is grep -lF',
        )

    def test_grep_lf_contract_distinguishes_typo_from_fixed_string_form(self) -> None:
        self.assertTrue(_contains_grep_lf("grep -rlf 'needle here' ."))
        self.assertFalse(_contains_grep_lf("grep -rlF 'needle here' ."))

    def test_smoke_resolves_and_validates_required_commands(self) -> None:
        for name in ('python3', 'curl', 'grep', 'docker'):
            with self.subTest(name=name):
                self.assertRegex(
                    self.script,
                    rf'{name}_bin="\$\(resolve_command {name}\)"',
                )
                self.assertIn(f'"${{{name}_bin}}"', self.script)


class SmokeRuntimeTests(unittest.TestCase):
    def _runtime(self) -> tuple[tempfile.TemporaryDirectory[str], FakeSmokeRuntime]:
        temporary_directory = tempfile.TemporaryDirectory(prefix='trust-ci-smoke-')
        return temporary_directory, FakeSmokeRuntime(Path(temporary_directory.name))

    def _assert_failure(
        self,
        result: subprocess.CompletedProcess[str],
        diagnostic: str,
    ) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(diagnostic, result.stderr)
        self.assertNotIn('trust-ci smoke: PASS', result.stdout)

    def test_valid_fake_runtime_produces_pass_and_checks_all_commands(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'trust-ci smoke: PASS\n')
            self.assertEqual(result.stderr, '')
            self.assertEqual(
                runtime.log_lines(),
                [
                    'curl health/live',
                    'curl health/ready',
                    'curl metrics',
                    'docker compose config',
                    'docker compose run migration-status',
                    'docker compose ps',
                ],
            )

    def test_explicit_tool_roots_work_when_fakes_are_absent_from_path(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(discover_fakes_from_path=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'trust-ci smoke: PASS\n')

    def test_empty_health_live_fails_closed_with_diagnostic(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(health_live='')

            self._assert_failure(result, 'health/live returned an empty response')

    def test_empty_health_ready_fails_closed_with_diagnostic(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(health_ready='')

            self._assert_failure(result, 'health/ready returned an empty response')

    def test_empty_metrics_fails_closed_with_diagnostic(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(metrics='')

            self._assert_failure(result, 'metrics returned an empty response')

    def test_metrics_without_policy_marker_fails_closed_with_diagnostic(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(metrics='# HELP another_metric something\n')

            self._assert_failure(
                result,
                'metrics missing adaptive_trust_ci_policy_info marker',
            )

    def test_empty_rendered_compose_fails_closed_with_diagnostic(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(rendered='')

            self._assert_failure(
                result,
                'docker compose config returned an empty response',
            )

    def test_rendered_compose_without_docker_engine_fails_closed(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(
                rendered=(
                    'services:\n'
                    '  worker:\n'
                    '    environment:\n'
                    '      DOCKER_HOST: tcp://other:2375\n'
                )
            )

            self._assert_failure(
                result,
                'rendered Compose missing docker-engine service',
            )

    def test_rendered_compose_without_isolated_docker_host_fails_closed(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(
                rendered='services:\n  docker-engine:\n    image: fake\n'
            )

            self._assert_failure(
                result,
                'rendered Compose missing isolated Docker host',
            )

    def test_host_docker_socket_fails_closed_with_diagnostic(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(
                rendered=(
                    FakeSmokeRuntime._VALID_RENDERED_COMPOSE
                    + '      DOCKER_SOCKET: /var/run/docker.sock\n'
                )
            )

            self._assert_failure(
                result,
                'worker topology still exposes the host Docker socket',
            )

    def test_migration_status_failure_is_not_ignored(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(migration_status_exit=17)

            self._assert_failure(result, 'fake docker: migration-status failed')

    def test_compose_ps_failure_is_not_ignored(self) -> None:
        temporary_directory, runtime = self._runtime()
        with temporary_directory:
            result = runtime.run(compose_ps_exit=19)

            self._assert_failure(result, 'fake docker: compose ps failed')


if __name__ == '__main__':
    unittest.main()
