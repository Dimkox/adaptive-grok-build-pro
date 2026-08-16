from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.manifest import generate_manifest, included_files, verify_manifest

SPEC = importlib.util.spec_from_file_location('package_stack', ROOT / 'scripts/package_stack.py')
PACKAGE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PACKAGE)


class ManifestTests(unittest.TestCase):
    def test_manifest_detects_change_and_untracked_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'a.txt').write_text('alpha', encoding='utf-8')
            generate_manifest(root)
            self.assertEqual(verify_manifest(root), [])

            (root / 'a.txt').write_text('changed', encoding='utf-8')
            (root / 'b.txt').write_text('new', encoding='utf-8')
            errors = verify_manifest(root)
            self.assertIn('checksum mismatch: a.txt', errors)
            self.assertIn('untracked by manifest: b.txt', errors)

    def test_runtime_state_is_not_packaged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            runtime = root / '.grok-stack/runtime'
            runtime.mkdir(parents=True)
            (runtime / '.gitkeep').write_text('', encoding='utf-8')
            (runtime / 'active-route.json').write_text('{}', encoding='utf-8')
            (root / 'README.md').write_text('project', encoding='utf-8')
            manifest = generate_manifest(root).read_text(encoding='utf-8')
            self.assertIn('.grok-stack/runtime/.gitkeep', manifest)
            self.assertNotIn('active-route.json', manifest)


class PackageTests(unittest.TestCase):
    def test_default_output_follows_version_file(self) -> None:
        self.assertEqual(
            PACKAGE._default_output(ROOT),
            f"dist/adaptive-grok-build-pro-v{(ROOT / 'VERSION').read_text(encoding='utf-8').strip()}.zip",
        )

    def test_archive_is_deterministic_and_self_verifying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            script = root / 'scripts/run.sh'
            script.parent.mkdir()
            script.write_text('#!/bin/sh\necho ok\n', encoding='utf-8')
            os.chmod(script, 0o755)

            first = Path(tmp) / 'first.zip'
            second = Path(tmp) / 'second.zip'
            first_digest = PACKAGE.write_archive(root, first)
            second_digest = PACKAGE.write_archive(root, second)
            self.assertEqual(first_digest, second_digest)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            with zipfile.ZipFile(first) as archive:
                self.assertIsNone(archive.testzip())
                names = set(archive.namelist())
                self.assertIn('adaptive-grok-build-pro/MANIFEST.sha256', names)
                self.assertIn('adaptive-grok-build-pro/scripts/run.sh', names)
                mode = archive.getinfo('adaptive-grok-build-pro/scripts/run.sh').external_attr >> 16
                self.assertTrue(mode & 0o100)

    def test_archive_excludes_dotenv_and_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'keep.txt').write_text('keep', encoding='utf-8')
            (root / '.env').write_text('GIT_FINE_GRAIN_TOKEN=should-not-pack', encoding='utf-8')
            (root / '.env.local').write_text('SECRET=x', encoding='utf-8')
            (root / 'dev.pem').write_text('nope', encoding='utf-8')
            archive_path = Path(tmp) / 'project.zip'
            PACKAGE.write_archive(root, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn('adaptive-grok-build-pro/keep.txt', names)
            self.assertFalse(any(name.endswith('.env') or name.endswith('.env.local') or name.endswith('.pem') for name in names))

    def test_archive_excludes_err_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'keep.txt').write_text('keep', encoding='utf-8')
            (root / 'err.log').write_text('do not pack', encoding='utf-8')
            archive_path = Path(tmp) / 'project.zip'
            PACKAGE.write_archive(root, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn('adaptive-grok-build-pro/keep.txt', names)
            self.assertFalse(any(name.endswith('err.log') for name in names))

    def test_included_files_and_shipped_zip_have_no_github_actions(self) -> None:
        version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(version, '2.0.6')
        rels = [path.relative_to(ROOT).as_posix() for path in included_files(ROOT)]
        self.assertFalse(any(rel.startswith('.github/workflows/') for rel in rels))
        self.assertNotIn('.github/dependabot.yml', rels)
        self.assertNotIn('.grok-stack/templates/ci/github-actions.yml', rels)
        zip_path = ROOT / 'packages' / f'adaptive-grok-build-pro-v{version}.zip'
        if zip_path.is_file():
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                member = 'adaptive-grok-build-pro/VERSION'
                self.assertIn(member, names)
                self.assertEqual(archive.read(member).decode('utf-8').strip(), '2.0.6')
                self.assertFalse(any('.github/workflows/' in name for name in names))
                self.assertFalse(any(name.endswith('dependabot.yml') for name in names))
                self.assertFalse(any(name.endswith('github-actions.yml') for name in names))

    def test_project_archive_excludes_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'keep.txt').write_text('keep', encoding='utf-8')
            (root / 'ignored.zip').write_text('ignore', encoding='utf-8')
            (root / '__pycache__').mkdir()
            (root / '__pycache__/x.pyc').write_bytes(b'ignore')
            archive_path = Path(tmp) / 'project.zip'
            PACKAGE.write_archive(root, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn('adaptive-grok-build-pro/keep.txt', names)
            self.assertNotIn('adaptive-grok-build-pro/ignored.zip', names)
            self.assertFalse(any('__pycache__' in name for name in names))


if __name__ == '__main__':
    unittest.main()
