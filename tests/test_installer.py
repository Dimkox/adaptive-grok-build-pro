from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('install_into', ROOT / 'scripts/install_into.py')
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _noop_runner(command: str):
    return SimpleNamespace(returncode=0)


def install_silent(*args, **kwargs) -> None:
    kwargs.setdefault('runner', _noop_runner)
    with contextlib.redirect_stdout(io.StringIO()):
        MODULE.install(*args, **kwargs)


class InstallerTests(unittest.TestCase):
    def test_installs_without_deleting_unrelated_agent_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            (target / '.grok/agents').mkdir(parents=True)
            unrelated = target / '.grok/agents/custom.toml'
            unrelated.write_text('name="custom"')
            install_silent(ROOT, target, force=False, dry_run=False)
            self.assertTrue(unrelated.is_file())
            self.assertTrue((target / '.grok/agents/bitrix_implementer.toml').is_file())
            self.assertIn('ADAPTIVE-GROK-PRO:START', (target / 'AGENTS.md').read_text())
            self.assertTrue((target / 'pre_tool_use.py').is_file())
            self.assertIn('.grok', (target / 'pre_tool_use.py').read_text())
            self.assertNotIn('STACK =', (target / 'pre_tool_use.py').read_text())

    def test_conflicting_managed_file_stops_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            path = target / '.grok/config.toml'
            path.parent.mkdir(parents=True)
            path.write_text('different=true')
            with self.assertRaises(SystemExit):
                install_silent(ROOT, target, force=False, dry_run=False)

    def test_force_overwrites_only_managed_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            path = target / '.grok/config.toml'
            path.parent.mkdir(parents=True)
            path.write_text('different=true')
            other = target / '.grok/keep.txt'
            other.write_text('keep')
            install_silent(ROOT, target, force=True, dry_run=False)
            self.assertIn('sandbox_mode', path.read_text())
            self.assertEqual(other.read_text(), 'keep')

    def test_bitrix_target_gets_local_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            (target / 'bitrix').mkdir(parents=True)
            (target / 'local').mkdir()
            install_silent(ROOT, target, force=False, dry_run=False)
            self.assertTrue((target / 'local/AGENTS.md').is_file())

    def test_with_ci_preserves_unrelated_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            workflows = target / '.github/workflows'
            workflows.mkdir(parents=True)
            unrelated = workflows / 'existing.yml'
            unrelated.write_text('name: existing\n', encoding='utf-8')
            install_silent(ROOT, target, force=False, dry_run=False, with_ci=True)
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'name: existing\n')
            self.assertTrue((workflows / 'adaptive-grok.yml').is_file())

    def test_managed_agents_block_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            install_silent(ROOT, target, force=False, dry_run=False)
            install_silent(ROOT, target, force=False, dry_run=False)
            text = (target / 'AGENTS.md').read_text()
            self.assertEqual(text.count('ADAPTIVE-GROK-PRO:START'), 1)

    def test_install_runs_required_dep_command(self) -> None:
        from adaptive_grok.toolchain import ToolCheck

        missing = ToolCheck(
            id='python3',
            name='Python 3',
            status='fail',
            message='missing',
            required=True,
            install='echo install-python',
            offer='Install fallback Python 3.12',
        )
        calls: list[str] = []

        def runner(command: str):
            calls.append(command)
            return SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as tmp, patch(
            'adaptive_grok.toolchain.check_toolchain',
            return_value=[missing],
        ):
            target = Path(tmp) / 'target'
            MODULE.install(ROOT, target, force=True, dry_run=False, install_deps=True, runner=runner)
        self.assertEqual(calls, ['echo install-python'])

    def test_install_no_deps_skips_runner(self) -> None:
        from adaptive_grok.toolchain import ToolCheck

        missing = ToolCheck(
            id='python3',
            name='Python 3',
            status='fail',
            message='missing',
            required=True,
            install='echo install-python',
            offer='offer',
        )
        calls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp, patch(
            'adaptive_grok.toolchain.check_toolchain',
            return_value=[missing],
        ):
            target = Path(tmp) / 'target'
            MODULE.install(
                ROOT,
                target,
                force=True,
                dry_run=False,
                install_deps=False,
                runner=lambda command: calls.append(command) or SimpleNamespace(returncode=0),
            )
        self.assertEqual(calls, [])

    def test_install_skips_optional_deps_unless_all_deps(self) -> None:
        from adaptive_grok.toolchain import ToolCheck

        optional = ToolCheck(
            id='php',
            name='PHP',
            status='info',
            message='missing',
            required=False,
            install='echo install-php',
            offer='offer',
        )
        calls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp, patch(
            'adaptive_grok.toolchain.check_toolchain',
            return_value=[optional],
        ):
            target = Path(tmp) / 'target'
            MODULE.install(ROOT, target, force=True, dry_run=False, install_deps=True, runner=lambda c: calls.append(c) or SimpleNamespace(returncode=0))
            self.assertEqual(calls, [])
            MODULE.install(
                ROOT,
                target,
                force=True,
                dry_run=False,
                install_deps=True,
                all_deps=True,
                runner=lambda c: calls.append(c) or SimpleNamespace(returncode=0),
            )
        self.assertEqual(calls, ['echo install-php'])

    def test_install_http_url_is_manual_and_does_not_run_runner(self) -> None:
        from adaptive_grok.toolchain import ToolCheck

        missing = ToolCheck(
            id='widget',
            name='Widget',
            status='fail',
            message='missing',
            required=True,
            install='HTTPS://example.com/widget/install',
            offer='Install Widget from URL',
        )
        calls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp, patch(
            'adaptive_grok.toolchain.check_toolchain',
            return_value=[missing],
        ):
            target = Path(tmp) / 'target'
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                MODULE.install(
                    ROOT,
                    target,
                    force=True,
                    dry_run=False,
                    install_deps=True,
                    runner=lambda command: calls.append(command) or SimpleNamespace(returncode=0),
                )
        self.assertEqual(calls, [])
        self.assertIn('MANUAL widget: HTTPS://example.com/widget/install', buf.getvalue())

    def test_install_dry_run_would_install_and_does_not_run_runner(self) -> None:
        from adaptive_grok.toolchain import ToolCheck

        missing = ToolCheck(
            id='python3',
            name='Python 3',
            status='fail',
            message='missing',
            required=True,
            install='echo install-python',
            offer='offer',
        )
        calls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp, patch(
            'adaptive_grok.toolchain.check_toolchain',
            return_value=[missing],
        ):
            target = Path(tmp) / 'target'
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                MODULE.install(
                    ROOT,
                    target,
                    force=True,
                    dry_run=True,
                    install_deps=True,
                    runner=lambda command: calls.append(command) or SimpleNamespace(returncode=0),
                )
        self.assertEqual(calls, [])
        self.assertIn('WOULD INSTALL python3: echo install-python', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
