from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.receipts import invalidate_receipts, validate_evidence, write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.state import get_active_change, get_active_route, set_active_route
from adaptive_grok.verification import verify
from tests._support import project_copy

_PASSING_UNITTEST = (
    'import unittest\n'
    '\n'
    'class OkTests(unittest.TestCase):\n'
    '    def test_ok(self) -> None:\n'
    '        self.assertTrue(True)\n'
)


class ChangeTests(unittest.TestCase):
    def test_start_requires_route(self) -> None:
        with project_copy() as root:
            with self.assertRaises(RuntimeError):
                start_change(root, 'Test')

    def test_start_creates_durable_package(self) -> None:
        with project_copy() as root:
            route = build_route(root, 'Добавить Битрикс модуль синхронизации', 's1').to_dict()
            set_active_route(root, route)
            state = start_change(root)
            active = get_active_change(root)
            self.assertEqual(state['status'], 'draft')
            self.assertIsNotNone(active)
            change = root / str(active['path'])
            self.assertTrue((change / 'requirements.md').is_file())
            self.assertIn('bitrix', (change / 'route.json').read_text(encoding='utf-8'))
            self.assertEqual(get_active_route(root)['change_id'], state['change_id'])

    def test_valid_transitions(self) -> None:
        with project_copy() as root:
            set_active_route(root, build_route(root, 'Добавить функцию', 's1').to_dict())
            state = start_change(root)
            change_id = state['change_id']
            self.assertEqual(transition(root, change_id, 'scoped', 'scope ready')['status'], 'scoped')
            self.assertEqual(transition(root, change_id, 'approved', 'approved')['status'], 'approved')

    def test_invalid_transition_is_rejected(self) -> None:
        with project_copy() as root:
            set_active_route(root, build_route(root, 'Добавить функцию', 's1').to_dict())
            state = start_change(root)
            with self.assertRaises(ValueError):
                transition(root, state['change_id'], 'ready', 'skip')


class ReceiptTests(unittest.TestCase):
    def test_receipts_validate_against_current_tree(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            route['required_evidence'] = ['verification', 'code_review']
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')
            write_receipt(root, 'code_review', 'pass')
            self.assertEqual(validate_evidence(root, route), [])

    def test_receipt_becomes_stale_after_change(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Исправить PHP баг', 's1').to_dict()
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')
            (root / 'new.php').write_text('<?php echo 1;')
            gaps = validate_evidence(root, route)
            self.assertTrue(any('stale' in item for item in gaps))

    def test_failed_receipt_is_not_valid(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review this PR', 's1').to_dict()
            route['required_evidence'] = ['code_review']
            set_active_route(root, route)
            write_receipt(root, 'code_review', 'fail')
            self.assertTrue(any('status=fail' in item for item in validate_evidence(root, route)))

    def test_explicit_invalidation_marks_receipts(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review this PR', 's1').to_dict()
            route['required_evidence'] = ['code_review']
            set_active_route(root, route)
            path = write_receipt(root, 'code_review', 'pass')
            invalidate_receipts(root, route['route_id'], 'changed')
            self.assertIn('"stale": true', path.read_text(encoding='utf-8'))


class ContourTests(unittest.TestCase):
    def test_contour_route_change_verify_review_has_no_evidence_gaps(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            route['required_evidence'] = ['verification', 'code_review', 'test_review']
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root)
            self.assertIsNotNone(active)
            change = root / str(active['path'])
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            evidence = change / 'evidence'
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / 'code-review.md').write_text('# dummy code review\n', encoding='utf-8')
            (evidence / 'test-review.md').write_text('# dummy test review\n', encoding='utf-8')
            report = verify(root, mode='fast', record=True)
            checks = {item['name']: item for item in report['checks']}
            self.assertIn('python-unittest', checks)
            self.assertEqual(checks['python-unittest']['status'], 'pass')
            write_receipt(root, 'code_review', 'pass')
            write_receipt(root, 'test_review', 'pass')
            self.assertEqual(validate_evidence(root, get_active_route(root) or route), [])


if __name__ == '__main__':
    unittest.main()
