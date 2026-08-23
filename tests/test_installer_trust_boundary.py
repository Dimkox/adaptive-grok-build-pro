from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'install_into_trust_boundary',
    ROOT / 'scripts/install_into.py',
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

TRUST_FILES = (
    '.github/workflows/trusted-ci.yml',
    '.github/workflows/release.yml',
    '.github/CODEOWNERS',
    'docs/TRUST-BOUNDARY.md',
)


def install_silent(*args, **kwargs) -> None:
    kwargs.setdefault('runner', lambda command: SimpleNamespace(returncode=0))
    with contextlib.redirect_stdout(io.StringIO()):
        MODULE.install(*args, **kwargs)


class InstallerTrustBoundaryTests(unittest.TestCase):
    def test_with_ci_copies_trust_files_and_preserves_unrelated_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            unrelated = target / '.github/workflows/existing.yml'
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text('name: existing\n', encoding='utf-8')

            install_silent(
                ROOT,
                target,
                force=False,
                dry_run=False,
                with_ci=True,
            )

            self.assertEqual(
                unrelated.read_text(encoding='utf-8'),
                'name: existing\n',
            )
            for rel in TRUST_FILES:
                self.assertEqual(
                    (target / rel).read_bytes(),
                    (ROOT / rel).read_bytes(),
                    rel,
                )

    def test_with_ci_managed_conflict_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            path = target / '.github/workflows/trusted-ci.yml'
            path.parent.mkdir(parents=True)
            path.write_text('name: local\n', encoding='utf-8')

            with self.assertRaises(SystemExit):
                install_silent(
                    ROOT,
                    target,
                    force=False,
                    dry_run=False,
                    with_ci=True,
                )

            self.assertEqual(path.read_text(encoding='utf-8'), 'name: local\n')
            install_silent(
                ROOT,
                target,
                force=True,
                dry_run=False,
                with_ci=True,
            )
            self.assertEqual(path.read_bytes(), (ROOT / path.relative_to(target)).read_bytes())

    def test_with_ci_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            install_silent(
                ROOT,
                target,
                force=True,
                dry_run=True,
                with_ci=True,
            )
            for rel in TRUST_FILES:
                self.assertFalse((target / rel).exists(), rel)
            self.assertFalse((target / 'scripts/grok_verify.py').exists())


if __name__ == '__main__':
    unittest.main()
