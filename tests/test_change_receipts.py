from __future__ import annotations

import sys
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.receipts import invalidate_receipts, validate_evidence, write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.state import get_active_change, get_active_route, set_active_route
from adaptive_grok.verification import verify
from adaptive_grok.spec import dump_canonical_spec
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
    def _install_spec(self, root: Path, active: dict, evidence_by_id: dict[str, dict], *, contracts=None) -> Path:
        path = root / str(active['path']) / 'change-spec.yaml'
        spec = {
            'schema_version': 2,
            'change_id': active['change_id'],
            'objective': {'id': 'OBJ-001', 'statement': 'bind evidence', 'success_metric': 'bound_receipts', 'target': 'all'},
            'risk': {'tier': 'green', 'domains': []},
            'acceptance_criteria': [
                {'id': criterion_id, 'statement': f'bind {criterion_id}', 'evidence': [evidence]}
                for criterion_id, evidence in evidence_by_id.items()
            ],
            'invariants': [], 'forbidden_outcomes': [],
            'contracts': contracts or {'openapi': [], 'json_schema': [], 'events': []},
            'observability': [],
            'rollback': {'strategy': 'forward_fix', 'maximum_steps': 1},
            'approvals': {'required_scopes': []},
        }
        path.write_text(dump_canonical_spec(spec), encoding='utf-8')
        return path

    def test_receipt_binds_active_spec_and_declared_criteria(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            path = root / str(active['path']) / 'change-spec.yaml'
            spec = {
                'schema_version': 2,
                'change_id': active['change_id'],
                'objective': {'id': 'OBJ-001', 'statement': 'bind evidence', 'success_metric': 'bound_receipts', 'target': 'all'},
                'risk': {'tier': 'green', 'domains': []},
                'acceptance_criteria': [{'id': 'AC-002', 'statement': 'bound', 'evidence': [{'receipt': 'verification'}]}, {'id': 'AC-001', 'statement': 'also bound', 'evidence': [{'receipt': 'verification'}]}],
                'invariants': [], 'forbidden_outcomes': [],
                'contracts': {'openapi': [], 'json_schema': [], 'events': []},
                'observability': [],
                'rollback': {'strategy': 'forward_fix', 'maximum_steps': 1},
                'approvals': {'required_scopes': []},
            }
            path.write_text(dump_canonical_spec(spec), encoding='utf-8')
            receipt_path = write_receipt(root, 'verification', 'pass')
            receipt = __import__('json').loads(receipt_path.read_text(encoding='utf-8'))
            self.assertEqual(receipt['criterion_ids'], ['AC-001', 'AC-002'])
            self.assertEqual(len(receipt['spec_digest']), 64)
            self.assertEqual(validate_evidence(root, get_active_route(root) or route), [])
            spec['objective']['target'] = 'changed'
            path.write_text(dump_canonical_spec(spec), encoding='utf-8')
            self.assertTrue(any('spec' in item and 'stale' in item for item in validate_evidence(root, get_active_route(root) or route)))

    def test_every_receipt_kind_selects_only_its_declared_criteria(self) -> None:
        kinds = ['verification', 'code_review', 'test_review', 'security_review', 'release_review']
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            route['required_evidence'] = kinds
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            self._install_spec(root, active, {
                f'AC-{index:03d}': {'receipt': kind}
                for index, kind in enumerate(kinds, 1)
            })
            for index, kind in enumerate(kinds, 1):
                receipt = json.loads(write_receipt(root, kind, 'pass').read_text(encoding='utf-8'))
                self.assertEqual(receipt['criterion_ids'], [f'AC-{index:03d}'])
            self.assertEqual(validate_evidence(root, get_active_route(root) or route), [])

    def test_explicit_binding_mismatch_is_rejected(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            self._install_spec(root, active, {'AC-001': {'receipt': 'verification'}})
            with self.assertRaises(ValueError):
                write_receipt(root, 'verification', 'pass', criterion_ids=['AC-999'])
            with self.assertRaises(ValueError):
                write_receipt(root, 'verification', 'pass', spec_digest='0' * 64)

    def test_legacy_receipt_without_spec_bindings_is_insufficient(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            self._install_spec(root, active, {'AC-001': {'receipt': 'verification'}})
            path = write_receipt(root, 'verification', 'pass')
            receipt = json.loads(path.read_text(encoding='utf-8'))
            for field in ('criterion_ids', 'spec_digest', 'spec_fingerprint'):
                receipt.pop(field)
            path.write_text(json.dumps(receipt), encoding='utf-8')
            gaps = validate_evidence(root, get_active_route(root) or route)
            self.assertTrue(any('spec binding stale' in gap for gap in gaps))
            self.assertTrue(any('criterion binding stale' in gap for gap in gaps))

    def test_receipt_stales_on_contract_route_base_and_git_head_changes(self) -> None:
        for mutation in ('contract', 'route', 'head'):
            with self.subTest(mutation=mutation), project_copy(git=True) as root:
                route = build_route(root, 'Добавить функцию', 's1').to_dict()
                route['required_evidence'] = ['verification']
                set_active_route(root, route)
                start_change(root)
                active = get_active_change(root) or {}
                contract = root / 'contracts/schema.json'
                contract.parent.mkdir(parents=True)
                contract.write_text('{}\n', encoding='utf-8')
                self._install_spec(
                    root,
                    active,
                    {'AC-001': {'receipt': 'verification'}},
                    contracts={'openapi': [], 'json_schema': ['contracts/schema.json'], 'events': []},
                )
                subprocess.run(['git', 'add', '.'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'typed spec baseline'], cwd=root, check=True)
                write_receipt(root, 'verification', 'pass')
                if mutation == 'contract':
                    contract.write_text('{"changed":true}\n', encoding='utf-8')
                elif mutation == 'route':
                    route['base_commit'] = 'f' * 40
                    set_active_route(root, route)
                else:
                    (root / 'head-change.txt').write_text('changed\n', encoding='utf-8')
                    subprocess.run(['git', 'add', 'head-change.txt'], cwd=root, check=True)
                    subprocess.run(['git', 'commit', '-qm', 'head change'], cwd=root, check=True)
                gaps = validate_evidence(root, get_active_route(root) or route)
                self.assertTrue(any('stale' in gap for gap in gaps), gaps)
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
