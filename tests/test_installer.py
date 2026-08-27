from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
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
    def test_clean_install_delivers_architecture_tooling_without_adopting_a_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            install_silent(ROOT, target, force=False, dry_run=False)
            self.assertTrue((target / 'scripts/grok_architecture.py').is_file())
            self.assertTrue((target / 'schemas/architecture-system.schema.json').is_file())
            self.assertTrue((target / 'schemas/architecture-rules.schema.json').is_file())
            self.assertFalse((target / 'architecture/system.yaml').exists())
            self.assertFalse((target / 'architecture/rules.yaml').exists())
            self.assertFalse((target / 'architecture/adoption.json').exists())
            subprocess.run(['git', 'init', '-q'], cwd=target, check=True)
            result = subprocess.run(
                ['python3', 'scripts/grok_verify.py', '--mode', 'fast', '--no-record', '--json'],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['architecture']['status'], 'not_configured')

    def test_clean_install_delivers_valid_non_authoritative_architecture_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            install_silent(ROOT, target, force=False, dry_run=False)
            template_root = target / '.grok-stack/templates/architecture'
            system_example = template_root / 'system.example.yaml'
            rules_example = template_root / 'rules.example.yaml'
            self.assertTrue(system_example.is_file())
            self.assertTrue(rules_example.is_file())
            authority = target / 'architecture'
            authority.mkdir()
            (authority / 'system.yaml').write_bytes(system_example.read_bytes())
            (authority / 'rules.yaml').write_bytes(rules_example.read_bytes())
            result = subprocess.run(
                ['python3', 'scripts/grok_architecture.py', '--root', '.', 'validate', '--json'],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)['ok'])

    def test_force_never_manages_target_owned_architecture_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            expected = {
                'architecture/system.yaml': b'target system\n',
                'architecture/rules.yaml': b'target rules\n',
                'architecture/adoption.json': b'target adoption\n',
            }
            for relative, content in expected.items():
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            accidentally_managed = (*MODULE.MANAGED_FILES, *expected)
            with patch.object(MODULE, 'MANAGED_FILES', accidentally_managed):
                install_silent(ROOT, target, force=True, dry_run=False)
            for relative, content in expected.items():
                self.assertEqual((target / relative).read_bytes(), content, relative)

    def test_clean_install_delivers_schema_and_runnable_spec_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            install_silent(ROOT, target, force=False, dry_run=False)
            schema = target / 'schemas/change-spec.schema.json'
            self.assertEqual(schema.read_bytes(), (ROOT / 'schemas/change-spec.schema.json').read_bytes())
            change = target / 'engineering/changes/20260826-installed-cli'
            change.mkdir(parents=True)
            payload = {
                'schema_version': 2, 'change_id': '20260826-installed-cli',
                'objective': {'id': 'OBJ-001', 'statement': 'installed CLI', 'success_metric': 'exit', 'target': 'zero'},
                'risk': {'tier': 'green', 'domains': []},
                'acceptance_criteria': [{'id': 'AC-001', 'statement': 'validates', 'evidence': [{'receipt': 'verification'}]}],
                'invariants': [], 'forbidden_outcomes': [],
                'contracts': {'openapi': [], 'json_schema': [], 'events': []}, 'observability': [],
                'rollback': {'strategy': 'forward_fix', 'maximum_steps': 1}, 'approvals': {'required_scopes': []},
            }
            spec_path = change / 'change-spec.yaml'
            spec_path.write_text(json.dumps(payload), encoding='utf-8')
            proc = subprocess.run(
                ['python3', str(target / 'scripts/grok_spec.py'), 'validate', str(spec_path.relative_to(target)), '--gate', '--json'],
                cwd=target, text=True, capture_output=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
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

    def test_force_rejects_symlink_and_special_managed_destinations(self) -> None:
        for label in ('final_symlink', 'ancestor_symlink', 'special_file'):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                target = root / 'target'
                outside = root / 'outside'
                authority = target / 'architecture/system.yaml'
                authority.parent.mkdir(parents=True)
                authority.write_bytes(b'target authority\n')
                outside.mkdir()
                if label == 'final_symlink':
                    managed = target / '.grok/config.toml'
                    managed.parent.mkdir(parents=True)
                    managed.symlink_to(authority)
                elif label == 'ancestor_symlink':
                    outside_managed = outside / 'config.toml'
                    outside_managed.write_bytes(b'outside\n')
                    (target / '.grok').symlink_to(outside, target_is_directory=True)
                else:
                    managed = target / '.grok/config.toml'
                    managed.parent.mkdir(parents=True)
                    os.mkfifo(managed)
                with self.assertRaises((OSError, RuntimeError, SystemExit)):
                    install_silent(ROOT, target, force=True, dry_run=False)
                self.assertEqual(authority.read_bytes(), b'target authority\n')
                if label == 'ancestor_symlink':
                    self.assertEqual((outside / 'config.toml').read_bytes(), b'outside\n')

    def test_force_rolls_back_when_managed_parent_is_relocated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'target'
            managed = target / '.grok/config.toml'
            managed.parent.mkdir(parents=True)
            managed.write_bytes(b'outside original\n')
            relocated = root / 'relocated-grok'
            real_replace = os.replace
            moved = False

            def relocate_before_replace(src, dst, *args, **kwargs):
                nonlocal moved
                destination_fd = kwargs.get('dst_dir_fd')
                destination = (
                    Path(os.readlink(f'/proc/self/fd/{destination_fd}'))
                    if destination_fd is not None
                    else None
                )
                if not moved and destination == managed.parent:
                    moved = True
                    managed.parent.rename(relocated)
                    managed.parent.mkdir()
                return real_replace(src, dst, *args, **kwargs)

            with patch('os.replace', side_effect=relocate_before_replace):
                with self.assertRaises((OSError, RuntimeError, SystemExit)):
                    install_silent(ROOT, target, force=True, dry_run=False)
            self.assertTrue(moved)
            self.assertEqual((relocated / 'config.toml').read_bytes(), b'outside original\n')

    def test_bitrix_target_gets_local_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            (target / 'bitrix').mkdir(parents=True)
            (target / 'local').mkdir()
            install_silent(ROOT, target, force=False, dry_run=False)
            self.assertTrue((target / 'local/AGENTS.md').is_file())

    def test_with_ci_is_forbidden_and_preserves_unrelated_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            workflows = target / '.github/workflows'
            workflows.mkdir(parents=True)
            unrelated = workflows / 'existing.yml'
            unrelated.write_text('name: existing\n', encoding='utf-8')
            with self.assertRaises(SystemExit) as ctx:
                install_silent(ROOT, target, force=False, dry_run=False, with_ci=True)
            self.assertIn('forbidden', str(ctx.exception).lower())
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'name: existing\n')
            self.assertFalse((workflows / 'adaptive-grok.yml').exists())

    def test_with_ci_dry_run_is_forbidden_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            workflows = target / '.github/workflows'
            workflows.mkdir(parents=True)
            unrelated = workflows / 'existing.yml'
            unrelated.write_text('name: existing\n', encoding='utf-8')
            with self.assertRaises(SystemExit) as ctx:
                install_silent(ROOT, target, force=True, dry_run=True, with_ci=True)
            self.assertIn('forbidden', str(ctx.exception).lower())
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'name: existing\n')
            self.assertFalse((workflows / 'adaptive-grok.yml').exists())
            self.assertFalse((target / 'scripts/grok_verify.py').exists())

    def test_default_install_does_not_copy_workflow_from_grok_stack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            install_silent(ROOT, target, force=False, dry_run=False)
            self.assertTrue((target / 'scripts/grok_verify.py').is_file())
            self.assertFalse((target / '.github/workflows').exists())
            self.assertFalse((target / '.grok-stack/templates/ci/github-actions.yml').exists())
            copied = [
                path for path in target.rglob('*')
                if path.is_file() and path.suffix in {'.yml', '.yaml'} and (
                    '.github/workflows' in path.as_posix() or path.name == 'github-actions.yml'
                )
            ]
            self.assertEqual(copied, [])

    def test_default_install_copies_quality_configs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            install_silent(ROOT, target, force=False, dry_run=False)
            for name in ('ruff.toml', 'bandit.yaml', '.coveragerc'):
                copied = target / name
                self.assertTrue(copied.is_file(), name)
                self.assertEqual(copied.read_bytes(), (ROOT / name).read_bytes(), name)
            self.assertFalse((target / '.github/workflows').exists())

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
