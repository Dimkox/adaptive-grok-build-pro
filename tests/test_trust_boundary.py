from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.router import build_route
from adaptive_grok.state import (
    approval_requests_path,
    request_approval,
    set_active_route,
)
from adaptive_grok.util import git_head, tree_fingerprint
from adaptive_grok.verification import verify
from tests._support import project_copy


_PASSING_UNITTEST = (
    'import unittest\n'
    '\n'
    'class OkTests(unittest.TestCase):\n'
    '    def test_ok(self) -> None:\n'
    '        self.assertTrue(True)\n'
)


def _check(report: dict, name: str) -> dict:
    for item in report.get('checks', []):
        if item.get('name') == name:
            return item
    raise AssertionError(f'missing check: {name}')


def _without_required_tools(name: str) -> bool:
    if name in {'ruff', 'bandit', 'coverage'}:
        return False
    return shutil.which(name) is not None


class ApprovalRequestTests(unittest.TestCase):
    def test_request_is_bound_to_route_head_and_tree_without_granting(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Подготовить релиз', 'trust-boundary').to_dict()
            set_active_route(root, route)

            request = request_approval(root, 'production', 'release candidate')

            self.assertEqual(request['status'], 'requested')
            self.assertEqual(request['scope'], 'production')
            self.assertEqual(request['reason'], 'release candidate')
            self.assertEqual(request['route_id'], route['route_id'])
            self.assertEqual(request['git_head'], git_head(root))
            self.assertEqual(request['tree_fingerprint'], tree_fingerprint(root))
            self.assertTrue(request['id'])
            self.assertTrue(request['created_at'])
            self.assertFalse((root / '.grok-stack/runtime/approvals.json').exists())

            stored = json.loads(
                approval_requests_path(root).read_text(encoding='utf-8'),
            )
            self.assertEqual(stored, [request])

    def test_compatibility_cli_records_request_not_authorization(self) -> None:
        with project_copy(git=True) as root:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / 'scripts/grok_approve.py'),
                    'production',
                    '--reason',
                    'release candidate',
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload['status'], 'requested')
            self.assertEqual(payload['authorization'], 'not-granted')
            self.assertIn('protected pull-request', payload['next_step'])
            self.assertFalse((root / '.grok-stack/runtime/approvals.json').exists())


class StrictVerificationTests(unittest.TestCase):
    def test_strict_mode_fails_when_required_tools_are_missing(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')

            with patch(
                'adaptive_grok.verification.command_exists',
                side_effect=_without_required_tools,
            ):
                report = verify(
                    root,
                    mode='pr',
                    profiles=['base'],
                    record=False,
                    strict=True,
                )

            self.assertTrue(report['strict'])
            self.assertEqual(report['status'], 'fail')
            self.assertEqual(_check(report, 'ruff')['status'], 'fail')
            self.assertEqual(_check(report, 'bandit')['status'], 'fail')
            self.assertEqual(_check(report, 'coverage')['status'], 'fail')

    def test_non_strict_mode_preserves_missing_tool_skips(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')

            with patch(
                'adaptive_grok.verification.command_exists',
                side_effect=_without_required_tools,
            ):
                report = verify(
                    root,
                    mode='pr',
                    profiles=['base'],
                    record=False,
                    strict=False,
                )

            self.assertFalse(report['strict'])
            self.assertEqual(report['status'], 'pass')
            self.assertEqual(_check(report, 'ruff')['status'], 'skip')
            self.assertEqual(_check(report, 'bandit')['status'], 'skip')
            self.assertEqual(_check(report, 'coverage')['status'], 'skip')


if __name__ == '__main__':
    unittest.main()
