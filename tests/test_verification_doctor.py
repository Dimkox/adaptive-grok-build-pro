from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.doctor import run_doctor
from adaptive_grok.change import start_change
from adaptive_grok.router import build_route
from adaptive_grok.spec import dump_canonical_spec
from adaptive_grok.state import get_active_change, set_active_route
from adaptive_grok.verification import CheckResult, _change_specs, _contracts, _node, _python, _secret_scan, _sql_safety, verify
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

_ADOPTION_MARKER = '''{
  "architecture_id": "ARCH-ADAPTIVE-GROK-M2",
  "schema_version": 1,
  "state": "adopted"
}
'''


def _check(report: dict, name: str) -> dict | None:
    for item in report.get('checks', []):
        if item.get('name') == name:
            return item
    return None


def _names(items) -> list[str]:
    return [item.name if hasattr(item, 'name') else item.get('name') for item in items]


def _valid_change_spec(change_id: str) -> dict:
    return {
        'schema_version': 2, 'change_id': change_id,
        'objective': {'id': 'OBJ-001', 'statement': 'verify selection', 'success_metric': 'selected', 'target': 'all'},
        'risk': {'tier': 'green', 'domains': []},
        'acceptance_criteria': [{'id': 'AC-001', 'statement': 'selected', 'evidence': [{'receipt': 'verification'}]}],
        'invariants': [], 'forbidden_outcomes': [],
        'contracts': {'openapi': [], 'json_schema': [], 'events': []},
        'observability': [], 'rollback': {'strategy': 'forward_fix', 'maximum_steps': 1},
        'approvals': {'required_scopes': []},
    }


def _which_except(*blocked: str):
    def exists(name: str) -> bool:
        if name in blocked:
            return False
        return shutil.which(name) is not None

    return exists


def _which_only(*allowed: str):
    def exists(name: str) -> bool:
        if name in allowed:
            return True
        if name in {'ruff', 'bandit', 'coverage', 'semgrep', 'trivy', 'pytest', 'npm'}:
            return False
        return shutil.which(name) is not None

    return exists


_FAKE_RUFF = '''#!/usr/bin/env python3
import sys
from pathlib import Path

needle = "import unused_module"
fail = False
args = [a for a in sys.argv[1:] if a != "check" and not a.startswith("-")]
for raw in args:
    path = Path(raw)
    files = [path] if path.is_file() else list(path.rglob("*.py")) if path.exists() else []
    for item in files:
        try:
            text = item.read_text(encoding="utf-8")
        except OSError:
            continue
        if needle in text:
            print(f"{item}: F401 unused import")
            fail = True
sys.exit(1 if fail else 0)
'''

_FAKE_BANDIT = '''#!/usr/bin/env python3
import sys
from pathlib import Path

args = sys.argv[1:]
paths = []
i = 0
while i < len(args):
    if args[i] in {"-c", "--config"}:
        i += 2
        continue
    if args[i] in {"-q", "-r", "--quiet", "--recursive"}:
        i += 1
        continue
    if args[i].startswith("-"):
        i += 1
        continue
    paths.append(args[i])
    i += 1
fail = False
for raw in paths:
    path = Path(raw)
    files = [path] if path.is_file() else list(path.rglob("*.py")) if path.exists() else []
    for item in files:
        try:
            text = item.read_text(encoding="utf-8")
        except OSError:
            continue
        if "eval(" in text:
            print(f"{item}: B307 use of eval")
            fail = True
sys.exit(1 if fail else 0)
'''

_FAKE_COVERAGE_FAIL_REPORT = '''#!/usr/bin/env python3
import os
import sys
if len(sys.argv) > 1 and sys.argv[1] == "run":
    rest = sys.argv[2:]
    if "--rcfile" in rest:
        idx = rest.index("--rcfile")
        del rest[idx:idx + 2]
    else:
        rest = [item for item in rest if not item.startswith("--rcfile=")]
    os.execv(sys.executable, [sys.executable, *rest])
if len(sys.argv) > 1 and sys.argv[1] == "report":
    print("TOTAL 0 0 0%")
    sys.exit(1)
sys.exit(0)
'''


def _install_tool(bindir: Path, name: str, body: str) -> None:
    path = bindir / name
    path.write_text(body, encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class _PathTools:
    def __init__(self, tools: dict[str, str]) -> None:
        self.tools = tools
        self._tmp = None
        self._old_path = None

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory(prefix='adaptive-grok-tools-')
        bindir = Path(self._tmp.name)
        for name, body in self.tools.items():
            _install_tool(bindir, name, body)
        self._old_path = os.environ.get('PATH', '')
        os.environ['PATH'] = f'{bindir}{os.pathsep}{self._old_path}'
        return bindir

    def __exit__(self, *exc) -> None:
        if self._old_path is not None:
            os.environ['PATH'] = self._old_path
        if self._tmp is not None:
            self._tmp.cleanup()


class VerificationTests(unittest.TestCase):
    @staticmethod
    def _adopt_architecture(root: Path) -> None:
        for rel in ('architecture', 'schemas', 'engineering/contracts'):
            source = ROOT / rel
            target = root / rel
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        (root / 'architecture/adoption.json').write_text(_ADOPTION_MARKER, encoding='utf-8')

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

    def test_verify_reports_architecture_metadata_without_exact_worktree_sha(self) -> None:
        with project_copy(git=True) as root:
            self._adopt_architecture(root)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt architecture'], cwd=root, check=True)
            route = build_route(root, 'Review current architecture', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            report = verify(root, mode='fast', record=False)
            metadata = report['architecture']
            self.assertEqual(metadata['head_kind'], 'worktree')
            self.assertNotIn('exact_head_sha', metadata)
            for key in ('schema_digest', 'system_digest', 'rules_digest', 'architecture_digest', 'architecture_evidence_digest'):
                self.assertRegex(metadata[key], r'^[0-9a-f]{64}$')
            self.assertEqual(len(metadata['generated_artifact_digests']), 5)

    def test_verify_unconfigured_is_compatible_but_adopted_deletion_fails(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            self.assertEqual(verify(root, mode='fast', record=False)['architecture']['status'], 'not_configured')
            self._adopt_architecture(root)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt architecture'], cwd=root, check=True)
            (root / 'architecture/system.yaml').unlink()
            report = verify(root, mode='fast', record=False)
            self.assertEqual(report['status'], 'fail')
            self.assertEqual(_check(report, 'architecture')['status'], 'fail')

    def test_verify_fails_after_committed_deletion_of_both_adopted_models(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current architecture', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            self._adopt_architecture(root)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt architecture'], cwd=root, check=True)
            (root / 'architecture/system.yaml').unlink()
            (root / 'architecture/rules.yaml').unlink()
            subprocess.run(['git', 'add', '-u'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'delete architecture'], cwd=root, check=True)

            report = verify(root, mode='fast', record=False)
            self.assertEqual(report['status'], 'fail')
            self.assertEqual(report['architecture']['status'], 'fail')
            architecture = _check(report, 'architecture')
            self.assertIsNotNone(architecture)
            self.assertEqual(architecture['status'], 'fail')
            self.assertIn('missing', architecture['summary'])

    def test_marker_backed_merge_deletion_fails_without_history_inference(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current architecture', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            legacy = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=root, text=True, encoding='utf-8'
            ).strip()
            main_branch = subprocess.check_output(
                ['git', 'branch', '--show-current'], cwd=root, text=True, encoding='utf-8'
            ).strip()
            self._adopt_architecture(root)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt architecture'], cwd=root, check=True)
            subprocess.run(['git', 'checkout', '-qb', 'legacy-side', legacy], cwd=root, check=True)
            (root / 'side.txt').write_text('side\n', encoding='utf-8')
            subprocess.run(['git', 'add', 'side.txt'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'legacy side'], cwd=root, check=True)
            subprocess.run(['git', 'checkout', '-q', main_branch], cwd=root, check=True)
            subprocess.run(['git', 'merge', '--no-commit', '--no-ff', 'legacy-side'], cwd=root, check=True)
            (root / 'architecture/system.yaml').unlink()
            (root / 'architecture/rules.yaml').unlink()
            subprocess.run(['git', 'add', '-u'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'merge with architecture deletion'], cwd=root, check=True)

            report = verify(root, mode='fast', record=False)
            self.assertEqual(report['status'], 'fail')
            self.assertIn('missing', _check(report, 'architecture')['summary'])

    def test_marker_backed_shallow_deletion_fails_at_depth_one(self) -> None:
        with project_copy(git=True) as source, tempfile.TemporaryDirectory() as tmp:
            self._adopt_architecture(source)
            subprocess.run(['git', 'add', '.'], cwd=source, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt architecture'], cwd=source, check=True)
            (source / 'architecture/system.yaml').unlink()
            (source / 'architecture/rules.yaml').unlink()
            subprocess.run(['git', 'add', '-u'], cwd=source, check=True)
            subprocess.run(['git', 'commit', '-qm', 'delete architecture'], cwd=source, check=True)
            clone = Path(tmp) / 'shallow'
            subprocess.run(
                ['git', 'clone', '-q', '--depth=1', f'file://{source}', str(clone)],
                check=True,
            )

            report = verify(clone, mode='fast', record=False)
            self.assertEqual(report['status'], 'fail')
            self.assertIn('missing', _check(report, 'architecture')['summary'])

    def test_malformed_adoption_marker_fails_closed(self) -> None:
        malformed = (
            '{}\n',
            '{"architecture_id":"ARCH-ADAPTIVE-GROK-M2","schema_version":1,"state":"adopted"}\n',
        )
        for marker in malformed:
            with self.subTest(marker=marker), project_copy(git=True) as root:
                path = root / 'architecture/adoption.json'
                path.parent.mkdir(parents=True)
                path.write_text(marker, encoding='utf-8')
                report = verify(root, mode='fast', record=False)
                self.assertEqual(report['status'], 'fail')
                self.assertEqual(_check(report, 'architecture')['status'], 'fail')

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
            names = _names(_python(root))
            self.assertNotIn('python-unittest', names)
            self.assertNotIn('pytest', names)

    def test_python_ignores_non_python_tests_directory(self) -> None:
        with project_copy() as root:
            path = root / 'tests' / 'Unit' / 'GreetingServiceTest.php'
            path.parent.mkdir(parents=True)
            path.write_text('<?php class GreetingServiceTest {}\n', encoding='utf-8')
            names = _names(_python(root))
            self.assertNotIn('python-unittest', names)
            self.assertNotIn('pytest', names)

    def test_python_ignores_nested_unittest_without_top_level(self) -> None:
        with project_copy() as root:
            nested = root / 'tests' / 'nested'
            nested.mkdir(parents=True)
            (nested / 'test_x.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            names = _names(_python(root))
            self.assertNotIn('python-unittest', names)
            self.assertNotIn('pytest', names)

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
            names = _names(results)
            self.assertIn('pytest', names)
            self.assertNotIn('python-unittest', names)


class TypedSpecVerificationTests(unittest.TestCase):
    def test_pr_selects_active_and_every_changed_spec(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            active_rel = f"{active['path']}/change-spec.yaml"
            (root / active_rel).write_text(dump_canonical_spec(_valid_change_spec(active['change_id'])), encoding='utf-8')
            other_rel = 'engineering/changes/20260826-other/change-spec.yaml'
            other = root / other_rel
            other.parent.mkdir(parents=True)
            other.write_text(dump_canonical_spec(_valid_change_spec('20260826-other')), encoding='utf-8')
            check, metadata = _change_specs(root, [other_rel], route, 'pr')
            self.assertEqual(check.status, 'pass')
            self.assertEqual([item['path'] for item in metadata['specs']], sorted([active_rel, other_rel]))

    def test_changed_v1_and_missing_selected_spec_fail(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            active_path = root / str(active['path']) / 'change-spec.yaml'
            active_path.write_text(dump_canonical_spec(_valid_change_spec(active['change_id'])), encoding='utf-8')
            legacy_rel = 'engineering/changes/20260826-legacy/change-spec.yaml'
            legacy = root / legacy_rel
            legacy.parent.mkdir(parents=True)
            legacy.write_text('schema_version: 1\nchange_id: 20260826-legacy\n', encoding='utf-8')
            check, _ = _change_specs(root, [legacy_rel], route, 'pr')
            self.assertEqual(check.status, 'fail')
            missing_rel = 'engineering/changes/20260826-missing/change-spec.yaml'
            check, _ = _change_specs(root, [missing_rel], route, 'pr')
            self.assertEqual(check.status, 'fail')
            self.assertTrue(any(item['code'] == 'spec-missing' for item in check.details))

    def test_fast_is_draft_but_pr_is_gate(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            rel = f"{active['path']}/change-spec.yaml"
            draft = _valid_change_spec(active['change_id'])
            draft['objective']['success_metric'] = 'UNKNOWN'
            draft['objective']['target'] = 'UNKNOWN'
            draft['acceptance_criteria'][0]['evidence'] = []
            (root / rel).write_text(dump_canonical_spec(draft), encoding='utf-8')
            fast, fast_metadata = _change_specs(root, [], route, 'fast')
            gate, gate_metadata = _change_specs(root, [], route, 'pr')
            self.assertEqual(fast.status, 'pass', fast.details)
            self.assertEqual(fast_metadata['specs'][0]['profile'], 'draft')
            self.assertEqual(gate.status, 'fail')
            self.assertEqual(gate_metadata['specs'][0]['profile'], 'gate')

    def test_docs_micro_exemption_is_exact(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Исправить документацию', 's1').to_dict()
            route.update({'complexity': 'micro', 'risk': 'low', 'delivery_expected': True})
            docs_check, docs_metadata = _change_specs(root, ['docs/x.md'], route, 'pr')
            code_check, code_metadata = _change_specs(root, ['src/x.py'], route, 'pr')
            self.assertEqual(docs_check.status, 'skip')
            self.assertTrue(docs_metadata['exempt'])
            self.assertEqual(code_check.status, 'fail')
            self.assertFalse(code_metadata['exempt'])


class QualityContourTests(unittest.TestCase):
    def test_unmarked_tree_with_ruff_still_runs_unittest(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            recorded: list[str] = []
            real_check = __import__('adaptive_grok.verification', fromlist=['_command_check'])._command_check

            def fake_exists(name: str) -> bool:
                if name == 'ruff':
                    return True
                if name in {'pytest', 'bandit', 'coverage', 'semgrep', 'trivy'}:
                    return False
                return shutil.which(name) is not None

            def fake_check(root_path, name, command, timeout=300):
                recorded.append(name)
                if name == 'ruff':
                    return CheckResult('ruff', 'pass', 'ok', command=command)
                return real_check(root_path, name, command, timeout)

            with patch('adaptive_grok.verification.command_exists', side_effect=fake_exists), patch(
                'adaptive_grok.verification._command_check',
                side_effect=fake_check,
            ):
                report = verify(root, mode='fast', record=False)
            self.assertIsNotNone(_check(report, 'ruff'))
            unittest_check = _check(report, 'python-unittest')
            self.assertIsNotNone(unittest_check)
            self.assertEqual(unittest_check['status'], 'pass')
            self.assertIsNone(_check(report, 'pytest'))

    def test_missing_ruff_is_skip_not_fail(self) -> None:
        with project_copy() as root:
            with patch('adaptive_grok.verification.command_exists', side_effect=_which_except('ruff')):
                results = _python(root)
            ruff = next((item for item in results if item.name == 'ruff'), None)
            self.assertIsNotNone(ruff)
            self.assertEqual(ruff.status, 'skip')
            self.assertNotEqual(ruff.status, 'fail')

    def test_unused_import_in_quality_path_fails_ruff(self) -> None:
        with project_copy() as root:
            planted = root / '.grok-stack/adaptive_grok/_planted_unused.py'
            planted.write_text('import unused_module\n', encoding='utf-8')
            with _PathTools({'ruff': _FAKE_RUFF}):
                results = _python(root, mode='fast')
            ruff = next((item for item in results if item.name == 'ruff'), None)
            self.assertIsNotNone(ruff)
            self.assertEqual(ruff.status, 'fail')

    def test_pytest_wins_but_ruff_and_bandit_run_first(self) -> None:
        with project_copy() as root:
            (root / 'pyproject.toml').write_text('[project]\nname = "demo"\n', encoding='utf-8')
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            order: list[str] = []

            def fake_exists(name: str) -> bool:
                return name in {'pytest', 'ruff', 'bandit'}

            def fake_check(root_path, name, command, timeout=300):
                order.append(name)
                return CheckResult(name, 'pass', 'ok', command=command)

            with patch('adaptive_grok.verification.command_exists', side_effect=fake_exists), patch(
                'adaptive_grok.verification._command_check',
                side_effect=fake_check,
            ):
                results = _python(root)
            names = _names(results)
            self.assertIn('ruff', names)
            self.assertIn('bandit', names)
            self.assertIn('pytest', names)
            self.assertNotIn('python-unittest', names)
            self.assertLess(names.index('ruff'), names.index('pytest'))
            self.assertLess(names.index('bandit'), names.index('pytest'))
            self.assertLess(order.index('ruff'), order.index('pytest'))
            self.assertLess(order.index('bandit'), order.index('pytest'))

    def test_missing_bandit_is_skip_and_secret_scan_remains(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            with patch('adaptive_grok.verification.command_exists', side_effect=_which_except('bandit')):
                report = verify(root, mode='fast', record=False)
            bandit = _check(report, 'bandit')
            self.assertIsNotNone(bandit)
            self.assertEqual(bandit['status'], 'skip')
            self.assertIsNotNone(_check(report, 'secret-scan'))

    def test_eval_in_product_path_fails_bandit(self) -> None:
        with project_copy() as root:
            planted = root / '.grok-stack/adaptive_grok/_planted_eval.py'
            planted.write_text('value = eval("1 + 1")\n', encoding='utf-8')
            with _PathTools({'bandit': _FAKE_BANDIT}):
                results = _python(root, mode='fast')
            bandit = next((item for item in results if item.name == 'bandit'), None)
            self.assertIsNotNone(bandit)
            self.assertEqual(bandit.status, 'fail')

    def test_eval_only_in_tests_does_not_fail_bandit(self) -> None:
        with project_copy() as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_eval_plant.py').write_text(
                'import unittest\nvalue = eval("1 + 1")\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n',
                encoding='utf-8',
            )
            with _PathTools({'bandit': _FAKE_BANDIT}):
                results = _python(root, mode='fast')
            bandit = next((item for item in results if item.name == 'bandit'), None)
            self.assertIsNotNone(bandit)
            self.assertNotEqual(bandit.status, 'fail')

    def test_secret_scan_still_fails_when_bandit_present(self) -> None:
        with project_copy(git=True) as root:
            fake_secret = 'abcde' * 5
            (root / 'config.php').write_text("<?php $" + "api_key = '" + fake_secret + "';", encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            with _PathTools({'bandit': _FAKE_BANDIT}):
                report = verify(root, mode='fast', record=False)
            secret = _check(report, 'secret-scan')
            self.assertIsNotNone(secret)
            self.assertEqual(secret['status'], 'fail')
            self.assertIsNotNone(_check(report, 'bandit'))

    def test_coverage_skip_when_missing_in_pr_mode(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            with patch('adaptive_grok.verification.command_exists', side_effect=_which_except('coverage', 'ruff', 'bandit', 'pytest')):
                report = verify(root, mode='pr', record=False)
            coverage = _check(report, 'coverage')
            self.assertIsNotNone(coverage)
            self.assertEqual(coverage['status'], 'skip')
            unittest_check = _check(report, 'python-unittest')
            self.assertIsNotNone(unittest_check)
            self.assertEqual(unittest_check['status'], 'pass')

    def test_fast_mode_does_not_fail_closed_on_coverage(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            (root / '.coveragerc').write_text('[report]\nfail_under = 100\n', encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            with _PathTools({'coverage': _FAKE_COVERAGE_FAIL_REPORT}):
                report = verify(root, mode='fast', record=False)
            unittest_check = _check(report, 'python-unittest')
            self.assertIsNotNone(unittest_check)
            self.assertEqual(unittest_check['status'], 'pass')
            coverage = _check(report, 'coverage')
            if coverage is not None:
                self.assertNotEqual(coverage['status'], 'fail')

    def test_coverage_fail_under_on_tiny_pr_fixture(self) -> None:
        with project_copy(git=True) as root:
            tests_dir = root / 'tests'
            tests_dir.mkdir()
            (tests_dir / 'test_ok.py').write_text(_PASSING_UNITTEST, encoding='utf-8')
            (root / '.coveragerc').write_text('[report]\nfail_under = 100\n', encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            with _PathTools({'coverage': _FAKE_COVERAGE_FAIL_REPORT}):
                report = verify(root, mode='pr', record=False)
            coverage = _check(report, 'coverage')
            self.assertIsNotNone(coverage)
            self.assertEqual(coverage['status'], 'fail')

    def test_this_repo_shaped_tree_omits_bucket_b(self) -> None:
        with project_copy(git=True) as root:
            self.assertFalse((root / 'package.json').exists())
            self.assertFalse((root / 'Dockerfile').exists())
            self.assertFalse((root / 'semgrep.yaml').exists())
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            report = verify(root, mode='fast', record=False)
            names = [item['name'] for item in report['checks']]
            self.assertNotIn('semgrep', names)
            self.assertNotIn('trivy-config', names)
            self.assertFalse(any(name.startswith('npm-') for name in names))

    def test_semgrep_signal_without_binary_is_skip(self) -> None:
        with project_copy(git=True) as root:
            (root / 'semgrep.yaml').write_text('rules: []\n', encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            with patch('adaptive_grok.verification.command_exists', side_effect=_which_except('semgrep')):
                report = verify(root, mode='fast', record=False)
            semgrep = _check(report, 'semgrep')
            self.assertIsNotNone(semgrep)
            self.assertEqual(semgrep['status'], 'skip')

    def test_trivy_signal_without_binary_is_skip(self) -> None:
        with project_copy(git=True) as root:
            (root / 'Dockerfile').write_text('FROM scratch\n', encoding='utf-8')
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['quality_profiles'] = ['base']
            set_active_route(root, route)
            with patch('adaptive_grok.verification.command_exists', side_effect=_which_except('trivy')):
                report = verify(root, mode='fast', record=False)
            trivy = _check(report, 'trivy-config')
            self.assertIsNotNone(trivy)
            self.assertEqual(trivy['status'], 'skip')

    def test_npm_prettier_emitted_when_script_present(self) -> None:
        with project_copy() as root:
            (root / 'package.json').write_text(
                json.dumps({'scripts': {'prettier': 'prettier --check .'}}),
                encoding='utf-8',
            )
            with patch('adaptive_grok.verification.command_exists', side_effect=_which_only('npm')), patch(
                'adaptive_grok.verification._command_check',
                side_effect=lambda root_path, name, command, timeout=300: CheckResult(name, 'pass', 'ok', command=command),
            ):
                results = _node(root, 'fast')
            self.assertIn('npm-prettier', _names(results))


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
