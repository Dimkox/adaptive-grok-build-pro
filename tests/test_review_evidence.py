from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.review_evidence import ReviewEvidenceError, validate_review_report  # noqa: E402
from adaptive_grok.receipts import validate_evidence, write_receipt  # noqa: E402
from adaptive_grok.router import build_route  # noqa: E402
from adaptive_grok.state import set_active_route  # noqa: E402
from tests._support import project_copy, write_review_report  # noqa: E402


def _source_claim(root: Path) -> dict:
    source = root / 'src.py'
    source.write_text('alpha = 1\nbeta = 2\n', encoding='utf-8')
    span = b'alpha = 1\nbeta = 2\n'
    return {
        'id': 'SRC-001',
        'type': 'source_citation',
        'statement': 'The source defines alpha and beta.',
        'citations': [{
            'path': 'src.py', 'start_line': 1, 'end_line': 2,
            'span_sha256': hashlib.sha256(span).hexdigest(),
        }],
    }


def _report(root: Path, *, claims: list[dict] | None = None, revision: dict | None = None) -> dict:
    return {
        'schema_version': 1,
        'review_kind': 'code_review',
        'status': 'pass',
        'revision': revision or {
            'revision_id': 'rev-001', 'previous_report': None,
            'previous_digest': None, 'changed_claim_ids': [],
            'fresh_evidence_claim_ids': [], 'changed_report_fields': [],
        },
        'claims': claims if claims is not None else [_source_claim(root)],
    }


def _write_report(root: Path, relative: str, data: dict) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    return path


class ReviewEvidenceTests(unittest.TestCase):
    def test_accepts_confined_structured_report_and_current_source_span(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_report(root, 'engineering/reviews/code.json', _report(root))
            validated = validate_review_report(root, 'engineering/reviews/code.json', expected_kind='code_review')
            self.assertEqual(validated['report_path'], 'engineering/reviews/code.json')
            self.assertEqual(len(validated['report_digest']), 64)
            self.assertEqual(validated['summary']['source_citation_count'], 1)
            broken = _report(root)
            broken['status'] = 'fail'
            _write_report(root, 'engineering/reviews/code.json', broken)
            with self.assertRaises(ReviewEvidenceError):
                validate_review_report(root, 'engineering/reviews/code.json', expected_kind='code_review', expected_status='pass')

    def test_rejects_escaping_missing_non_regular_and_oversized_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root, outside = Path(tmp), Path(outside_tmp)
            _write_report(root, 'report.json', _report(root))
            (outside / 'report.json').write_text('{}', encoding='utf-8')
            (root / 'escape.json').symlink_to(outside / 'report.json')
            (root / 'directory.json').mkdir()
            (root / 'large.json').write_bytes(b' ' * (512 * 1024 + 1))
            for path in ('../report.json', str(outside / 'report.json'), 'escape.json', 'missing.json', 'directory.json', 'large.json'):
                with self.subTest(path=path), self.assertRaises(ReviewEvidenceError):
                    validate_review_report(root, path, expected_kind='code_review')

    def test_rejects_missing_source_bad_span_wrong_digest_and_symlink_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root, outside = Path(tmp), Path(outside_tmp)
            source = _source_claim(root)
            report = _report(root, claims=[source])
            for mutate in (
                lambda c: c['citations'][0].update(path='../src.py'),
                lambda c: c['citations'][0].update(path='absent.py'),
                lambda c: c['citations'][0].update(start_line=0),
                lambda c: c['citations'][0].update(end_line=99),
                lambda c: c['citations'][0].update(span_sha256='0' * 64),
            ):
                broken = json.loads(json.dumps(report))
                mutate(broken['claims'][0])
                _write_report(root, 'report.json', broken)
                with self.assertRaises(ReviewEvidenceError):
                    validate_review_report(root, 'report.json', expected_kind='code_review')
            (outside / 'source.py').write_text('secret = 1\n', encoding='utf-8')
            (root / 'linked.py').symlink_to(outside / 'source.py')
            broken = _report(root, claims=[{
                'id': 'SRC-001', 'type': 'source_citation', 'statement': 'linked source',
                'citations': [{'path': 'linked.py', 'start_line': 1, 'end_line': 1, 'span_sha256': hashlib.sha256(b'secret = 1\n').hexdigest()}],
            }])
            _write_report(root, 'report.json', broken)
            with self.assertRaises(ReviewEvidenceError):
                validate_review_report(root, 'report.json', expected_kind='code_review')

    def test_execution_records_are_shape_checked_but_always_self_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_claim = {
                'id': 'EXEC-001', 'type': 'execution', 'statement': 'A command was reported.',
                'command': {
                    'argv': ['python3', '-m', 'unittest'], 'cwd': '.', 'exit_code': 0,
                    'stdout_excerpt': 'OK', 'stderr_excerpt': '',
                    'provenance': 'self_reported_unverified',
                    'probe': {'schema_id': 'adaptive_grok.architecture.unsupported_schema', 'schema_version': 1, 'input': {'schema': {'type': 'string'}}},
                },
            }
            valid = _report(root, claims=[command_claim])
            _write_report(root, 'report.json', valid)
            checked = validate_review_report(root, 'report.json', expected_kind='code_review')
            self.assertEqual(checked['summary']['execution_provenance'], 'self_reported_unverified')
            for mutate in (
                lambda c: c.update(command='python3 -m unittest'),
                lambda c: c['command'].update(argv='python3 -m unittest'),
                lambda c: c['command'].update(exit_code=True),
                lambda c: c['command'].update(provenance='trusted_capture'),
                lambda c: c['command'].update(probe={'schema_id': 'adaptive_grok.architecture.unsupported_schema', 'schema_version': 1, 'input': {'schema': '{"type":"string"}'}}),
                lambda c: c['command'].update(probe={'schema_id': 'unknown.probe', 'schema_version': 1, 'input': {'schema': {'type': 'string'}}}),
                lambda c: c['command'].update(probe={'schema_id': 'adaptive_grok.architecture.unsupported_schema', 'schema_version': 1.0, 'input': {'schema': {'type': 'string'}}}),
                lambda c: c['command'].update(cwd='../outside'),
            ):
                broken = json.loads(json.dumps(valid))
                mutate(broken['claims'][0])
                _write_report(root, 'report.json', broken)
                with self.assertRaises(ReviewEvidenceError):
                    validate_review_report(root, 'report.json', expected_kind='code_review')

    def test_revision_requires_existing_matching_predecessor_and_fresh_changed_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = _write_report(root, 'reports/rev1.json', _report(root))
            previous_digest = hashlib.sha256(previous.read_bytes()).hexdigest()
            revision = {
                'revision_id': 'rev-002', 'previous_report': 'reports/rev1.json',
                'previous_digest': previous_digest, 'changed_claim_ids': ['SRC-001'],
                'fresh_evidence_claim_ids': ['SRC-001'], 'changed_report_fields': [],
            }
            repeated_claim = _source_claim(root)
            repeated_claim['statement'] = 'The narrative changed without new source evidence.'
            repeated = _report(root, claims=[repeated_claim], revision=revision)
            _write_report(root, 'reports/rev2.json', repeated)
            with self.assertRaisesRegex(ReviewEvidenceError, 'repeats its predecessor evidence'):
                validate_review_report(root, 'reports/rev2.json', expected_kind='code_review')

            (root / 'src.py').write_text('alpha = 1\nbeta = 2\ngamma = 3\n', encoding='utf-8')
            new_span = b'beta = 2\ngamma = 3\n'
            current = _report(root, claims=[{
                'id': 'SRC-001', 'type': 'source_citation',
                'statement': 'The source now defines beta and gamma.',
                'citations': [{
                    'path': 'src.py', 'start_line': 2, 'end_line': 3,
                    'span_sha256': hashlib.sha256(new_span).hexdigest(),
                }],
            }], revision=revision)
            _write_report(root, 'reports/rev2.json', current)
            validate_review_report(root, 'reports/rev2.json', expected_kind='code_review')
            for field, value in (('previous_digest', '0' * 64), ('fresh_evidence_claim_ids', [])):
                broken = json.loads(json.dumps(current))
                broken['revision'][field] = value
                _write_report(root, 'reports/rev2.json', broken)
                with self.assertRaises(ReviewEvidenceError):
                    validate_review_report(root, 'reports/rev2.json', expected_kind='code_review')

            duplicate = json.loads(json.dumps(current))
            duplicate['revision']['revision_id'] = 'rev-001'
            _write_report(root, 'reports/rev2.json', duplicate)
            with self.assertRaises(ReviewEvidenceError):
                validate_review_report(root, 'reports/rev2.json', expected_kind='code_review')

    def test_revision_derives_statement_and_status_changes_and_rejects_removal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_claim(root)
            execution = {
                'id': 'EXEC-B', 'type': 'execution', 'statement': 'A command was reported.',
                'command': {
                    'argv': ['python3', '-m', 'unittest'], 'cwd': '.', 'exit_code': 0,
                    'stdout_excerpt': 'OK', 'stderr_excerpt': '', 'provenance': 'self_reported_unverified',
                },
            }
            previous = _write_report(root, 'reports/prev.json', _report(root, claims=[source, execution]))
            previous_digest = hashlib.sha256(previous.read_bytes()).hexdigest()
            changed_execution = json.loads(json.dumps(execution))
            changed_execution['command']['argv'] = ['python3', '-m', 'unittest', 'tests.test_x']
            contradicted_source = json.loads(json.dumps(source))
            contradicted_source['statement'] = 'The source does not define alpha or beta.'
            revision = {
                'revision_id': 'rev-002', 'previous_report': 'reports/prev.json',
                'previous_digest': previous_digest, 'changed_claim_ids': ['EXEC-B'],
                'fresh_evidence_claim_ids': ['EXEC-B'], 'changed_report_fields': [],
            }
            current = _report(root, claims=[contradicted_source, changed_execution], revision=revision)
            _write_report(root, 'reports/current.json', current)
            with self.assertRaisesRegex(ReviewEvidenceError, 'exactly match the derived claim changes'):
                validate_review_report(root, 'reports/current.json', expected_kind='code_review')

            removed = _report(root, claims=[source], revision={
                **revision, 'changed_claim_ids': ['EXEC-B'], 'fresh_evidence_claim_ids': ['EXEC-B'],
            })
            _write_report(root, 'reports/current.json', removed)
            with self.assertRaisesRegex(ReviewEvidenceError, 'cannot be removed'):
                validate_review_report(root, 'reports/current.json', expected_kind='code_review')

            status_only = _report(root, claims=[source, execution], revision={
                **revision, 'changed_claim_ids': [], 'fresh_evidence_claim_ids': [], 'changed_report_fields': ['status'],
            })
            status_only['status'] = 'fail'
            _write_report(root, 'reports/current.json', status_only)
            with self.assertRaisesRegex(ReviewEvidenceError, 'status transition requires fresh changed claims'):
                validate_review_report(root, 'reports/current.json', expected_kind='code_review')

            status_evidence = json.loads(json.dumps(execution))
            status_evidence['id'] = 'EXEC-C'
            status_evidence['statement'] = 'Additional evidence was reported.'
            status_transition = _report(root, claims=[source, execution, status_evidence], revision={
                **revision, 'changed_claim_ids': ['EXEC-C'], 'fresh_evidence_claim_ids': ['EXEC-C'], 'changed_report_fields': ['status'],
            })
            status_transition['status'] = 'fail'
            _write_report(root, 'reports/current.json', status_transition)
            validate_review_report(root, 'reports/current.json', expected_kind='code_review')

    def test_added_claim_omitted_from_change_lists_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_claim(root)
            execution = {
                'id': 'EXEC-A', 'type': 'execution', 'statement': 'An earlier command was reported.',
                'command': {
                    'argv': ['python3', '-m', 'unittest'], 'cwd': '.', 'exit_code': 0,
                    'stdout_excerpt': 'OK', 'stderr_excerpt': '', 'provenance': 'self_reported_unverified',
                },
            }
            previous = _write_report(root, 'reports/prev.json', _report(root, claims=[source, execution]))
            added = {
                'id': 'EXEC-B', 'type': 'execution', 'statement': 'A newly reported command.',
                'command': {
                    'argv': ['python3', '-m', 'unittest', 'tests.test_new'], 'cwd': '.', 'exit_code': 0,
                    'stdout_excerpt': 'OK', 'stderr_excerpt': '', 'provenance': 'self_reported_unverified',
                },
            }
            current = _report(root, claims=[source, execution, added], revision={
                'revision_id': 'rev-002', 'previous_report': 'reports/prev.json',
                'previous_digest': hashlib.sha256(previous.read_bytes()).hexdigest(),
                'changed_claim_ids': [], 'fresh_evidence_claim_ids': [], 'changed_report_fields': [],
            })
            _write_report(root, 'reports/current.json', current)
            with self.assertRaisesRegex(ReviewEvidenceError, 'changed_claim_ids must exactly match the derived claim changes'):
                validate_review_report(root, 'reports/current.json', expected_kind='code_review')

    def test_status_change_omitting_changed_report_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = _source_claim(root)
            previous = _write_report(root, 'reports/prev.json', _report(root, claims=[source]))
            current = _report(root, claims=[source], revision={
                'revision_id': 'rev-002', 'previous_report': 'reports/prev.json',
                'previous_digest': hashlib.sha256(previous.read_bytes()).hexdigest(),
                'changed_claim_ids': [], 'fresh_evidence_claim_ids': [], 'changed_report_fields': [],
            })
            current['status'] = 'fail'
            _write_report(root, 'reports/current.json', current)
            with self.assertRaisesRegex(ReviewEvidenceError, 'changed_report_fields must exactly match the derived report changes'):
                validate_review_report(root, 'reports/current.json', expected_kind='code_review')

    def test_passing_receipt_binds_report_digest_and_revalidation_detects_change_or_deletion(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current change', 's1').to_dict()
            route['required_evidence'] = ['code_review']
            set_active_route(root, route)
            report = write_review_report(root, 'code_review')
            report_rel = str(report.relative_to(root))
            receipt_path = write_receipt(root, 'code_review', 'pass', report_rel)
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            self.assertEqual(receipt['report_digest'], hashlib.sha256(report.read_bytes()).hexdigest())
            self.assertIn('source_citation_count', receipt['report_validation'])
            self.assertEqual(validate_evidence(root, route), [])

            report.write_text(report.read_text(encoding='utf-8') + ' ', encoding='utf-8')
            changed_gaps = validate_evidence(root, route)
            self.assertTrue(any('digest mismatch' in gap for gap in changed_gaps), changed_gaps)
            report.unlink()
            missing_gaps = validate_evidence(root, route)
            self.assertTrue(any('report is missing or invalid' in gap for gap in missing_gaps), missing_gaps)

    def test_passing_review_receipt_without_structured_report_is_rejected(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Review current change', 's1').to_dict()
            set_active_route(root, route)
            with self.assertRaises(ReviewEvidenceError):
                write_receipt(root, 'code_review', 'pass')


if __name__ == '__main__':
    unittest.main()
