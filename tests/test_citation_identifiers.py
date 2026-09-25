from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.citations import (
    audit_documents,
    corpus_identifiers,
    decline_reason,
    extract_citations,
    is_identifier_like,
)
from adaptive_grok.receipts import invalidate_receipts, receipt_echo, write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.state import set_active_route
from adaptive_grok.util import now_utc
from tests._support import project_copy

def _synthetic_hex(seed: int, length: int) -> str:
    """Build an identifier-shaped token without putting a high-entropy literal in the file.

    A scanner cannot be asked to disposition a secret that is not present, and these are
    fixture identifiers, not credentials.
    """
    digits = '0123456789abcdef'
    value = seed
    out: list[str] = []
    for _ in range(length):
        value = (value * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(digits[(value >> 16) % 16])
    return ''.join(out)


REAL_ID = _synthetic_hex(0x5EED, 64)
REAL_ROUTE_ID = _synthetic_hex(0x101112, 12)
FABRICATED_TAIL = REAL_ID[:12] + '0000'
FABRICATED_WHOLE = _synthetic_hex(0xF00D, 16)
FOREIGN_CORPUS_ID = _synthetic_hex(0xC0FFEE, 16)
UNKNOWN_GIT_ID = _synthetic_hex(0xBADC0DE, 20)
SHA512_SHAPE = _synthetic_hex(0x51D5, 128)
LINE_KEY = re.compile(r'^RECEIPT( [A-Za-z0-9_./-]+=("[^"]*"|\S+))+$')


class IdentifierExtractionTests(unittest.TestCase):
    def test_decimal_dates_and_counters_are_not_identifier_tokens(self) -> None:
        citations = extract_citations(
            'package 20260924 built 0000000000 port 80808080 at v2.0.19\n',
            'report.md',
        )

        self.assertEqual(citations, [])

    def test_hex_runs_are_taken_whole_and_once_per_line(self) -> None:
        text = f'bound {REAL_ID} again {REAL_ID} and short {REAL_ID[:20]}\n'
        citations = extract_citations(text, 'report.md')

        tokens = [item.token for item in citations]
        self.assertEqual(tokens, [REAL_ID, REAL_ID[:20]])
        self.assertTrue(all(item.line == 1 for item in citations))
        self.assertTrue(all(item.document == 'report.md' for item in citations))

    def test_identifier_likeness_rejects_degenerate_runs(self) -> None:
        self.assertFalse(is_identifier_like('12345678'))
        self.assertFalse(is_identifier_like('aaaaaaaa'))
        self.assertFalse(is_identifier_like('abc12'))
        self.assertFalse(is_identifier_like('ab' * 40))
        self.assertTrue(is_identifier_like('ff575f1e5c4b'))

    def test_a_hex_run_longer_than_the_ceiling_is_declined_for_a_name(self) -> None:
        # A sha512 was previously invisible to both the extractor and the corpus, which let a
        # fabricated long run read as a clean result. It must now be a counted decline.
        self.assertEqual(decline_reason(SHA512_SHAPE), 'over-max')
        self.assertEqual(decline_reason('1234567890'), 'decimal-only')
        self.assertIsNone(decline_reason(REAL_ROUTE_ID))

    def test_declined_runs_are_surfaced_instead_of_silently_absent(self) -> None:
        with project_copy(git=True) as root:
            result = audit_documents(
                root,
                [('report.md', f'fingerprint 1234567890 and sha512 {SHA512_SHAPE}\n')],
            )

            self.assertEqual(result['citation_count'], 0)
            self.assertEqual(result['declined_runs'], 2)
            self.assertEqual(result['declined_by_reason'], {'decimal-only': 1, 'over-max': 1})


class CorpusCorruptsItsOwnTrustTests(unittest.TestCase):
    """The corpus is machine state. Report prose must never launder a fabricated id."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix='grok-citation-')
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.root / '.grok-stack/runtime/receipts/r1').mkdir(parents=True)
        (self.root / '.grok-stack/runtime/receipts/r1/verification.json').write_text(
            json.dumps({'kind': 'verification', 'tree_fingerprint': REAL_ID, 'status': 'pass'}),
            encoding='utf-8',
        )

    def test_real_identifier_and_a_faithful_prefix_resolve(self) -> None:
        report = f'fingerprint {REAL_ID} and prefix {REAL_ID[:12]} both cited\n'
        result = audit_documents(self.root, [('report.md', report)])

        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['unresolved'], [])
        self.assertEqual(result['citation_count'], 2)

    def test_real_prefix_with_an_invented_tail_is_unresolved(self) -> None:
        # The incident shape from issue 206: a plausible hex that sits next to a real one.
        report = f'meter is byte-idempotent (fingerprint {FABRICATED_TAIL} unchanged)\n'
        result = audit_documents(self.root, [('report.md', report)])

        self.assertEqual(result['status'], 'fail')
        self.assertEqual([item['token'] for item in result['unresolved']], [FABRICATED_TAIL])

    def test_a_short_identifier_plus_an_invented_tail_is_unresolved(self) -> None:
        # The acceptance rule this pins used to exist: a citation longer than the real
        # identifier it prefixes was resolved whenever that identifier stood alone in the
        # corpus. Deleting that rule must turn this red, not leave the suite green.
        (self.root / '.grok-stack/runtime/receipts/r1/route.json').write_text(
            json.dumps({'route_id': REAL_ROUTE_ID}), encoding='utf-8'
        )
        invented = REAL_ROUTE_ID + 'deadbeef'

        result = audit_documents(self.root, [('report.md', f'route {invented} recorded it\n')])

        self.assertEqual(result['status'], 'fail')
        self.assertEqual([item['token'] for item in result['unresolved']], [invented])

    def test_a_token_only_repeated_in_report_prose_stays_unresolved(self) -> None:
        evidence = self.root / 'engineering/changes/20260924-x/evidence'
        evidence.mkdir(parents=True)
        (evidence / 'verification.md').write_text(f'prior report cited {FABRICATED_WHOLE}\n', encoding='utf-8')

        result = audit_documents(self.root, [('brief.md', f'as recorded {FABRICATED_WHOLE}\n')])

        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['unresolved'][0]['token'], FABRICATED_WHOLE)

    def test_prose_inside_machine_state_does_not_make_a_token_authoritative(self) -> None:
        # A change package is hand-written. A hex typed into a title or reason must not become
        # a real identifier for the whole tree; only an identifier-bearing key may do that.
        package = self.root / 'engineering/changes/20260924-x'
        package.mkdir(parents=True)
        (package / 'state.json').write_text(
            json.dumps({'title': f'work on {FABRICATED_WHOLE}', 'notes': [FABRICATED_TAIL]}),
            encoding='utf-8',
        )

        scan = corpus_identifiers(self.root)

        self.assertNotIn(FABRICATED_WHOLE, scan.identifiers)
        self.assertNotIn(FABRICATED_TAIL, scan.identifiers)

        (package / 'state.json').write_text(
            json.dumps({'history': [{'spec_fingerprint': FABRICATED_WHOLE}]}), encoding='utf-8'
        )
        self.assertIn(FABRICATED_WHOLE, corpus_identifiers(self.root).identifiers)

    def test_corpus_reads_only_machine_state_files(self) -> None:
        scan = corpus_identifiers(self.root)

        self.assertIn(REAL_ID, scan.identifiers)
        self.assertEqual(scan.files_read, 1)
        self.assertFalse(scan.truncated)

    def test_symlinked_and_oversized_corpus_entries_are_skipped(self) -> None:
        outside = self.root.parent / 'outside-secret.json'
        outside.write_text(json.dumps({'leak': FOREIGN_CORPUS_ID}), encoding='utf-8')
        self.addCleanup(outside.unlink, missing_ok=True)
        oversized = self.root.parent / 'huge-secret.json'
        oversized.write_bytes(
            (json.dumps({'leak': FOREIGN_CORPUS_ID + '00000000'}) + '\n').encode('utf-8')
            + b' ' * (4 * 1024 * 1024)
        )
        self.addCleanup(oversized.unlink, missing_ok=True)
        receipts = self.root / '.grok-stack/runtime/receipts/r1'
        (receipts / 'leak.json').symlink_to(outside)
        # A symlinked *directory* is followed by Path.glob, so containment has to be checked on
        # the resolved target rather than on the link text.
        escaping = self.root / '.grok-stack/runtime/receipts/linkdir'
        outside_dir = self.root.parent / 'outside-dir'
        outside_dir.mkdir(exist_ok=True)
        self.addCleanup(lambda: (outside_dir / 'deep.json').unlink(missing_ok=True), )
        (outside_dir / 'deep.json').write_text(json.dumps({'leak': FOREIGN_CORPUS_ID}), encoding='utf-8')
        escaping.symlink_to(outside_dir, target_is_directory=True)
        big = self.root / '.grok-stack/runtime/receipts/r1/huge-sidecar.json'
        big.write_bytes(oversized.read_bytes())

        result = audit_documents(self.root, [('report.md', f'cite {FOREIGN_CORPUS_ID}\n')])

        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['unresolved'][0]['token'], FOREIGN_CORPUS_ID)
        self.assertEqual(result['corpus_identifiers'], 1)
        self.assertGreaterEqual(result['corpus_files_skipped'], 1)
        self.assertNotIn(FOREIGN_CORPUS_ID + '00000000', corpus_identifiers(self.root).identifiers)
        self.assertTrue(oversized.is_file())
        self.assertTrue(result['corpus_files'] >= 1)
        self.assertNotIn('deep.json', [path.name for path in self.root.glob('.grok-stack/runtime/receipts/r1/*')])
        del big


class GitObjectResolutionTests(unittest.TestCase):
    def test_a_real_commit_prefix_resolves_even_though_no_receipt_repeats_it(self) -> None:
        with project_copy(git=True) as root:
            head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True)
            commit = head.stdout.strip()

            result = audit_documents(root, [('report.md', f'landed as {commit[:12]}\n')])

            self.assertEqual(result['status'], 'pass')
            self.assertEqual(result['unresolved'], [])
            self.assertFalse(result['git_probes_capped'])

    def test_an_unknown_object_id_is_not_resolved_by_git(self) -> None:
        self.assertTrue(is_identifier_like(UNKNOWN_GIT_ID))
        with project_copy(git=True) as root:
            result = audit_documents(root, [('report.md', f'landed as {UNKNOWN_GIT_ID}\n')])

            self.assertEqual(result['status'], 'fail')

    def test_the_git_hatch_only_makes_the_check_stricter(self) -> None:
        with project_copy(git=True) as root:
            head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True)
            commit = head.stdout.strip()
            previous = os.environ.get('GROK_CITATIONS_SKIP_GIT')
            os.environ['GROK_CITATIONS_SKIP_GIT'] = '1'
            self.addCleanup(
                lambda: (
                    os.environ.pop('GROK_CITATIONS_SKIP_GIT', None)
                    if previous is None
                    else os.environ.__setitem__('GROK_CITATIONS_SKIP_GIT', previous)
                )
            )

            result = audit_documents(root, [('report.md', f'landed as {commit[:12]}\n')])

            self.assertEqual(result['status'], 'fail')
            self.assertTrue(result['git_probes_capped'])


class ReceiptEchoTests(unittest.TestCase):
    def test_echo_is_one_line_carrying_the_bound_fingerprint(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            started = now_utc()
            write_receipt(root, 'verification', 'pass')

            line = receipt_echo(root, 'verification', not_before=started)

            self.assertNotIn('\n', line)
            self.assertTrue(line.startswith('RECEIPT kind=verification status=pass '))
            self.assertIn('fingerprint=', line)
            self.assertIn('path=.grok-stack/runtime/receipts/', line)
            self.assertIn(f'route={route["route_id"]}', line)
            self.assertRegex(echoed_fingerprint(line), r'^[0-9a-f]{64}$')

    def test_echo_reports_unavailable_instead_of_printing_nothing(self) -> None:
        with project_copy(git=True) as root:
            line = receipt_echo(root, 'verification', not_before=now_utc())

            self.assertTrue(line.startswith('RECEIPT kind=verification status=unavailable'))
            self.assertIn('reason=no-active-route', line)

    def test_echo_refuses_to_present_an_older_receipt_as_this_run(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')

            (root / 'README-echo-probe.md').write_text('drift\n', encoding='utf-8')
            line = receipt_echo(
                root, 'verification', expect_tree_fingerprint='e' * 64, not_before=now_utc()
            )

            self.assertIn('status=unavailable', line)
            self.assertIn('reason=tree-fingerprint-mismatch', line)
            self.assertNotIn(' fingerprint=', line)

    def test_echo_refuses_a_receipt_this_run_never_recorded(self) -> None:
        # The governance-fail shape: verify() records nothing, the tree is untouched, so the
        # fingerprint guard passes and only the run bound can refuse the old receipt.
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')
            later = '2099-01-01T00:00:00+00:00'

            line = receipt_echo(root, 'verification', not_before=later)

            self.assertIn('status=unavailable', line)
            self.assertIn('reason=not-recorded-this-run', line)
            self.assertNotIn(' fingerprint=', line)

    def test_echo_requires_a_run_to_bind_to(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')

            line = receipt_echo(root, 'verification')

            self.assertIn('status=unavailable', line)
            self.assertIn('reason=freshness-unbound', line)

    def test_echo_refuses_a_receipt_invalidated_in_place(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            started = now_utc()
            write_receipt(root, 'verification', 'pass')
            invalidate_receipts(root, route['route_id'], 'repository tree changed after tool use')

            line = receipt_echo(root, 'verification', not_before=started)

            self.assertIn('status=unavailable', line)
            self.assertIn('reason=receipt-invalidated', line)
            self.assertNotIn(' fingerprint=', line)
            self.assertNotIn('dead', line)

    def test_echo_validates_the_envelope_before_emitting_an_identifier(self) -> None:
        fingerprints = [REAL_ID, 'f' * 64]
        shapes = {
            'only-a-fingerprint': {'tree_fingerprint': REAL_ID},
            'foreign-kind': {
                'schema_version': 1, 'route_id': 'r1', 'kind': 'code_review', 'status': 'pass',
                'created_at': '2026-09-20T01:02:03+00:00', 'tree_fingerprint': REAL_ID,
            },
            'foreign-route': {
                'schema_version': 1, 'route_id': 'OTHER', 'kind': 'verification', 'status': 'pass',
                'created_at': '2026-09-20T01:02:03+00:00', 'tree_fingerprint': REAL_ID,
            },
            'wrong-schema': {
                'schema_version': 99, 'route_id': 'r1', 'kind': 'verification', 'status': 'pass',
                'created_at': '2026-09-20T01:02:03+00:00', 'tree_fingerprint': REAL_ID,
            },
            'empty-object': {},
        }
        for name, payload in shapes.items():
            with self.subTest(name=name):
                with project_copy(git=True) as root:
                    set_active_route(root, {'route_id': 'r1', 'required_evidence': ['verification']})
                    receipts = root / '.grok-stack/runtime/receipts/r1'
                    receipts.mkdir(parents=True, exist_ok=True)
                    (receipts / 'verification.json').write_text(json.dumps(payload), encoding='utf-8')

                    line = receipt_echo(root, 'verification', not_before='2020-01-01T00:00:00+00:00')

                    self.assertIn('status=unavailable', line)
                    self.assertTrue(
                        all(fingerprint not in line for fingerprint in fingerprints),
                        f'{name} leaked an identifier: {line}',
                    )
                    self.assertIn('path=.grok-stack/runtime/receipts/', line)

    def test_echo_line_grammar_stays_one_shell_safe_token_per_field(self) -> None:
        with project_copy(git=True) as root:
            set_active_route(root, {'route_id': 'r1', 'required_evidence': ['verification']})
            receipts = root / '.grok-stack/runtime/receipts/r1'
            receipts.mkdir(parents=True)
            (receipts / 'verification.json').write_text('{"a": }', encoding='utf-8')

            line = receipt_echo(root, 'verification', not_before=now_utc())

            reason = line.split(' reason=')[1].split(' ')[0]
            self.assertRegex(reason, r'^[a-z0-9._-]+$')
            self.assertIn(' detail="', line)
            self.assertTrue(LINE_KEY.match(line), line)

    def test_echo_does_not_reject_a_hostile_route_and_writes_nothing(self) -> None:
        with project_copy(git=True) as root:
            set_active_route(root, {'route_id': 'oops/../../escape', 'required_evidence': []})
            before = sorted(path.name for path in root.iterdir())

            line = receipt_echo(root, 'verification', not_before=now_utc())

            self.assertIn('reason=no-active-route', line)
            self.assertEqual(sorted(path.name for path in root.iterdir()), before)
            self.assertNotIn('escape', [path.name for path in root.iterdir()])

    def test_a_cited_echo_fingerprint_resolves_against_the_checker(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            started = now_utc()
            write_receipt(root, 'verification', 'pass')
            line = receipt_echo(root, 'verification', not_before=started)
            fingerprint = line.split('fingerprint=')[1].split(' ')[0]

            pasted = audit_documents(root, [('report.md', f'receipt {fingerprint} bound the tree\n')])
            invented = audit_documents(root, [('report.md', f'receipt {fingerprint[:12]}dead bound the tree\n')])

            self.assertEqual(pasted['status'], 'pass')
            self.assertEqual(invented['status'], 'fail')
            self.assertEqual(invented['unresolved'][0]['token'], fingerprint[:12] + 'dead')


def echoed_line(stdout: str) -> str:
    """The single RECEIPT line a CLI printed, or the whole output to fail with."""
    return next((item for item in stdout.splitlines() if item.startswith('RECEIPT ')), stdout)


def echoed_fingerprint(line: str) -> str:
    """The one field a report is allowed to copy, read back out of the echo line."""
    return line.split(' fingerprint=')[1].split(' ')[0]


class EchoCliWiringTests(unittest.TestCase):
    """The freshness bound is supplied by the CLIs, so only a CLI run proves the wiring.

    A unit test of ``receipt_echo`` cannot catch a caller that forgets ``not_before``: the echo
    then refuses every legitimate receipt, and the report loses its pasteable identifier while
    every module-level test stays green.
    """

    def _run(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(root / 'scripts' / args[0]), *args[1:]],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPYCACHEPREFIX': '/tmp/pycache-cli'},
        )

    def _prepared(self, root: Path) -> str:
        from shutil import copytree, ignore_patterns

        copytree(ROOT / 'scripts', root / 'scripts', ignore=ignore_patterns('__pycache__'), dirs_exist_ok=True)
        route = build_route(root, 'Wire the echo to its run', 'wiring').to_dict()
        set_active_route(root, route)
        return str(route['route_id'])

    def test_grok_review_echoes_a_pasteable_line_for_its_own_receipt(self) -> None:
        with project_copy(git=True) as root:
            self._prepared(root)
            report = root / 'review-report.md'
            report.write_text('independent review\n', encoding='utf-8')

            proc = self._run(root, 'grok_review.py', 'code_review', '--status', 'pass',
                             '--report', 'review-report.md')

            line = echoed_line(proc.stdout)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('kind=code_review status=pass ', line)
            self.assertNotIn('reason=freshness-unbound', line)
            self.assertRegex(echoed_fingerprint(line), r'^[0-9a-f]{64}$')

    def test_grok_verify_echoes_a_pasteable_line_for_its_own_receipt(self) -> None:
        with project_copy(git=True) as root:
            route_id = self._prepared(root)

            proc = self._run(root, 'grok_verify.py', '--mode', 'fast')

            line = echoed_line(proc.stdout)
            self.assertIn('kind=verification status=', line, proc.stdout[-400:])
            self.assertNotIn('status=unavailable', line)
            self.assertIn('fingerprint=', line)
            # Whatever the run concluded, the echo must agree with the receipt it claims to show.
            stored_path = root / '.grok-stack/runtime/receipts' / route_id / 'verification.json'
            self.assertTrue(stored_path.is_file(), 'the run recorded nothing yet the echo was pasteable')
            stored = json.loads(stored_path.read_text(encoding='utf-8'))
            self.assertIn(f'status={stored["status"]} ', line)
            self.assertIn(f'fingerprint={stored["tree_fingerprint"]} ', line)


class CitationsCliTests(unittest.TestCase):
    def _cli(self, root: Path, *args: str, stdin: str = '') -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(root / 'scripts' / 'grok_citations.py'), *args],
            cwd=root,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def _installed(self, root: Path) -> None:
        from shutil import copy2, copytree, ignore_patterns

        target = root / 'scripts'
        target.mkdir(parents=True, exist_ok=True)
        copy2(ROOT / 'scripts' / 'grok_citations.py', target / 'grok_citations.py')
        package = root / '.grok-stack/adaptive_grok'
        if not package.is_dir():
            copytree(ROOT / '.grok-stack/adaptive_grok', package, ignore=ignore_patterns('__pycache__', '*.pyc'))
        else:
            for module in ('citations.py', 'receipts.py'):
                copy2(ROOT / '.grok-stack/adaptive_grok' / module, package / module)

    def _with_corpus(self, root: Path) -> Path:
        (root / '.grok-stack/runtime/receipts/r1').mkdir(parents=True, exist_ok=True)
        (root / '.grok-stack/runtime/receipts/r1/verification.json').write_text(
            json.dumps({'tree_fingerprint': REAL_ID}), encoding='utf-8'
        )
        return root

    def test_cli_exits_nonzero_and_names_the_missing_token(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            self._with_corpus(root)
            report = root / 'report.md'
            report.write_text(f'real {REAL_ID}\nfake {FABRICATED_TAIL}\n', encoding='utf-8')

            proc = self._cli(root, str(report))

            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn(f'MISSING {FABRICATED_TAIL} cited at report.md:2', proc.stdout)
            self.assertIn('CITATION FAIL', proc.stdout)
            self.assertNotIn(f'MISSING {REAL_ID}', proc.stdout)

    def test_cli_distinguishes_two_documents_with_the_same_name(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            self._with_corpus(root)
            for directory in ('alpha', 'beta'):
                (root / directory).mkdir(exist_ok=True)
                (root / directory / 'report.md').write_text(f'fake {FABRICATED_WHOLE}\n', encoding='utf-8')

            proc = self._cli(root, 'alpha/report.md', 'beta/report.md')

            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn(f'MISSING {FABRICATED_WHOLE} cited at alpha/report.md:1', proc.stdout)
            self.assertIn(f'MISSING {FABRICATED_WHOLE} cited at beta/report.md:1', proc.stdout)
            self.assertIn('unresolved-citations=2 unresolved-tokens=1', proc.stdout)

    def test_a_document_that_was_never_read_is_an_error_not_a_pass(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            self._with_corpus(root)
            (root / 'afolder').mkdir(exist_ok=True)

            proc = self._cli(root, 'afolder', 'no-such-report.md')

            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn('CITATION ERROR', proc.stdout)
            self.assertIn('NOT READ no-such-report.md', proc.stdout)
            self.assertIn('NOT READ afolder', proc.stdout)
            self.assertNotIn('CITATION PASS', proc.stdout)

    def test_an_oversized_document_is_declined_and_the_stdin_ceiling_applies(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            self._with_corpus(root)
            big = root / 'big.md'
            big.write_text(f'{"x" * 5000} {REAL_ID}\n', encoding='utf-8')

            oversize = self._cli(root, '--max-bytes', '100', 'big.md')
            stdin = self._cli(root, '--max-bytes', '10', stdin=f'{"y" * 500} {REAL_ID}\n')
            warned = self._cli(root, '--warn-only', '--max-bytes', '100', 'big.md')

            self.assertEqual(oversize.returncode, 2, oversize.stderr)
            self.assertIn('NOT READ big.md', oversize.stdout)
            self.assertEqual(stdin.returncode, 2, stdin.stderr)
            self.assertIn('NOT READ <stdin>', stdin.stdout)
            self.assertEqual(warned.returncode, 0, warned.stderr)
            self.assertIn('CITATION ERROR', warned.stdout)

    def test_warn_only_and_clean_documents_exit_zero(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            self._with_corpus(root)
            report = root / 'report.md'
            report.write_text(f'fake {FABRICATED_TAIL}\n', encoding='utf-8')

            warned = self._cli(root, '--warn-only', str(report))
            clean = self._cli(root, '-', stdin=f'clean {REAL_ID}\n')
            noisy = self._cli(root, '-', stdin='no identifiers here 20260924\n')

            self.assertEqual(warned.returncode, 0, warned.stderr)
            self.assertIn('CITATION FAIL', warned.stdout)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertEqual(noisy.returncode, 0, noisy.stderr)
            self.assertIn('CITATION PASS', noisy.stdout)

    def test_the_summary_shows_what_the_checker_declined_to_judge(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            self._with_corpus(root)
            report = root / 'report.md'
            report.write_text(f'decimal 1234567890 sha512 {SHA512_SHAPE}\n', encoding='utf-8')

            proc = self._cli(root, str(report))

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('DECLINED 2 hex run(s)', proc.stdout)
            self.assertIn('declined=2', proc.stdout)


if __name__ == '__main__':
    unittest.main()
