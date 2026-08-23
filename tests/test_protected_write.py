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

from adaptive_grok.protected_write import ProtectedWriteError, apply_manifest
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


if __name__ == '__main__':
    unittest.main()
