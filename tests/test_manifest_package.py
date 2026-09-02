from __future__ import annotations

import hashlib
import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok import manifest as MANIFEST
from adaptive_grok.manifest import generate_manifest, included_files, verify_manifest

SPEC = importlib.util.spec_from_file_location('package_stack', ROOT / 'scripts/package_stack.py')
PACKAGE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PACKAGE)


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

    def test_shipped_zip_exactly_matches_current_included_source(self) -> None:
        version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(version, '2.0.13')
        source_files = included_files(ROOT)
        rels = [path.relative_to(ROOT).as_posix() for path in source_files]
        self.assertFalse(any(rel.startswith('.github/workflows/') for rel in rels))
        self.assertNotIn('.github/dependabot.yml', rels)
        self.assertNotIn('.grok-stack/templates/ci/github-actions.yml', rels)
        zip_path = ROOT / 'packages' / f'adaptive-grok-build-pro-v{version}.zip'
        sidecar_path = zip_path.with_suffix('.zip.sha256')
        if (ROOT / '.git').exists():
            self.assertTrue(zip_path.is_file())
            self.assertTrue(sidecar_path.is_file())
            digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
            self.assertEqual(sidecar_path.read_text(encoding='utf-8'), f'{digest}  {zip_path.name}\n')
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                prefix = 'adaptive-grok-build-pro/'
                source_members = {
                    f'{prefix}{path.relative_to(ROOT).as_posix()}': path
                    for path in source_files
                }
                manifest_member = f'{prefix}MANIFEST.sha256'
                self.assertEqual(names, sorted([*source_members, manifest_member]))
                self.assertEqual(
                    archive.read(manifest_member),
                    MANIFEST.render_manifest(ROOT, files=source_files),
                )
                for member, source in source_members.items():
                    self.assertTrue(
                        archive.read(member) == source.read_bytes(),
                        f'archive member differs from current source: {source.relative_to(ROOT)}',
                    )
                self.assertEqual(archive.read(f'{prefix}VERSION').decode('utf-8').strip(), '2.0.13')
                self.assertFalse(any('.github/workflows/' in name for name in names))
                self.assertFalse(any(name.endswith('dependabot.yml') for name in names))
                self.assertFalse(any(name.endswith('github-actions.yml') for name in names))

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
