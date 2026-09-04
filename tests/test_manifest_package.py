from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path, PurePosixPath
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import manifest as MANIFEST
from adaptive_grok.manifest import generate_manifest, included_files, verify_manifest

SPEC = importlib.util.spec_from_file_location('package_stack', ROOT / 'scripts/package_stack.py')
PACKAGE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PACKAGE)


def _shipped_git_environment() -> dict[str, str]:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith('GIT_')
    }
    environment.update(
        {
            'GIT_CONFIG_COUNT': '0',
            'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_SYSTEM': os.devnull,
            'GIT_GRAFT_FILE': os.devnull,
            'GIT_NO_REPLACE_OBJECTS': '1',
            'GIT_OPTIONAL_LOCKS': '0',
        }
    )
    return environment


def _shipped_git_command(
    root: Path,
    arguments: list[str],
    *,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    canonical_root = root.resolve(strict=True)
    return subprocess.run(
        [
            'git',
            '--no-replace-objects',
            '-c',
            f'safe.directory={canonical_root}',
            '-C',
            str(canonical_root),
            *arguments,
        ],
        input=input_bytes,
        check=True,
        capture_output=True,
        env=_shipped_git_environment(),
    )


def _head_release_sources(root: Path) -> dict[str, tuple[bytes, int]]:
    head = _shipped_git_command(root, ['rev-parse', '--verify', 'HEAD^{commit}']).stdout.strip()
    tree_oid = _shipped_git_command(
        root,
        ['rev-parse', '--verify', f'{head.decode("ascii")}^{{tree}}'],
    ).stdout.strip()
    tree = _shipped_git_command(
        root,
        ['ls-tree', '-r', '-z', tree_oid.decode('ascii')],
    ).stdout
    objects: list[tuple[str, str, int]] = []
    excluded_parts = {
        '.git', '__pycache__', '.pytest_cache', 'node_modules', 'vendor', '.venv',
        'dist', 'build', '.idea', '.vscode', 'htmlcov', '.ruff_cache',
    }
    excluded_files = {'MANIFEST.sha256', '.coverage', '.env', 'err.log'}
    for record in tree.rstrip(b'\0').split(b'\0') if tree else []:
        metadata, encoded_path = record.split(b'\t', 1)
        mode, kind, object_id = metadata.decode('ascii').split(' ')
        relative = os.fsdecode(encoded_path)
        path = PurePosixPath(relative)
        if kind != 'blob' or mode not in {'100644', '100755'}:
            continue
        if path.name in excluded_files or any(part in excluded_parts for part in path.parts):
            continue
        if (path.name == '.env' or path.name.startswith('.env.')) and path.name != '.env.example':
            continue
        if path.name.endswith(('.pem', '.key', '.p12', '.pfx')):
            continue
        if relative.startswith('.grok-stack/runtime/') and relative != '.grok-stack/runtime/.gitkeep':
            continue
        if '20260817-' in relative or path.name.endswith('-pin.env'):
            continue
        if path.name == '.coverage' or path.name.startswith('.coverage.'):
            continue
        if relative.endswith(('.pyc', '.pyo', '.zip', '.sha256')):
            continue
        objects.append((relative, object_id, int(mode, 8)))

    batch = _shipped_git_command(
        root,
        ['cat-file', '--batch'],
        input_bytes=''.join(
            f'{object_id}\n'
            for _relative, object_id, _mode in objects
        ).encode('ascii'),
    ).stdout
    cursor = 0
    sources: dict[str, tuple[bytes, int]] = {}
    for relative, expected_object_id, mode in objects:
        header_end = batch.index(b'\n', cursor)
        object_id, kind, encoded_size = batch[cursor:header_end].decode('ascii').split(' ')
        size = int(encoded_size)
        content_start = header_end + 1
        content_end = content_start + size
        if object_id != expected_object_id or kind != 'blob' or batch[content_end:content_end + 1] != b'\n':
            raise AssertionError(f'invalid git cat-file batch response for {relative}')
        sources[relative] = (batch[content_start:content_end], mode)
        cursor = content_end + 1
    if cursor != len(batch):
        raise AssertionError('unexpected trailing git cat-file batch output')
    return dict(sorted(sources.items()))


class StreamingChecksumPath(type(Path())):
    def read_bytes(self) -> bytes:
        raise AssertionError('archive checksum must stream')


class CloseFailureFile:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    def close(self) -> None:
        self.wrapped.close()
        raise OSError('injected close failure')


class ManifestTests(unittest.TestCase):
    def test_manifest_import_and_legacy_helpers_work_without_posix_open_flags(self) -> None:
        fake_os = types.ModuleType('os')
        unavailable = {'O_CLOEXEC', 'O_DIRECTORY', 'O_NOFOLLOW'}
        for name in dir(os):
            if name not in unavailable:
                setattr(fake_os, name, getattr(os, name))
        module_name = 'manifest_without_posix_open_flags'
        spec = importlib.util.spec_from_file_location(
            module_name,
            ROOT / '.grok-stack/adaptive_grok/manifest.py',
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[module_name] = module
        try:
            with patch.dict(sys.modules, {'os': fake_os}):
                spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('project\n', encoding='utf-8')

            module.generate_manifest(root)

            self.assertEqual(module.verify_manifest(root), [])
            with self.assertRaises(module.ManifestError):
                module.snapshot_files(root)

    def test_included_files_accepts_symlinked_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical_root = Path(tmp) / 'project'
            canonical_root.mkdir()
            (canonical_root / 'README.md').write_text('project\n', encoding='utf-8')
            alias = Path(tmp) / 'project-alias'
            alias.symlink_to(canonical_root, target_is_directory=True)

            files = included_files(alias)

            self.assertEqual(
                [path.relative_to(canonical_root).as_posix() for path in files],
                ['README.md'],
            )

    def test_generate_and_verify_manifest_accept_symlinked_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical_root = Path(tmp) / 'project'
            canonical_root.mkdir()
            (canonical_root / 'README.md').write_text('project\n', encoding='utf-8')
            alias = Path(tmp) / 'project-alias'
            alias.symlink_to(canonical_root, target_is_directory=True)

            generate_manifest(alias)

            self.assertEqual(verify_manifest(alias), [])

    def test_post_open_fstat_failures_close_descriptors_and_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'payload.txt').write_text('payload\n', encoding='utf-8')

            before_root = len(list(Path('/proc/self/fd').iterdir()))
            with patch.object(MANIFEST.os, 'fstat', side_effect=OSError('injected root fstat')):
                with self.assertRaises(MANIFEST.ManifestError):
                    MANIFEST._open_root(root)
            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), before_root)

            directory_flags, _file_flags = MANIFEST._descriptor_flags()
            root_descriptor = os.open(root, directory_flags)
            try:
                before_file = len(list(Path('/proc/self/fd').iterdir()))
                with patch.object(MANIFEST.os, 'fstat', side_effect=OSError('injected file fstat')):
                    with self.assertRaises(MANIFEST.ManifestError):
                        MANIFEST._open_regular_at(root_descriptor, ('payload.txt',), 'payload.txt')
                self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), before_file)
            finally:
                os.close(root_descriptor)

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

    def test_architecture_tooling_schemas_and_templates_are_packaged(self) -> None:
        rels = {path.relative_to(ROOT).as_posix() for path in included_files(ROOT)}
        required = {
            '.grok-stack/adaptive_grok/architecture.py',
            '.grok-stack/adaptive_grok/architecture_diagrams.py',
            '.grok-stack/adaptive_grok/architecture_diff.py',
            '.grok-stack/adaptive_grok/architecture_fitness.py',
            '.grok-stack/templates/architecture/system.example.yaml',
            '.grok-stack/templates/architecture/rules.example.yaml',
            'schemas/architecture-system.schema.json',
            'schemas/architecture-rules.schema.json',
            'scripts/grok_architecture.py',
        }
        self.assertEqual(required - rels, set())


class PackageTests(unittest.TestCase):
    @staticmethod
    def _init_release_repository(root: Path) -> None:
        root.mkdir()
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        (root / 'VERSION').write_text('2.0.13\n', encoding='utf-8')
        (root / 'README.md').write_text('tracked\n', encoding='utf-8')
        (root / '.gitignore').write_text('ignored.txt\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'VERSION', 'README.md', '.gitignore'], cwd=root, check=True)
        subprocess.run(
            [
                'git', '-c', 'user.name=Package Test', '-c', 'user.email=package@example.invalid',
                'commit', '-q', '-m', 'fixture',
            ],
            cwd=root,
            check=True,
        )

    @staticmethod
    def _same_tree_release_commits(root: Path) -> tuple[str, str]:
        PackageTests._init_release_repository(root)
        first = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        subprocess.run(
            [
                'git', '-c', 'user.name=Package Test', '-c', 'user.email=package@example.invalid',
                'commit', '-q', '--allow-empty', '-m', 'second fixture',
            ],
            cwd=root,
            check=True,
        )
        second = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        subprocess.run(['git', 'update-ref', 'HEAD', first, second], cwd=root, check=True)
        return first, second

    @staticmethod
    def _run_release_cli(
        root: Path,
        output: Path,
        *,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        program = """
import importlib.util
import sys
from pathlib import Path

package_path, root, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('isolated_package_stack', package_path)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
module.ROOT = root
sys.argv = [str(package_path), '--output', str(output)]
module.main()
"""
        return subprocess.run(
            [sys.executable, '-c', program, str(ROOT / 'scripts/package_stack.py'), str(root), str(output)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            env=environment,
        )

    @staticmethod
    def _replacement_release_repository(root: Path) -> tuple[str, str]:
        PackageTests._init_release_repository(root)
        (root / 'README.md').write_text('raw-one\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'README.md'], cwd=root, check=True)
        subprocess.run(
            [
                'git', '-c', 'user.name=Package Test', '-c', 'user.email=package@example.invalid',
                'commit', '-q', '-m', 'raw source',
            ],
            cwd=root,
            check=True,
        )
        raw = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        (root / 'README.md').write_text('replacement-two\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'README.md'], cwd=root, check=True)
        subprocess.run(
            [
                'git', '-c', 'user.name=Package Test', '-c', 'user.email=package@example.invalid',
                'commit', '-q', '-m', 'replacement source',
            ],
            cwd=root,
            check=True,
        )
        replacement = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=root,
            text=True,
        ).strip()
        subprocess.run(['git', 'reset', '-q', '--hard', raw], cwd=root, check=True)
        subprocess.run(['git', 'replace', raw, replacement], cwd=root, check=True)
        subprocess.run(['git', 'reset', '-q', '--hard', 'HEAD'], cwd=root, check=True)
        return raw, replacement

    def test_head_release_source_helper_ignores_replace_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._replacement_release_repository(root)

            self.assertEqual((root / 'README.md').read_bytes(), b'replacement-two\n')
            self.assertEqual(
                subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=root),
                b'',
            )
            self.assertEqual(_head_release_sources(root)['README.md'][0], b'raw-one\n')

    def test_release_cli_never_packages_replace_ref_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            raw, _replacement = self._replacement_release_repository(root)
            graft_file = Path(tmp) / 'injected-grafts'
            graft_file.write_text(f'{raw}\n', encoding='ascii')
            output = Path(tmp) / 'publish' / 'project.zip'
            environment = os.environ.copy()
            environment['GIT_GRAFT_FILE'] = str(graft_file)

            result = self._run_release_cli(root, output, environment=environment)

            if result.returncode:
                self.assertIn(b'tracked HEAD', result.stderr)
                self.assertFalse(output.exists())
                self.assertFalse(output.with_suffix('.zip.sha256').exists())
            else:
                with zipfile.ZipFile(output) as archive:
                    packaged = archive.read('adaptive-grok-build-pro/README.md')
                self.assertEqual(packaged, b'raw-one\n')
                self.assertNotEqual(packaged, b'replacement-two\n')

    def test_release_cli_ignores_ambient_git_repository_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            decoy = Path(tmp) / 'decoy'
            self._init_release_repository(root)
            self._init_release_repository(decoy)
            (decoy / 'README.md').write_text('redirected\n', encoding='utf-8')
            subprocess.run(['git', 'add', 'README.md'], cwd=decoy, check=True)
            subprocess.run(
                [
                    'git', '-c', 'user.name=Package Test', '-c',
                    'user.email=package@example.invalid', 'commit', '-q', '-m', 'redirect',
                ],
                cwd=decoy,
                check=True,
            )
            output = Path(tmp) / 'publish' / 'project.zip'
            environment = os.environ.copy()
            environment.update(
                {
                    'GIT_COMMON_DIR': str(decoy / '.git'),
                    'GIT_CONFIG_COUNT': '1',
                    'GIT_CONFIG_KEY_0': 'core.abbrev',
                    'GIT_CONFIG_VALUE_0': '4',
                    'GIT_DIR': str(decoy / '.git'),
                    'GIT_INDEX_FILE': str(decoy / '.git' / 'index'),
                    'GIT_NAMESPACE': 'redirected',
                    'GIT_OBJECT_DIRECTORY': str(decoy / '.git' / 'objects'),
                    'GIT_WORK_TREE': str(decoy),
                }
            )

            result = self._run_release_cli(root, output, environment=environment)

            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    archive.read('adaptive-grok-build-pro/README.md'),
                    b'tracked\n',
                )

    def test_release_git_invocation_trusts_only_canonical_root_for_different_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            canonical_root = root.resolve(strict=True)
            command, environment = PACKAGE._git_invocation(
                root,
                ['rev-parse', '--verify', 'HEAD^{commit}'],
            )
            trust_entries = [
                argument
                for argument in command
                if argument.startswith('safe.directory=')
            ]
            self.assertEqual(
                trust_entries,
                [f'safe.directory={canonical_root}'],
            )
            self.assertFalse(any(name.startswith('GIT_') for name in environment if name not in {
                'GIT_CONFIG_COUNT',
                'GIT_CONFIG_GLOBAL',
                'GIT_CONFIG_NOSYSTEM',
                'GIT_CONFIG_SYSTEM',
                'GIT_GRAFT_FILE',
                'GIT_NO_REPLACE_OBJECTS',
                'GIT_OPTIONAL_LOCKS',
            }))
            environment['GIT_TEST_ASSUME_DIFFERENT_OWNER'] = '1'
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                env=environment,
            )
            self.assertEqual(
                result.returncode,
                0,
                result.stderr.decode('utf-8', errors='replace'),
            )

    def test_shipped_head_reader_trusts_only_canonical_root_for_different_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            canonical_root = root.resolve(strict=True)
            real_environment = _shipped_git_environment
            real_run = subprocess.run
            commands: list[tuple[str, ...]] = []

            def different_owner_environment() -> dict[str, str]:
                return {
                    **real_environment(),
                    'GIT_TEST_ASSUME_DIFFERENT_OWNER': '1',
                }

            def capture(command, **kwargs):
                commands.append(tuple(command))
                return real_run(command, **kwargs)

            with (
                patch(
                    f'{__name__}._shipped_git_environment',
                    side_effect=different_owner_environment,
                ),
                patch.object(subprocess, 'run', side_effect=capture),
            ):
                sources = _head_release_sources(root)

            self.assertEqual(sources['README.md'][0], b'tracked\n')
            self.assertTrue(commands)
            for command in commands:
                with self.subTest(command=command):
                    trust_entries = [
                        argument
                        for argument in command
                        if argument.startswith('safe.directory=')
                    ]
                    self.assertEqual(
                        trust_entries,
                        [f'safe.directory={canonical_root}'],
                    )

    def test_release_cli_keeps_linked_worktree_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repository = Path(tmp) / 'repository'
            linked = Path(tmp) / 'linked'
            self._init_release_repository(repository)
            subprocess.run(
                ['git', 'worktree', 'add', '-q', '-b', 'linked-fixture', str(linked)],
                cwd=repository,
                check=True,
            )
            output = Path(tmp) / 'publish' / 'project.zip'

            result = self._run_release_cli(linked, output)

            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    archive.read('adaptive-grok-build-pro/README.md'),
                    b'tracked\n',
                )

    def test_release_cli_rejects_tracked_source_as_output_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            root.chmod(0o700)
            output = root / 'README.md'
            original = output.read_bytes()

            result = self._run_release_cli(root, output)

            self.assertEqual(output.read_bytes(), original, result.stderr.decode('utf-8', errors='replace'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'overlaps included tracked source', result.stderr)
            self.assertEqual(
                subprocess.check_output(
                    ['git', 'status', '--porcelain=v1', '--untracked-files=all'],
                    cwd=root,
                ),
                b'',
            )

    def test_release_cli_rejects_symlink_alias_to_tracked_source_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            root.chmod(0o700)
            source = root / 'README.md'
            original = source.read_bytes()
            output = Path(tmp) / 'readme-alias.zip'
            output.symlink_to(source)

            result = self._run_release_cli(root, output)

            self.assertEqual(source.read_bytes(), original, result.stderr.decode('utf-8', errors='replace'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'overlaps included tracked source', result.stderr)
            self.assertTrue(output.is_symlink())
            self.assertEqual(
                subprocess.check_output(
                    ['git', 'status', '--porcelain=v1', '--untracked-files=all'],
                    cwd=root,
                ),
                b'',
            )

    def test_release_cli_rejects_head_move_immediately_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            first, second = self._same_tree_release_commits(root)
            output = Path(tmp) / 'publish' / 'project.zip'
            real_validate = PACKAGE._validate_temporary_name
            validation_count = 0

            def advance_head_after_archive_validation(directory, temporary):
                nonlocal validation_count
                real_validate(directory, temporary)
                validation_count += 1
                if validation_count == 2:
                    subprocess.run(
                        ['git', 'update-ref', 'HEAD', second, first],
                        cwd=root,
                        check=True,
                    )

            failure: PACKAGE.PackageError | None = None
            with (
                patch.object(PACKAGE, 'ROOT', root),
                patch.object(sys, 'argv', ['package_stack.py', '--output', str(output)]),
                patch.object(
                    PACKAGE,
                    '_validate_temporary_name',
                    side_effect=advance_head_after_archive_validation,
                ),
            ):
                try:
                    PACKAGE.main()
                except PACKAGE.PackageError as exc:
                    failure = exc

            self.assertIsNotNone(failure)
            self.assertIn('tracked HEAD changed', str(failure))
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.zip.sha256').exists())
            self.assertEqual(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), second)
            self.assertEqual(subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=root), b'')

    def test_release_cli_rejects_source_change_after_stream_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            output = Path(tmp) / 'publish' / 'project.zip'
            source = root / 'README.md'
            real_stream = PACKAGE.stream_entry

            def mutate_after_source_stream(stream_root, entry, destination):
                real_stream(stream_root, entry, destination)
                if entry.relative_path == 'README.md':
                    source.write_text('changed during packaging\n', encoding='utf-8')

            failure: PACKAGE.PackageError | None = None
            with (
                patch.object(PACKAGE, 'ROOT', root),
                patch.object(sys, 'argv', ['package_stack.py', '--output', str(output)]),
                patch.object(PACKAGE, 'stream_entry', side_effect=mutate_after_source_stream),
            ):
                try:
                    PACKAGE.main()
                except PACKAGE.PackageError as exc:
                    failure = exc

            self.assertIsNotNone(failure)
            self.assertIn('tracked HEAD source changed', str(failure))
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.zip.sha256').exists())

    def test_release_cli_restores_preexisting_outputs_when_head_moves_after_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            first, second = self._same_tree_release_commits(root)
            publish = Path(tmp) / 'publish'
            publish.mkdir(mode=0o700)
            output = publish / 'project.zip'
            sidecar = publish / 'project.zip.sha256'
            old_archive = b'previous archive bytes\n'
            old_sidecar = b'previous checksum bytes\n'
            output.write_bytes(old_archive)
            sidecar.write_bytes(old_sidecar)
            real_replace = PACKAGE.os.replace
            replacement_count = 0

            def advance_head_after_publication(*args, **kwargs):
                nonlocal replacement_count
                result = real_replace(*args, **kwargs)
                replacement_count += 1
                if replacement_count == 2:
                    subprocess.run(
                        ['git', 'update-ref', 'HEAD', second, first],
                        cwd=root,
                        check=True,
                    )
                return result

            failure: PACKAGE.PackageError | None = None
            with (
                patch.object(PACKAGE, 'ROOT', root),
                patch.object(sys, 'argv', ['package_stack.py', '--output', str(output)]),
                patch.object(PACKAGE.os, 'replace', side_effect=advance_head_after_publication),
            ):
                try:
                    PACKAGE.main()
                except PACKAGE.PackageError as exc:
                    failure = exc

            self.assertIsNotNone(failure)
            self.assertIn('tracked HEAD changed', str(failure))
            self.assertEqual(output.read_bytes(), old_archive)
            self.assertEqual(sidecar.read_bytes(), old_sidecar)
            self.assertEqual(set(publish.iterdir()), {output, sidecar})
            self.assertEqual(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), second)
            self.assertEqual(subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=root), b'')

    def test_release_cli_restores_preexisting_outputs_when_sidecar_publication_rename_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            publish = Path(tmp) / 'publish'
            publish.mkdir(mode=0o700)
            output = publish / 'project.zip'
            sidecar = publish / 'project.zip.sha256'
            old_archive = b'previous archive bytes\n'
            old_sidecar = b'previous checksum bytes\n'
            output.write_bytes(old_archive)
            sidecar.write_bytes(old_sidecar)
            real_replace = PACKAGE.os.replace
            replacement_count = 0

            def fail_sidecar_publication(*args, **kwargs):
                nonlocal replacement_count
                replacement_count += 1
                if replacement_count == 2:
                    raise OSError('injected sidecar publication rename failure')
                return real_replace(*args, **kwargs)

            with (
                patch.object(PACKAGE, 'ROOT', root),
                patch.object(sys, 'argv', ['package_stack.py', '--output', str(output)]),
                patch.object(PACKAGE.os, 'replace', side_effect=fail_sidecar_publication),
            ):
                with self.assertRaisesRegex(OSError, 'injected sidecar publication rename failure'):
                    PACKAGE.main()

            self.assertEqual(replacement_count, 3)
            self.assertEqual(output.read_bytes(), old_archive)
            self.assertEqual(sidecar.read_bytes(), old_sidecar)
            self.assertEqual(set(publish.iterdir()), {output, sidecar})
            self.assertEqual(subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=root), b'')

    def test_release_cli_packages_only_clean_tracked_head_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            (root / 'ignored.txt').write_text('ignored\n', encoding='utf-8')
            (root / 'untracked.txt').write_text('untracked\n', encoding='utf-8')
            output = Path(tmp) / 'publish' / 'project.zip'

            with (
                patch.object(PACKAGE, 'ROOT', root),
                patch.object(sys, 'argv', ['package_stack.py', '--output', str(output)]),
            ):
                PACKAGE.main()

            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    archive.namelist(),
                    [
                        'adaptive-grok-build-pro/.gitignore',
                        'adaptive-grok-build-pro/MANIFEST.sha256',
                        'adaptive-grok-build-pro/README.md',
                        'adaptive-grok-build-pro/VERSION',
                    ],
                )

    def test_release_cli_derives_deterministic_member_modes_from_git_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            script = root / 'scripts/run.sh'
            script.parent.mkdir()
            script.write_text('#!/bin/sh\necho ok\n', encoding='utf-8')
            script.chmod(0o755)
            subprocess.run(['git', 'add', 'scripts/run.sh'], cwd=root, check=True)
            subprocess.run(
                [
                    'git', '-c', 'user.name=Package Test', '-c',
                    'user.email=package@example.invalid', 'commit', '-q', '-m',
                    'add executable fixture',
                ],
                cwd=root,
                check=True,
            )
            clone = Path(tmp) / 'clone'
            subprocess.run(
                ['git', 'clone', '--no-local', '-q', str(root), str(clone)],
                check=True,
            )
            for revision in ('HEAD^{commit}', 'HEAD^{tree}'):
                self.assertEqual(
                    subprocess.check_output(['git', 'rev-parse', revision], cwd=root),
                    subprocess.check_output(['git', 'rev-parse', revision], cwd=clone),
                )
            (root / 'README.md').chmod(0o600)
            script.chmod(0o700)
            (clone / 'README.md').chmod(0o664)
            (clone / 'scripts/run.sh').chmod(0o775)
            self.assertEqual(
                subprocess.check_output(
                    ['git', 'status', '--porcelain=v1'], cwd=root
                ),
                b'',
            )
            self.assertEqual(
                subprocess.check_output(
                    ['git', 'status', '--porcelain=v1'], cwd=clone
                ),
                b'',
            )
            first = Path(tmp) / 'first.zip'
            second = Path(tmp) / 'second.zip'

            first_result = self._run_release_cli(root, first)
            second_result = self._run_release_cli(clone, second)

            self.assertEqual(
                first_result.returncode,
                0,
                first_result.stderr.decode('utf-8', errors='replace'),
            )
            self.assertEqual(
                second_result.returncode,
                0,
                second_result.stderr.decode('utf-8', errors='replace'),
            )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                prefix = 'adaptive-grok-build-pro/'
                self.assertEqual(
                    archive.getinfo(f'{prefix}README.md').external_attr >> 16,
                    0o100644,
                )
                self.assertEqual(
                    archive.getinfo(f'{prefix}scripts/run.sh').external_attr >> 16,
                    0o100755,
                )

    def test_release_cli_rejects_git_executable_missing_from_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            script = root / 'run.sh'
            script.write_text('#!/bin/sh\necho ok\n', encoding='utf-8')
            script.chmod(0o755)
            subprocess.run(['git', 'add', 'run.sh'], cwd=root, check=True)
            subprocess.run(
                [
                    'git', '-c', 'user.name=Package Test', '-c',
                    'user.email=package@example.invalid', 'commit', '-q', '-m',
                    'add executable fixture',
                ],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ['git', 'config', 'core.filemode', 'false'], cwd=root, check=True
            )
            script.chmod(0o644)

            result = self._run_release_cli(root, Path(tmp) / 'project.zip')

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'release source mode differs from tracked HEAD', result.stderr)

    def test_release_inventory_includes_only_regular_git_blob_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            executable = root / 'run.sh'
            executable.write_text('#!/bin/sh\necho ok\n', encoding='utf-8')
            executable.chmod(0o755)
            (root / 'alias').symlink_to('README.md')
            head = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=root, text=True
            ).strip()
            subprocess.run(['git', 'add', 'run.sh', 'alias'], cwd=root, check=True)
            subprocess.run(
                ['git', 'update-index', '--add', '--cacheinfo', f'160000,{head},nested'],
                cwd=root,
                check=True,
            )
            subprocess.run(
                [
                    'git', '-c', 'user.name=Package Test', '-c',
                    'user.email=package@example.invalid', 'commit', '-q', '-m',
                    'add mode fixtures',
                ],
                cwd=root,
                check=True,
            )
            tree = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD^{tree}'], cwd=root, text=True
            ).strip()

            files = PACKAGE._tracked_head_files(root, tree)

            self.assertEqual(
                {item.relative_path: item.mode for item in files},
                {
                    '.gitignore': 0o100644,
                    'README.md': 0o100644,
                    'VERSION': 0o100644,
                    'run.sh': 0o100755,
                },
            )

    def test_release_cli_allows_explicit_tracked_excluded_package_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            root.chmod(0o700)
            packages = root / 'packages'
            packages.mkdir(mode=0o700)
            output = packages / 'project.zip'
            sidecar = packages / 'project.zip.sha256'
            output.write_bytes(b'old archive\n')
            sidecar.write_bytes(b'old checksum\n')
            subprocess.run(['git', 'add', 'packages'], cwd=root, check=True)
            subprocess.run(
                [
                    'git', '-c', 'user.name=Package Test', '-c', 'user.email=package@example.invalid',
                    'commit', '-q', '-m', 'tracked package fixture',
                ],
                cwd=root,
                check=True,
            )

            result = self._run_release_cli(root, output)

            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            self.assertEqual(sidecar.read_text(encoding='utf-8'), f'{digest}  project.zip\n')
            self.assertEqual(
                set(
                    subprocess.check_output(
                        ['git', 'status', '--porcelain=v1'],
                        cwd=root,
                        text=True,
                    ).splitlines()
                ),
                {' M packages/project.zip', ' M packages/project.zip.sha256'},
            )

    def test_release_cli_rejects_modified_tracked_head_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            self._init_release_repository(root)
            (root / 'README.md').write_text('modified after commit\n', encoding='utf-8')
            output = Path(tmp) / 'publish' / 'project.zip'

            with (
                patch.object(PACKAGE, 'ROOT', root),
                patch.object(sys, 'argv', ['package_stack.py', '--output', str(output)]),
                self.assertRaisesRegex(PACKAGE.PackageError, 'tracked HEAD'),
            ):
                PACKAGE.main()

            self.assertFalse(output.exists())

    def test_archive_rejects_private_parent_below_writable_nonsticky_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            unsafe_ancestor = Path(tmp) / 'unsafe'
            unsafe_ancestor.mkdir()
            unsafe_ancestor.chmod(0o777)
            publish = unsafe_ancestor / 'publish'
            publish.mkdir(mode=0o700)
            output = publish / 'project.zip'

            with self.assertRaises(PACKAGE.PackageError):
                PACKAGE.write_archive(root, output)

            self.assertEqual(list(publish.iterdir()), [])

    def test_archive_accepts_private_parent_below_root_owned_sticky_tmp(self) -> None:
        with tempfile.TemporaryDirectory(dir='/tmp') as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            publish = Path(tmp) / 'publish'
            publish.mkdir(mode=0o700)
            output = publish / 'project.zip'

            PACKAGE.write_archive(root, output)

            self.assertTrue(output.is_file())
            self.assertTrue((publish / 'project.zip.sha256').is_file())

    def test_archive_replaces_hardlink_sidecar_without_mutating_external_inode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            publish = Path(tmp) / 'publish'
            publish.mkdir(mode=0o700)
            output = publish / 'project.zip'
            sidecar = publish / 'project.zip.sha256'
            external = Path(tmp) / 'external.txt'
            sentinel = b'external-hardlink-sentinel\n'
            external.write_bytes(sentinel)
            os.link(external, sidecar)

            digest = PACKAGE.write_archive(root, output)

            self.assertEqual(external.read_bytes(), sentinel)
            self.assertNotEqual(sidecar.stat().st_ino, external.stat().st_ino)
            self.assertEqual(sidecar.read_text(encoding='utf-8'), f'{digest}  project.zip\n')

    def test_archive_replaces_fifo_sidecar_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            publish = Path(tmp) / 'publish'
            publish.mkdir(mode=0o700)
            output = publish / 'project.zip'
            sidecar = publish / 'project.zip.sha256'
            os.mkfifo(sidecar)
            command = (
                'import sys; from pathlib import Path; '
                'from scripts.package_stack import write_archive; '
                'write_archive(Path(sys.argv[1]), Path(sys.argv[2]))'
            )

            completed = subprocess.run(
                [sys.executable, '-c', command, str(root), str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(stat.S_ISREG(sidecar.lstat().st_mode))

    def test_archive_replaces_symlink_sidecar_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            sidecar = Path(tmp) / 'project.zip.sha256'
            external = Path(tmp) / 'external.txt'
            sentinel = b'external-symlink-sentinel\n'
            external.write_bytes(sentinel)
            sidecar.symlink_to(external)

            digest = PACKAGE.write_archive(root, output)

            self.assertEqual(external.read_bytes(), sentinel)
            self.assertTrue(stat.S_ISREG(sidecar.lstat().st_mode))
            self.assertEqual(sidecar.read_text(encoding='utf-8'), f'{digest}  project.zip\n')

    def test_archive_rejects_directory_sidecar_before_output_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            sidecar = Path(tmp) / 'project.zip.sha256'
            sidecar.mkdir()

            with self.assertRaises(PACKAGE.PackageError):
                PACKAGE.write_archive(root, output)

            self.assertFalse(output.exists())
            self.assertTrue(sidecar.is_dir())
            self.assertEqual(list(Path(tmp).glob('.project.zip.sha256.*.tmp')), [])

    def test_archive_replaces_regular_sidecar_and_preserves_its_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            sidecar = Path(tmp) / 'project.zip.sha256'
            sidecar.write_text('old checksum\n', encoding='utf-8')
            sidecar.chmod(0o640)

            digest = PACKAGE.write_archive(root, output)

            self.assertEqual(stat.S_IMODE(sidecar.stat().st_mode), 0o640)
            self.assertEqual(sidecar.read_text(encoding='utf-8'), f'{digest}  project.zip\n')

    def test_sidecar_temp_swap_fails_without_target_mutation_or_temp_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            sidecar = Path(tmp) / 'project.zip.sha256'
            external = Path(tmp) / 'external.txt'
            sentinel = b'external-sidecar-swap-sentinel\n'
            external.write_bytes(sentinel)
            real_validate = PACKAGE._validate_temporary_name
            validation_count = 0

            def swap_sidecar_temp(directory, temporary):
                nonlocal validation_count
                real_validate(directory, temporary)
                validation_count += 1
                if validation_count == 3:
                    os.unlink(temporary.name, dir_fd=directory.descriptor)
                    os.symlink(external, temporary.name, dir_fd=directory.descriptor)

            with patch.object(
                PACKAGE,
                '_validate_temporary_name',
                side_effect=swap_sidecar_temp,
            ):
                with self.assertRaises(PACKAGE.PackageError):
                    PACKAGE.write_archive(root, output)

            self.assertEqual(validation_count, 3)
            self.assertEqual(external.read_bytes(), sentinel)
            self.assertTrue(output.is_file())
            self.assertFalse(sidecar.exists())
            self.assertEqual(list(Path(tmp).glob('.project.zip.sha256.*.tmp')), [])

    def test_archive_cleanup_retains_primary_error_when_close_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            real_creator = PACKAGE._create_temporary_archive
            real_binding_check = PACKAGE._validate_output_directory_binding
            binding_checks = 0

            def wrap_temporary(*args, **kwargs):
                temporary = real_creator(*args, **kwargs)
                return temporary._replace(file=CloseFailureFile(temporary.file))

            def fail_before_publication(directory):
                nonlocal binding_checks
                real_binding_check(directory)
                binding_checks += 1
                if binding_checks == 3:
                    raise PACKAGE.PackageError('injected primary publication failure')

            with (
                patch.object(PACKAGE, '_create_temporary_archive', side_effect=wrap_temporary),
                patch.object(
                    PACKAGE,
                    '_validate_output_directory_binding',
                    side_effect=fail_before_publication,
                ),
            ):
                with self.assertRaisesRegex(
                    PACKAGE.PackageError,
                    'injected primary publication failure',
                ) as raised:
                    PACKAGE.write_archive(root, output)

            self.assertTrue(any('close failure' in note for note in raised.exception.__notes__))
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(tmp).glob('.project.zip.*.tmp')), [])

    def test_missing_default_output_parent_is_private_under_restrictive_umasks(self) -> None:
        for mask in (0o002, 0o022, 0o700, 0o777):
            with self.subTest(mask=oct(mask)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'project'
                root.mkdir(mode=0o700)
                root.chmod(0o700)
                (root / 'README.md').write_text('hello\n', encoding='utf-8')
                (root / 'VERSION').write_text('9.9.9\n', encoding='utf-8')
                output = root / PACKAGE._default_output(root)
                previous_umask = os.umask(mask)
                try:
                    PACKAGE.write_archive(root, output)
                finally:
                    os.umask(previous_umask)

                self.assertEqual(output, root / 'dist/adaptive-grok-build-pro-v9.9.9.zip')
                self.assertEqual(stat.S_IMODE(output.parent.stat().st_mode), 0o700)
                self.assertTrue(output.is_file())

    def test_nested_output_parents_are_exactly_private_under_umask_0777(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir(mode=0o700)
            root.chmod(0o700)
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            first = root / 'missing'
            second = first / 'nested'
            output = second / 'project.zip'
            previous_umask = os.umask(0o777)
            try:
                PACKAGE.write_archive(root, output)
            finally:
                os.umask(previous_umask)

            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(second.stat().st_mode), 0o700)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix('.zip.sha256').is_file())

    def test_created_output_parents_are_removed_when_binding_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir(mode=0o700)
            root.chmod(0o700)
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            created_parent = root / 'missing' / 'nested'
            output = created_parent / 'project.zip'

            previous_umask = os.umask(0o777)
            try:
                with patch.object(
                    PACKAGE,
                    '_open_output_directory',
                    side_effect=PACKAGE.PackageError('injected output binding failure'),
                ):
                    with self.assertRaisesRegex(
                        PACKAGE.PackageError,
                        'injected output binding failure',
                    ):
                        PACKAGE.write_archive(root, output)
            finally:
                os.umask(previous_umask)

            self.assertFalse((root / 'missing').exists())

    def test_archive_rejects_group_or_world_writable_output_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            for mode in (0o770, 0o702):
                with self.subTest(mode=oct(mode)):
                    publish = Path(tmp) / f'publish-{mode:o}'
                    publish.mkdir()
                    publish.chmod(mode)
                    output = publish / 'project.zip'

                    with self.assertRaises(PACKAGE.PackageError):
                        PACKAGE.write_archive(root, output)

                    self.assertFalse(output.exists())
                    self.assertFalse((publish / 'project.zip.sha256').exists())
                    self.assertEqual(list(publish.iterdir()), [])

    def test_open_output_directory_rejects_foreign_leaf_owner_and_closes_fd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            publish = Path(tmp) / 'publish'
            publish.mkdir(mode=0o700)
            output = publish / 'project.zip'
            real_fstat = os.fstat
            descriptor_count = len(list(Path('/proc/self/fd').iterdir()))
            opened = None

            def foreign_leaf_owner(descriptor):
                metadata = real_fstat(descriptor)
                return types.SimpleNamespace(
                    st_mode=metadata.st_mode,
                    st_uid=os.geteuid() + 1,
                    st_dev=metadata.st_dev,
                    st_ino=metadata.st_ino,
                )

            try:
                with patch.object(PACKAGE.os, 'fstat', side_effect=foreign_leaf_owner):
                    with self.assertRaisesRegex(
                        PACKAGE.PackageError,
                        'archive output parent must be owned by the effective user and private',
                    ):
                        opened = PACKAGE._open_output_directory(output)
            finally:
                if opened is not None:
                    os.close(opened.descriptor)

            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), descriptor_count)
            self.assertEqual(list(publish.iterdir()), [])

    def test_archive_parent_relocation_fails_without_redirecting_or_leaking_temp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            publish = Path(tmp) / 'publish'
            publish.mkdir(mode=0o700)
            relocated = Path(tmp) / 'relocated-publish'
            output = publish / 'project.zip'
            real_creator = PACKAGE._create_temporary_archive

            def relocate_after_create(*args, **kwargs):
                temporary = real_creator(*args, **kwargs)
                publish.rename(relocated)
                publish.mkdir(mode=0o700)
                return temporary

            with patch.object(
                PACKAGE,
                '_create_temporary_archive',
                side_effect=relocate_after_create,
            ):
                with self.assertRaises(PACKAGE.PackageError):
                    PACKAGE.write_archive(root, output)

            self.assertEqual(list(publish.iterdir()), [])
            self.assertEqual(list(relocated.iterdir()), [])

    def test_packaged_installer_materializes_new_target_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "project.zip"
            PACKAGE.write_archive(ROOT, archive_path)
            extracted = Path(tmp) / "extracted"
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extracted)
            source = extracted / "adaptive-grok-build-pro"
            install_spec = importlib.util.spec_from_file_location(
                "packaged_install_into", source / "scripts/install_into.py"
            )
            installer = importlib.util.module_from_spec(install_spec)
            assert install_spec and install_spec.loader
            sys.modules[install_spec.name] = installer
            install_spec.loader.exec_module(installer)
            target = Path(tmp) / "installed"
            plan = installer.materialize_new(source, target)
            self.assertEqual(plan["target_state"], "absent")
            self.assertTrue((target / "scripts/grok_verify.py").is_file())
            self.assertFalse((target / "architecture/system.yaml").exists())
            self.assertFalse((target / "architecture/rules.yaml").exists())
            self.assertFalse((target / "architecture/adoption.json").exists())

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


    def test_scratch_build_pin_env_and_leftover_change_are_not_packaged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('ok\n', encoding='utf-8')
            scratch = root / 'build'
            scratch.mkdir()
            (scratch / 'adaptive-trust-ci-pin.env').write_text('SECRET=1\n', encoding='utf-8')
            leftover = root / 'engineering/changes/20260817-user-query-leave-old'
            leftover.mkdir(parents=True)
            (leftover / 'brief.md').write_text('nope\n', encoding='utf-8')
            rels = [path.relative_to(root).as_posix() for path in included_files(root)]
            self.assertIn('README.md', rels)
            self.assertNotIn('build/adaptive-trust-ci-pin.env', rels)
            self.assertFalse(any('20260817-' in rel for rel in rels))

    def test_published_zip_matches_immutable_release_record_and_embedded_manifest(self) -> None:
        state = json.loads((ROOT / 'PROJECT_STATE.json').read_text(encoding='utf-8'))
        published = state['published_release']
        version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(version, '2.0.13')
        self.assertEqual(state['product_version'], version)
        self.assertEqual(published['tag'], f'v{version}')
        artifact = published['artifact']
        self.assertEqual(artifact['binding'], 'immutable_release_tag')
        expected_relative = f'packages/adaptive-grok-build-pro-v{version}.zip'
        self.assertEqual(artifact['path'], expected_relative)
        expected_digest = '3d5179f589c507143f4b93a98d2518e37e470e8566a62f77b31c35743ed8240c'
        self.assertEqual(artifact['sha256'], expected_digest)

        zip_path = ROOT / expected_relative
        sidecar_path = zip_path.with_suffix('.zip.sha256')
        self.assertTrue(zip_path.is_file())
        self.assertTrue(sidecar_path.is_file())
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        self.assertEqual(digest, expected_digest)
        self.assertEqual(
            sidecar_path.read_text(encoding='ascii'),
            f'{expected_digest}  {zip_path.name}\n',
        )

        with zipfile.ZipFile(zip_path) as archive:
            self.assertIsNone(archive.testzip())
            names = archive.namelist()
            self.assertEqual(names, sorted(names))
            self.assertEqual(len(names), len(set(names)))
            prefix = 'adaptive-grok-build-pro/'
            self.assertTrue(all(name.startswith(prefix) for name in names))
            manifest_member = f'{prefix}MANIFEST.sha256'
            self.assertIn(manifest_member, names)
            manifest = archive.read(manifest_member).decode('utf-8')
            self.assertTrue(manifest.endswith('\n'))
            entries: list[tuple[str, str]] = []
            for line in manifest.splitlines():
                match = re.fullmatch(r'([0-9a-f]{64})  ([^\\\x00]+)', line)
                self.assertIsNotNone(match, line)
                assert match is not None
                relative = match.group(2)
                path = PurePosixPath(relative)
                self.assertFalse(path.is_absolute())
                self.assertNotIn('..', path.parts)
                self.assertNotIn('.', path.parts)
                self.assertNotEqual(relative, 'MANIFEST.sha256')
                entries.append((relative, match.group(1)))
            relative_names = [relative for relative, _digest in entries]
            self.assertEqual(relative_names, sorted(relative_names))
            self.assertEqual(len(relative_names), len(set(relative_names)))
            self.assertEqual(
                {f'{prefix}{relative}' for relative in relative_names},
                set(names) - {manifest_member},
            )
            for relative, member_digest in entries:
                member = f'{prefix}{relative}'
                self.assertEqual(
                    hashlib.sha256(archive.read(member)).hexdigest(),
                    member_digest,
                    relative,
                )
            for info in archive.infolist():
                self.assertEqual(info.create_system, 3, info.filename)
                self.assertIn(
                    info.external_attr >> 16,
                    {stat.S_IFREG | 0o644, stat.S_IFREG | 0o755},
                    info.filename,
                )
            self.assertEqual(
                archive.getinfo(manifest_member).external_attr >> 16,
                stat.S_IFREG | 0o644,
            )
            self.assertEqual(
                archive.read(f'{prefix}VERSION').decode('utf-8').strip(),
                version,
            )
            self.assertFalse(any('.github/workflows/' in name for name in names))
            self.assertNotIn(f'{prefix}.github/dependabot.yml', names)
            self.assertNotIn(f'{prefix}.grok-stack/templates/ci/github-actions.yml', names)

    def test_write_archive_preserves_source_manifest_and_embeds_current_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            source_manifest = root / 'MANIFEST.sha256'
            original = b'pre-existing source manifest\n'
            source_manifest.write_bytes(original)
            archive_path = Path(tmp) / 'project.zip'
            PACKAGE.write_archive(root, archive_path)
            self.assertEqual(source_manifest.read_bytes(), original)
            with zipfile.ZipFile(archive_path) as archive:
                member = 'adaptive-grok-build-pro/MANIFEST.sha256'
                self.assertIn(member, archive.namelist())
                readme_digest = hashlib.sha256(b'hello\n').hexdigest()
                expected = f'{readme_digest}  README.md\n'.encode('ascii')
                self.assertEqual(archive.read(member), expected)

    def test_archive_excludes_external_secret_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            secret = Path(tmp) / '.env'
            sentinel = b'external-secret-sentinel\n'
            secret.write_bytes(sentinel)
            (root / 'keep.txt').write_text('keep\n', encoding='utf-8')
            (root / 'innocent.txt').symlink_to(secret)
            archive_path = Path(tmp) / 'project.zip'

            PACKAGE.write_archive(root, archive_path)

            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertNotIn('adaptive-grok-build-pro/innocent.txt', names)
                self.assertNotIn(sentinel, [archive.read(name) for name in names])

    def test_archive_fails_closed_when_file_is_replaced_after_manifest_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            victim = root / 'payload.txt'
            victim.write_bytes(b'before\n')
            archive_path = Path(tmp) / 'project.zip'
            real_render = PACKAGE.render_manifest

            def replace_after_render(*args, **kwargs):
                rendered = real_render(*args, **kwargs)
                victim.unlink()
                victim.write_bytes(b'after\n')
                return rendered

            with patch.object(PACKAGE, 'render_manifest', side_effect=replace_after_render):
                with self.assertRaises(RuntimeError):
                    PACKAGE.write_archive(root, archive_path)
            self.assertEqual(victim.read_bytes(), b'after\n')
            self.assertFalse(archive_path.exists())

    def test_archive_checksum_streams_without_output_read_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            archive_path = StreamingChecksumPath(tmp) / 'project.zip'

            digest = PACKAGE.write_archive(root, archive_path)

            with archive_path.open('rb') as archive_file:
                expected = hashlib.file_digest(archive_file, 'sha256').hexdigest()
            self.assertEqual(digest, expected)
            self.assertEqual(
                (archive_path.parent / f'{archive_path.name}.sha256').read_text(encoding='utf-8'),
                f'{expected}  {archive_path.name}\n',
            )

    def test_archive_temp_path_swap_fails_without_touching_external_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            external = Path(tmp) / 'external.bin'
            sentinel = b'external-target-sentinel\n'
            external.write_bytes(sentinel)
            real_creator = getattr(PACKAGE, '_create_temporary_archive', None)

            def swap_after_create(directory, output_name):
                if real_creator is None:
                    raise AssertionError('secure temporary creator is unavailable')
                temporary = real_creator(directory, output_name)
                os.unlink(temporary.name, dir_fd=directory.descriptor)
                os.symlink(external, temporary.name, dir_fd=directory.descriptor)
                return temporary

            with patch.object(
                PACKAGE,
                '_create_temporary_archive',
                side_effect=swap_after_create,
                create=True,
            ):
                with self.assertRaises(RuntimeError):
                    PACKAGE.write_archive(root, output)

            self.assertEqual(external.read_bytes(), sentinel)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(tmp).glob(f'.{output.name}.*.tmp')), [])

    def test_archive_final_validation_swap_cannot_publish_replacement_inode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            external = Path(tmp) / 'external.bin'
            sentinel = b'external-target-sentinel\n'
            external.write_bytes(sentinel)
            real_validate = PACKAGE._validate_temporary_name
            validate_calls = 0

            def swap_after_final_validation(directory, temporary):
                nonlocal validate_calls
                real_validate(directory, temporary)
                validate_calls += 1
                if validate_calls == 2:
                    os.unlink(temporary.name, dir_fd=directory.descriptor)
                    os.symlink(external, temporary.name, dir_fd=directory.descriptor)

            with patch.object(
                PACKAGE,
                '_validate_temporary_name',
                side_effect=swap_after_final_validation,
            ):
                with self.assertRaises(RuntimeError):
                    PACKAGE.write_archive(root, output)

            self.assertEqual(validate_calls, 2)
            self.assertEqual(external.read_bytes(), sentinel)
            self.assertFalse(output.exists())
            self.assertFalse((Path(tmp) / 'project.zip.sha256').exists())
            self.assertEqual(list(Path(tmp).glob(f'.{output.name}.*.tmp')), [])

    def test_new_archive_uses_normal_create_mode_under_umask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            previous_umask = os.umask(0o027)
            try:
                PACKAGE.write_archive(root, output)
            finally:
                os.umask(previous_umask)

            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o640)

    def test_replaced_archive_preserves_existing_permission_bits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'
            root.mkdir()
            (root / 'README.md').write_text('hello\n', encoding='utf-8')
            output = Path(tmp) / 'project.zip'
            output.write_bytes(b'old archive\n')
            output.chmod(0o664)
            previous_umask = os.umask(0o077)
            try:
                PACKAGE.write_archive(root, output)
            finally:
                os.umask(previous_umask)

            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o664)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())

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
