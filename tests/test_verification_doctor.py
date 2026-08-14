from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.doctor import run_doctor
from adaptive_grok.router import build_route
from adaptive_grok.state import set_active_route
from adaptive_grok.verification import _contracts, _secret_scan, _sql_safety, verify
from tests._support import project_copy


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
            path.write_text(f"<?php $api_key = '{fake_secret}';")
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


class DoctorTests(unittest.TestCase):
    def test_project_doctor_has_no_failures(self) -> None:
        items = run_doctor(ROOT)
        failures = [item for item in items if item.status == 'fail']
        self.assertEqual(failures, [], [(item.name, item.message) for item in failures])

    def test_unmanaged_agent_does_not_break_harness_doctor(self) -> None:
        with project_copy() as root:
            custom = root / '.grok/agents/custom-user-agent.toml'
            custom.write_text('this is not adaptive codex managed config', encoding='utf-8')
            items = run_doctor(root)
            failures = [item for item in items if item.status == 'fail']
            self.assertEqual(failures, [], [(item.name, item.message) for item in failures])
            self.assertTrue(any(item.name == 'unmanaged-agents' for item in items))


if __name__ == '__main__':
    unittest.main()
