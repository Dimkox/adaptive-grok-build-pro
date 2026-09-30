from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.router import build_route
from adaptive_grok.state import set_active_route
from adaptive_grok.verification import CheckResult, summarize_verification_report, verify
from tests._support import project_copy


def _sample(checks: list[dict[str, str]]) -> dict[str, object]:
    return {
        'schema_version': 1,
        'sample_id': 'consumer-coverage',
        'status': 'sample_evidence',
        'checks': checks,
    }


class ConsumerCoverageVerdictTests(unittest.TestCase):
    def test_factory_runtime_and_tests_have_real_lint_coverage_without_scanning_fixtures_as_secrets(self):
        from adaptive_grok import verification

        files = ['factory/runtime/setup_manager.py', 'factory/tests/test_runtime_installer.py']
        syntax = verification._factory_test_syntax(ROOT, files)
        self.assertEqual(syntax.status, 'pass')
        self.assertEqual(verification._unscanned_consumer_files(ROOT, files, [syntax]), [])
        self.assertIn(files[1], verification._unscanned_consumer_files(ROOT, files, []))
        with patch.object(verification, 'command_exists', return_value=True), patch.object(
            verification, '_command_check', return_value=CheckResult('lint', 'pass', 'exit=0')
        ) as execute:
            verification._ruff(ROOT)
            self.assertIn('factory/runtime', execute.call_args.args[2])
            self.assertNotIn('factory/tests', execute.call_args.args[2])
            verification._bandit(ROOT)
            self.assertIn('factory/runtime', execute.call_args.args[2])
            self.assertNotIn('factory/tests', execute.call_args.args[2])

    def test_factory_syntax_failure_or_nonpython_resource_never_claims_scanned_source(self):
        import tempfile
        from adaptive_grok import verification

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'factory' / 'tests'
            tests.mkdir(parents=True)
            (tests / 'invalid.py').write_text('def broken(:\n', encoding='utf-8')
            files = ['factory/tests/invalid.py', 'factory/tests/fixture.json']
            check = verification._factory_test_syntax(root, files)
            self.assertEqual(check.status, 'fail')
            self.assertEqual(verification._unscanned_consumer_files(root, files, [check]), [files[0]])

    def test_skip_only_report_or_unscanned_consumer_file_does_not_summarize_as_pass(self) -> None:
        skip_only = _sample([
            {'name': 'ruff', 'status': 'skip', 'summary': 'no python quality paths'},
            {'name': 'bandit', 'status': 'skip', 'summary': 'no non-test python paths'},
            {'name': 'architecture', 'status': 'skip', 'summary': 'architecture is not configured'},
        ])
        skip_summary = summarize_verification_report(skip_only)
        self.assertNotEqual(skip_summary['status'], 'pass')

        stack_only = _sample([
            {'name': 'ruff', 'status': 'pass', 'summary': 'exit=0'},
            {'name': 'bandit', 'status': 'pass', 'summary': 'exit=0'},
            {'name': 'architecture', 'status': 'skip', 'summary': 'architecture is not configured'},
        ])
        self.assertEqual(summarize_verification_report(stack_only)['status'], 'pass')
        unscanned_summary = summarize_verification_report(
            stack_only,
            uncovered_consumer_files=['engineering/product.py'],
        )
        self.assertNotEqual(unscanned_summary['status'], 'pass')

        with project_copy(git=True) as root:
            (root / 'engineering' / 'product.py').write_text('value = 1\n', encoding='utf-8')
            swift_dir = root / 'Sources'
            swift_dir.mkdir()
            (swift_dir / 'Game.swift').write_text('struct Game {}\n', encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)

            def fake_exists(name: str) -> bool:
                if name in {'ruff', 'bandit'}:
                    return True
                if name in {'pytest', 'coverage', 'semgrep', 'trivy', 'php', 'composer', 'npm'}:
                    return False
                return shutil.which(name) is not None

            def fake_check(root_path, name, command, timeout=300, env=None):
                return CheckResult(name, 'pass', 'exit=0', command=list(command))

            with patch('adaptive_grok.verification.command_exists', side_effect=fake_exists), patch(
                'adaptive_grok.verification._command_check',
                side_effect=fake_check,
            ):
                report = verify(root, mode='fast', record=False)

        self.assertNotEqual(report['status'], 'pass')
        coverage = next(item for item in report['checks'] if item['name'] == 'product-coverage')
        self.assertEqual(coverage['status'], 'fail')
        paths = {item['path'] for item in coverage['details']}
        self.assertIn('engineering/product.py', paths)
        self.assertIn('Sources/Game.swift', paths)
        self.assertTrue(all(item['code'] == 'incomplete_product_coverage' for item in coverage['details']))
        checks = {item['name']: item['status'] for item in report['checks']}
        self.assertEqual(checks['ruff'], 'pass')
        self.assertEqual(checks['architecture'], 'skip')


if __name__ == '__main__':
    unittest.main()
