from __future__ import annotations

import base64
import contextlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.protected_write import ProtectedWriteError, apply_manifest, load_manifest
from adaptive_grok.router import build_route
from adaptive_grok.state import add_approval, set_active_route
from adaptive_grok.util import file_sha256
from tests._support import project_copy


@contextlib.contextmanager
def github_project() -> Iterator[Path]:
    with project_copy(git=True) as root:
        subprocess.run(
            ['git', 'remote', 'add', 'origin', 'git@github.com:Dimkox/adaptive-grok-build-pro.git'],
            cwd=root,
            check=True,
        )
        set_active_route(root, build_route(root, 'Обновить control plane', 's1').to_dict())
        yield root


def write_manifest(root: Path, operations: list[dict[str, str]], name: str = 'protected-write.json') -> Path:
    path = root.parent / name
    path.write_text(
        json.dumps({'schema_version': 1, 'operations': operations}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return path


def operation(path: str, expected_sha256: str, content: bytes) -> dict[str, str]:
    return {
        'path': path,
        'expected_sha256': expected_sha256,
        'content_base64': base64.b64encode(content).decode('ascii'),
    }


class ProtectedWriteTests(unittest.TestCase):
    def test_one_tree_bound_grant_applies_atomic_multi_file_batch(self) -> None:
        with github_project() as root:
            first = root / 'AGENTS.md'
            second = root / '.grok/config.toml'
            first_content = first.read_bytes() + b'\n# batch-one\n'
            second_content = second.read_bytes() + b'\n# batch-two\n'
            add_approval(
                root,
                'protected-path',
                'approved reasoning-policy batch',
                5,
                actions=['protected-path-write'],
                resources=['AGENTS.md', '.grok/config.toml'],
            )
            manifest = write_manifest(
                root,
                [
                    operation('AGENTS.md', file_sha256(first), first_content),
                    operation('.grok/config.toml', file_sha256(second), second_content),
                ],
            )
            result = apply_manifest(root, manifest)
            self.assertTrue(result['ok'])
            self.assertFalse(result['dry_run'])
            self.assertEqual(first.read_bytes(), first_content)
            self.assertEqual(second.read_bytes(), second_content)

    def test_missing_grant_rejects_entire_batch_before_first_write(self) -> None:
        with github_project() as root:
            first = root / 'AGENTS.md'
            second = root / '.grok/config.toml'
            original_first = first.read_bytes()
            original_second = second.read_bytes()
            add_approval(
                root,
                'protected-path',
                'only one file approved',
                5,
                actions=['protected-path-write'],
                resources=['AGENTS.md'],
            )
            manifest = write_manifest(
                root,
                [
                    operation('AGENTS.md', file_sha256(first), original_first + b'\nchanged\n'),
                    operation('.grok/config.toml', file_sha256(second), original_second + b'\nchanged\n'),
                ],
            )
            with self.assertRaisesRegex(ProtectedWriteError, 'no exact protected-path grant'):
                apply_manifest(root, manifest)
            self.assertEqual(first.read_bytes(), original_first)
            self.assertEqual(second.read_bytes(), original_second)

    def test_stale_expected_sha_rejects_without_mutation(self) -> None:
        with github_project() as root:
            target = root / 'AGENTS.md'
            original = target.read_bytes()
            add_approval(
                root,
                'protected-path',
                'approved edit',
                5,
                actions=['protected-path-write'],
                resources=['AGENTS.md'],
            )
            manifest = write_manifest(
                root,
                [operation('AGENTS.md', '0' * 64, original + b'\nchanged\n')],
            )
            with self.assertRaisesRegex(ProtectedWriteError, 'optimistic-lock mismatch'):
                apply_manifest(root, manifest)
            self.assertEqual(target.read_bytes(), original)

    def test_manifest_must_live_outside_repository(self) -> None:
        with github_project() as root:
            target = root / 'AGENTS.md'
            add_approval(
                root,
                'protected-path',
                'approved edit',
                5,
                actions=['protected-path-write'],
                resources=['AGENTS.md'],
            )
            manifest = root / 'manifest.json'
            manifest.write_text(
                json.dumps(
                    {
                        'schema_version': 1,
                        'operations': [operation('AGENTS.md', file_sha256(target), target.read_bytes())],
                    }
                ),
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ProtectedWriteError, 'outside the repository'):
                apply_manifest(root, manifest)

    def test_non_control_plane_target_is_rejected_even_with_local_grant(self) -> None:
        with github_project() as root:
            target = 'engineering/reviews/new.md'
            add_approval(
                root,
                'protected-path',
                'attempted out-of-scope edit',
                5,
                actions=['protected-path-write'],
                resources=[target],
            )
            manifest = write_manifest(root, [operation(target, 'MISSING', b'nope\n')])
            with self.assertRaisesRegex(ProtectedWriteError, 'not part of the repository control plane'):
                apply_manifest(root, manifest)
            self.assertFalse((root / target).exists())

    def test_dry_run_validates_complete_batch_without_writing(self) -> None:
        with github_project() as root:
            target = root / 'AGENTS.md'
            original = target.read_bytes()
            add_approval(
                root,
                'protected-path',
                'approved dry run',
                5,
                actions=['protected-path-write'],
                resources=['AGENTS.md'],
            )
            manifest = write_manifest(
                root,
                [operation('AGENTS.md', file_sha256(target), original + b'\nchanged\n')],
            )
            result = apply_manifest(root, manifest, dry_run=True)
            self.assertTrue(result['dry_run'])
            self.assertEqual(target.read_bytes(), original)

    def test_load_manifest_rejects_missing_invalid_and_duplicate_operations(self) -> None:
        with github_project() as root:
            missing = root.parent / 'does-not-exist.json'
            with self.assertRaisesRegex(ProtectedWriteError, 'does not exist'):
                load_manifest(missing)
            broken = root.parent / 'broken.json'
            broken.write_text('{', encoding='utf-8')
            with self.assertRaisesRegex(ProtectedWriteError, 'cannot read'):
                load_manifest(broken)
            wrong_schema = root.parent / 'schema.json'
            wrong_schema.write_text(json.dumps({'schema_version': 2, 'operations': [{}]}), encoding='utf-8')
            with self.assertRaisesRegex(ProtectedWriteError, 'schema_version'):
                load_manifest(wrong_schema)
            empty = root.parent / 'empty.json'
            empty.write_text(json.dumps({'schema_version': 1, 'operations': []}), encoding='utf-8')
            with self.assertRaisesRegex(ProtectedWriteError, 'non-empty'):
                load_manifest(empty)
            not_object = root.parent / 'not-object.json'
            not_object.write_text(json.dumps({'schema_version': 1, 'operations': ['nope']}), encoding='utf-8')
            with self.assertRaisesRegex(ProtectedWriteError, 'must be an object'):
                load_manifest(not_object)
            no_path = root.parent / 'no-path.json'
            no_path.write_text(json.dumps({'schema_version': 1, 'operations': [{'expected_sha256': 'MISSING'}]}), encoding='utf-8')
            with self.assertRaisesRegex(ProtectedWriteError, 'non-empty path'):
                load_manifest(no_path)
            bad_hash = root.parent / 'bad-hash.json'
            bad_hash.write_text(
                json.dumps(
                    {
                        'schema_version': 1,
                        'operations': [{'path': 'AGENTS.md', 'expected_sha256': 'not-a-hash', 'content': 'x\n'}],
                    }
                ),
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ProtectedWriteError, 'expected_sha256'):
                load_manifest(bad_hash)
            duplicate = root.parent / 'duplicate.json'
            duplicate.write_text(
                json.dumps(
                    {
                        'schema_version': 1,
                        'operations': [
                            {'path': 'AGENTS.md', 'expected_sha256': 'MISSING', 'content': 'a\n'},
                            {'path': 'AGENTS.md', 'expected_sha256': 'MISSING', 'content': 'b\n'},
                        ],
                    }
                ),
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ProtectedWriteError, 'duplicate operation path'):
                load_manifest(duplicate)


if __name__ == '__main__':
    unittest.main()
