from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.doctor import run_doctor
from adaptive_grok.router import build_route
from adaptive_grok.state import set_active_route
from adaptive_grok.verification import CheckResult, _contracts, _python, _secret_scan, _sql_safety, verify
from tests._support import project_copy

_PASSING_UNITTEST = (
    'import unittest\n'
    '\n'
    'class OkTests(unittest.TestCase):\n'
    '    def test_ok(self) -> None:\n'
    '        self.assertTrue(True)\n'
)

_FAILING_UNITTEST = (
    'import unittest\n'
    '\n'
    'class FailTests(unittest.TestCase):\n'
    '    def test_fail(self) -> None:\n'
    '        self.fail("expected failure")\n'
)


def _check(report: dict, name: str) -> dict | None:
    for item in report.get('checks', []):
        if item.get('name') == name:
            return item
    return None


class VerificationTests(unittest.TestCase):
    def test_invalid_json_contract_fails(self) -> None:
        with project_copy() as root:
            path = root / 'engineering/contracts/schemas/bad.schema.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{')
            result = _contracts(root, ['engineering/contracts/schemas/bad.schema.json'])
            self.assertEqual(result.status, 'fail')

    def test_invalid_openapi_structure_fails(self) -> None:
        with project_copy() as root:
            path = root / 'engineering/contracts/openapi/test.yaml'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('openapi: 3.1.0\ninfo: {}\n')
            result = _contracts(root, ['engineering/contracts/openapi/test.yaml'])
            self.assertEqual(result.status, 'fail')
            self.assertTrue(any(item['code'] == 'openapi-paths' for item in result.details))

    def test_unsafe_sql_fails(self) -> None:
        with project_copy() as root:
            path = root / 'migrations/001.sql'
            path.parent.mkdir()
            path.write_text('TRUNCATE TABLE users;')
            result = _sql_safety(root, ['migrations/001.sql'])
            self.assertEqual(result.status, 'fail')

    def test_secret_scan_detects_key(self) -> None:
        with project_copy() as root:
            path = root / 'config.php'
            fake_secret = "abcde" * 5
            path.write_text("<?php $" + "api_key = '" + fake_secret + "';")
            result = _secret_scan(root, ['config.php'])
            self.assertEqual(result.status, 'fail')

    def test_verify_records_receipt_for_active_route(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            report = verify(root, mode='fast', record=True)
            self.assertEqual(report['status'], 'pass')
            receipt = root / f".grok-stack/runtime/receipts/{route['route_id']}/verification.json"
            self.assertTrue(receipt.is_file())

    def test_python_runs_unittest_without_project_marker(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            report = verify(root, mode='fast', record=True)
            check = _check(report, 'python-unittest')
            self.assertIsNotNone(check)
            self.assertEqual(check['status'], 'pass')

    def test_python_unittest_failure_is_a_failed_check(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_fail.py').write_text(_FAILING_UNITTEST, encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            report = verify(root, mode='fast', record=True)
            self.assertEqual(report['status'], 'fail')
            check = _check(report, 'python-unittest')
            self.assertIsNotNone(check)
            self.assertEqual(check['status'], 'fail')

    def test_python_skips_without_tests_or_project_marker(self) -> None:
        with project_copy() as root:
            self.assertFalse((root / 'tests').exists())
            self.assertEqual(_python(root), [])

    def test_python_ignores_non_python_tests_directory(self) -> None:
        with project_copy() as root:
            path = root / 'tests' / 'Unit' / 'GreetingServiceTest.php'
            path.parent.mkdir(parents=True)
            path.write_text('<?php class GreetingServiceTest {}\n', encoding='utf-8')
            self.assertEqual(_python(root), [])

    def test_python_ignores_nested_unittest_without_top_level(self) -> None:
        with project_copy() as root:
            nested = root / 'tests' / 'nested'
            nested.mkdir(parents=True)
            (nested / 'test_x.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            self.assertEqual(_python(root), [])

    def test_python_pytest_wins_when_project_marker_present(self) -> None:
        with project_copy() as root:
            (root / 'pyproject.toml').write_text('[project]\nname = "demo"\n', encoding='utf-8')
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')

            def fake_exists(name: str) -> bool:
                return name == 'pytest'

            with patch('adaptive_grok.verification.command_exists', side_effect=fake_exists), patch(
                'adaptive_grok.verification._command_check',
                return_value=CheckResult('pytest', 'pass', 'ok'),
            ):
                results = _python(root)
            names = [item.name for item in results]
            self.assertIn('pytest', names)
            self.assertNotIn('python-unittest', names)


class DoctorTests(unittest.TestCase):
    def test_project_doctor_has_no_failures(self) -> None:
        items = run_doctor(ROOT)
        failures = [item for item in items if item.status == 'fail']
        self.assertEqual(failures, [], [(item.name, item.message) for item in failures])

    def test_unmanaged_agent_does_not_break_harness_doctor(self) -> None:
        with project_copy() as root:
            custom = root / '.grok/agents/custom-user-agent.toml'
            custom.write_text('this is not adaptive grok managed config', encoding='utf-8')
            items = run_doctor(root)
            failures = [item for item in items if item.status == 'fail']
            self.assertEqual(failures, [], [(item.name, item.message) for item in failures])
            self.assertTrue(any(item.name == 'unmanaged-agents' for item in items))


if __name__ == '__main__':
    unittest.main()
