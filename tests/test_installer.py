from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('install_into', ROOT / 'scripts/install_into.py')
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def install_silent(*args, **kwargs) -> None:
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


if __name__ == '__main__':
    unittest.main()
