from __future__ import annotations

import sys
import json
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.change import start_change, transition
from adaptive_grok.architecture import architecture_fingerprint, contract_inventory, load_architecture
from adaptive_grok.architecture_diagrams import render_diagrams
from adaptive_grok.architecture_diff import (
    ArchitectureError,
    diff_architecture,
    select_architecture_comparison_base,
)
from adaptive_grok.receipts import (
    active_architecture_binding,
    active_governance_binding,
    invalidate_receipts,
    validate_evidence,
    write_receipt,
)
from adaptive_grok.router import build_route
from adaptive_grok.state import get_active_change, get_active_route, set_active_route
from adaptive_grok.verification import _architecture_check, verify
from adaptive_grok.spec import dump_canonical_spec
from tests._support import project_copy
from tests.test_architecture_model import _rules, _system

_PASSING_UNITTEST = (
    'import unittest\n'
    '\n'
    'class OkTests(unittest.TestCase):\n'
    '    def test_ok(self) -> None:\n'
    '        self.assertTrue(True)\n'
)

_ADOPTION_BASE = '25bfbe59ea188d9687b20a9caad19e7db3d031f8'
_PRE_ADOPTION_ROUTE_BASE = '069fe8226addb8a1922dde3db4e753434baa3a3d'
_ALTERNATE_PRE_ADOPTION_ROUTE_BASE = 'd17e95d9a99db2495c81f66053f0eebc7ae47d8d'


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
            for name in ('requirements.md', 'architecture.md'):
                text = (change / name).read_text(encoding='utf-8')
                self.assertIn('Canonical governance JSON', text)
                self.assertIn('non-authoritative context', text)
                self.assertNotIn('{{GOVERNANCE_AUTHORITY_NOTICE}}', text)
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
    @staticmethod
    def _adopt_architecture(root: Path) -> None:
        for rel in ("architecture", "schemas", "engineering/contracts"):
            source = ROOT / rel
            target = root / rel
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)

    @staticmethod
    def _adopt_governance(root: Path) -> None:
        shutil.copytree(ROOT / "governance", root / "governance")
        schemas = root / "schemas"
        schemas.mkdir(exist_ok=True)
        for name in (
            "canonical-example.schema.json",
            "debt-entry.schema.json",
            "governance-handoff-v1.schema.json",
            "governance-rule.schema.json",
        ):
            shutil.copy2(ROOT / "schemas" / name, schemas / name)

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

    @staticmethod
    def _unrelated_adopted_repo(
        root: Path,
        *,
        base_marker: bool = False,
        base_models: tuple[bool, bool] = (False, False),
    ) -> str:
        subprocess.run(['git', 'init', '-q', '-b', 'main'], cwd=root, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=root, check=True)
        subprocess.run(
            ['git', 'config', 'user.email', 'test@example.com'], cwd=root, check=True
        )
        schemas = root / 'schemas'
        schemas.mkdir()
        for name in ('architecture-system.schema.json', 'architecture-rules.schema.json'):
            shutil.copy2(ROOT / 'schemas' / name, schemas / name)
        architecture = root / 'architecture'
        architecture.mkdir()
        if base_models[0]:
            (architecture / 'system.yaml').write_text(
                json.dumps(_system(), sort_keys=True, indent=2) + '\n', encoding='utf-8'
            )
        if base_models[1]:
            (architecture / 'rules.yaml').write_text(
                json.dumps(_rules(), sort_keys=True, indent=2) + '\n', encoding='utf-8'
            )
        if base_marker:
            (architecture / 'adoption.json').write_text(
                '{\n  "architecture_id": "ARCH-TEST",\n  "schema_version": 1,\n  "state": "adopted"\n}\n',
                encoding='utf-8',
            )
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        subprocess.run(['git', 'commit', '-qm', 'consumer route base'], cwd=root, check=True)
        base = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=root, text=True, encoding='utf-8'
        ).strip()

        (architecture / 'system.yaml').write_text(
            json.dumps(_system(), sort_keys=True, indent=2) + '\n', encoding='utf-8'
        )
        (architecture / 'rules.yaml').write_text(
            json.dumps(_rules(), sort_keys=True, indent=2) + '\n', encoding='utf-8'
        )
        (architecture / 'adoption.json').write_text(
            '{\n  "architecture_id": "ARCH-TEST",\n  "schema_version": 1,\n  "state": "adopted"\n}\n',
            encoding='utf-8',
        )
        generated = architecture / 'generated'
        generated.mkdir()
        for name, artifact in render_diagrams(load_architecture(root)).items():
            (generated / f'{name}.mmd').write_text(artifact, encoding='utf-8')
        return base

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

    def test_adopted_receipt_binds_architecture_and_preserves_spec_criteria(self) -> None:
        with project_copy(git=True) as root:
            self._adopt_architecture(root)
            route = build_route(root, 'Добавить функцию', 's1').to_dict()
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            start_change(root)
            active = get_active_change(root) or {}
            self._install_spec(root, active, {'AC-001': {'receipt': 'verification'}})
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt architecture'], cwd=root, check=True)
            receipt_path = write_receipt(root, 'verification', 'pass')
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            self.assertRegex(receipt['architecture_digest'], r'^[0-9a-f]{64}$')
            self.assertRegex(receipt['architecture_fingerprint'], r'^[0-9a-f]{64}$')
            self.assertEqual(receipt['criterion_ids'], ['AC-001'])
            self.assertEqual(validate_evidence(root, get_active_route(root) or route), [])
            receipt.pop('architecture_digest')
            receipt.pop('architecture_fingerprint')
            receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
            self.assertTrue(any('architecture binding stale' in gap for gap in validate_evidence(root, route)))

    def test_receipt_binds_governance_and_stales_when_its_schema_changes(self) -> None:
        with project_copy(git=True) as root:
            self._adopt_architecture(root)
            self._adopt_governance(root)
            route = build_route(root, 'Review governed code', 's1').to_dict()
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt governed architecture'], cwd=root, check=True)

            receipt_path = write_receipt(root, 'verification', 'pass')
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            original = active_governance_binding(root, route)
            self.assertIsNotNone(original)
            assert original is not None
            self.assertEqual(receipt['governance_contract_version'], 1)
            self.assertEqual(receipt['governance_digest'], original['governance_digest'])
            self.assertEqual(
                receipt['governance_evidence_digest'],
                original['governance_evidence_digest'],
            )

            schema_path = root / 'schemas/governance-rule.schema.json'
            schema = json.loads(schema_path.read_text(encoding='utf-8'))
            schema['properties']['rules']['maxItems'] = 511
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                encoding='utf-8',
            )
            changed = active_governance_binding(root, route)
            self.assertIsNotNone(changed)
            assert changed is not None
            self.assertNotEqual(original['governance_digest'], changed['governance_digest'])
            self.assertNotEqual(
                original['governance_evidence_digest'],
                changed['governance_evidence_digest'],
            )
            self.assertTrue(
                any(
                    'governance binding stale' in gap
                    for gap in validate_evidence(root, route)
                )
            )

    def test_governance_failure_blocks_receipt_recording(self) -> None:
        with project_copy(git=True) as root:
            self._adopt_architecture(root)
            self._adopt_governance(root)
            route = build_route(root, 'Review governed code', 's1').to_dict()
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt governed architecture'], cwd=root, check=True)
            (root / 'governance/rules/index.json').write_text('{', encoding='utf-8')

            with self.assertRaisesRegex(RuntimeError, 'governance'):
                write_receipt(root, 'verification', 'pass')
            receipt_path = (
                root
                / '.grok-stack/runtime/receipts'
                / route['route_id']
                / 'verification.json'
            )
            self.assertFalse(receipt_path.exists())

    def test_governance_evidence_rotates_with_architecture_digest(self) -> None:
        with project_copy(git=True) as root:
            self._adopt_architecture(root)
            self._adopt_governance(root)
            route = build_route(root, 'Review governed architecture', 's1').to_dict()
            set_active_route(root, route)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'adopt governed architecture'], cwd=root, check=True)
            original = active_governance_binding(root, route)
            self.assertIsNotNone(original)
            assert original is not None

            system_path = root / 'architecture/system.yaml'
            system = json.loads(system_path.read_text(encoding='utf-8'))
            system['nodes'][0]['owner'] = 'changed architecture owner'
            system_path.write_text(
                json.dumps(system, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                encoding='utf-8',
            )
            changed = active_governance_binding(root, route)
            self.assertIsNotNone(changed)
            assert changed is not None
            self.assertEqual(original['governance_digest'], changed['governance_digest'])
            self.assertNotEqual(
                original['governance_architecture_digest'],
                changed['governance_architecture_digest'],
            )
            self.assertNotEqual(
                original['governance_evidence_digest'],
                changed['governance_evidence_digest'],
            )

    def test_pre_adoption_route_base_uses_one_architecture_comparison_base(self) -> None:
        route = {'base_commit': _PRE_ADOPTION_ROUTE_BASE}
        binding = active_architecture_binding(ROOT, route)
        self.assertIsNotNone(binding)
        assert binding is not None

        result, evidence = _architecture_check(ROOT, route)
        self.assertEqual(result.status, 'fail')
        self.assertEqual(binding['architecture_base_sha'], _ADOPTION_BASE)
        self.assertEqual(evidence['exact_base_sha'], _ADOPTION_BASE)
        self.assertEqual(evidence['architecture_fingerprint'], binding['architecture_fingerprint'])
        self.assertEqual(binding['architecture_route_base_sha'], _PRE_ADOPTION_ROUTE_BASE)
        self.assertEqual(binding['architecture_base_kind'], 'frozen_adoption')
        self.assertEqual(
            evidence['architecture_base_kind'], binding['architecture_base_kind']
        )
        self.assertTrue(binding['architecture_bootstrap_baseline'])
        self.assertEqual(
            evidence['architecture_bootstrap_baseline'],
            binding['architecture_bootstrap_baseline'],
        )
        self.assertTrue(evidence['baseline_introduced'])

        snapshot = load_architecture(ROOT)
        records = contract_inventory(ROOT, snapshot)
        expected_fingerprint = architecture_fingerprint(
            ROOT,
            snapshot,
            base_sha=_ADOPTION_BASE,
            head_sha=f"worktree:{binding['architecture_head_commit']}",
            contract_digests={record.path: record.digest for record in records},
        )
        self.assertEqual(binding['architecture_fingerprint'], expected_fingerprint)
        self.assertRegex(evidence['architecture_evidence_digest'], r'^[0-9a-f]{64}$')

    def test_unrelated_consumer_bootstrap_is_explicit_and_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory(prefix='adaptive-grok-consumer-bootstrap-') as tmp:
            root = Path(tmp)
            base = self._unrelated_adopted_repo(root)
            route = {
                'base_commit': base,
                'required_evidence': ['verification'],
                'route_id': 'consumer-bootstrap',
            }
            set_active_route(root, route)
            self.assertNotEqual(
                subprocess.run(
                    ['git', 'cat-file', '-e', _ADOPTION_BASE + '^{commit}'],
                    cwd=root,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode,
                0,
            )

            selection = select_architecture_comparison_base(root, route)
            self.assertEqual(selection.comparison_base_sha, base)
            self.assertTrue(selection.bootstrap_baseline)
            with self.assertRaises(ArchitectureError):
                diff_architecture(root, base_sha=base, worktree=True)

            receipt = json.loads(
                write_receipt(root, 'verification', 'pass').read_text(encoding='utf-8')
            )
            result, evidence = _architecture_check(root, route)
            self.assertEqual(result.status, 'pass')
            self.assertEqual(receipt['architecture_base_sha'], base)
            self.assertEqual(receipt['architecture_base_sha'], evidence['exact_base_sha'])
            self.assertEqual(
                receipt['architecture_fingerprint'], evidence['architecture_fingerprint']
            )
            self.assertTrue(receipt['architecture_bootstrap_baseline'])
            self.assertTrue(evidence['architecture_bootstrap_baseline'])
            self.assertEqual(receipt['architecture_base_kind'], 'route_pre_adoption')
            self.assertEqual(
                receipt['architecture_base_kind'], evidence['architecture_base_kind']
            )
            self.assertTrue(evidence['baseline_introduced'])

    def test_route_base_marker_with_partial_model_fails_selection(self) -> None:
        with tempfile.TemporaryDirectory(prefix='adaptive-grok-marker-partial-') as tmp:
            root = Path(tmp)
            base = self._unrelated_adopted_repo(
                root, base_marker=True, base_models=(True, False)
            )
            with self.assertRaisesRegex(ArchitectureError, 'partially missing'):
                select_architecture_comparison_base(root, {'base_commit': base})

    def test_route_base_marker_with_both_models_missing_fails_selection(self) -> None:
        with tempfile.TemporaryDirectory(prefix='adaptive-grok-marker-missing-') as tmp:
            root = Path(tmp)
            base = self._unrelated_adopted_repo(root, base_marker=True)
            with self.assertRaisesRegex(ArchitectureError, 'adopted architecture model is missing'):
                select_architecture_comparison_base(root, {'base_commit': base})

    def test_route_base_partial_model_without_marker_fails_selection(self) -> None:
        with tempfile.TemporaryDirectory(prefix='adaptive-grok-unmarked-partial-') as tmp:
            root = Path(tmp)
            base = self._unrelated_adopted_repo(root, base_models=(False, True))
            with self.assertRaisesRegex(ArchitectureError, 'partially missing'):
                select_architecture_comparison_base(root, {'base_commit': base})

    def test_route_base_remains_a_separate_architecture_staleness_binding(self) -> None:
        with tempfile.TemporaryDirectory(prefix='adaptive-grok-receipt-base-') as tmp:
            root = Path(tmp) / 'project'
            subprocess.run(
                ['git', 'clone', '-q', '--no-local', str(ROOT), str(root)],
                check=True,
            )
            route = {
                'base_commit': _PRE_ADOPTION_ROUTE_BASE,
                'required_evidence': ['verification'],
                'route_id': 'receipt-base-regression',
            }
            set_active_route(root, route)
            receipt = json.loads(
                write_receipt(root, 'verification', 'pass').read_text(encoding='utf-8')
            )
            result, evidence = _architecture_check(root, route)
            self.assertEqual(result.status, 'fail')
            self.assertEqual(receipt['architecture_base_sha'], _ADOPTION_BASE)
            self.assertEqual(receipt['architecture_base_sha'], evidence['exact_base_sha'])
            self.assertEqual(
                receipt['architecture_fingerprint'], evidence['architecture_fingerprint']
            )
            self.assertEqual(receipt['architecture_route_base_sha'], _PRE_ADOPTION_ROUTE_BASE)

            route['base_commit'] = _ALTERNATE_PRE_ADOPTION_ROUTE_BASE
            set_active_route(root, route)
            current = active_architecture_binding(root, route)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current['architecture_base_sha'], _ADOPTION_BASE)
            self.assertEqual(
                current['architecture_fingerprint'], receipt['architecture_fingerprint']
            )
            self.assertTrue(
                any(
                    'architecture binding stale' in gap
                    for gap in validate_evidence(root, route)
                )
            )

            route['base_commit'] = 'f' * 40
            set_active_route(root, route)
            self.assertTrue(
                any(
                    'architecture binding stale' in gap
                    for gap in validate_evidence(root, route)
                )
            )

    def test_unconfigured_consumer_keeps_legacy_receipt_compatibility(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current code', 's1').to_dict()
            route['required_evidence'] = ['verification']
            set_active_route(root, route)
            path = write_receipt(root, 'verification', 'pass')
            receipt = json.loads(path.read_text(encoding='utf-8'))
            self.assertNotIn('architecture_digest', receipt)
            self.assertEqual(validate_evidence(root, route), [])

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
