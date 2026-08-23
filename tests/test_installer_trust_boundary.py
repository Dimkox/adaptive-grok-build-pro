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


def rendered_source(rel: str, codeowner: str) -> bytes:
    data = (ROOT / rel).read_bytes()
    if rel in {'.github/CODEOWNERS', 'docs/TRUST-BOUNDARY.md'}:
        return data.replace(b'@Dimkox', codeowner.encode('utf-8'))
    return data


class InstallerTrustBoundaryTests(unittest.TestCase):
    def test_with_ci_requires_explicit_target_codeowner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            with self.assertRaisesRegex(SystemExit, 'codeowner'):
                install_silent(
                    ROOT,
                    target,
                    force=False,
                    dry_run=False,
                    with_ci=True,
                )
            for rel in TRUST_FILES:
                self.assertFalse((target / rel).exists(), rel)

    def test_with_ci_rejects_invalid_codeowner(self) -> None:
        invalid = ('Dimkox', '@bad owner', '@org/', '@')
        with tempfile.TemporaryDirectory() as tmp:
            for codeowner in invalid:
                with self.subTest(codeowner=codeowner), self.assertRaisesRegex(
                    SystemExit,
                    'codeowner',
                ):
                    install_silent(
                        ROOT,
                        Path(tmp) / codeowner.replace('/', '_').replace(' ', '_'),
                        force=False,
                        dry_run=False,
                        with_ci=True,
                        codeowner=codeowner,
                    )

    def test_with_ci_renders_target_owner_and_preserves_unrelated_workflow(self) -> None:
        codeowner = '@acme/platform'
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
                codeowner=codeowner,
            )

            self.assertEqual(
                unrelated.read_text(encoding='utf-8'),
                'name: existing\n',
            )
            for rel in TRUST_FILES:
                self.assertEqual(
                    (target / rel).read_bytes(),
                    rendered_source(rel, codeowner),
                    rel,
                )
            self.assertNotIn(
                '@Dimkox',
                (target / '.github/CODEOWNERS').read_text(encoding='utf-8'),
            )
            self.assertNotIn(
                '@Dimkox',
                (target / 'docs/TRUST-BOUNDARY.md').read_text(encoding='utf-8'),
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
                    codeowner='@Dimkox',
                )

            self.assertEqual(path.read_text(encoding='utf-8'), 'name: local\n')
            install_silent(
                ROOT,
                target,
                force=True,
                dry_run=False,
                with_ci=True,
                codeowner='@Dimkox',
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
                codeowner='@Dimkox',
            )
            for rel in TRUST_FILES:
                self.assertFalse((target / rel).exists(), rel)
            self.assertFalse((target / 'scripts/grok_verify.py').exists())


if __name__ == '__main__':
    unittest.main()
