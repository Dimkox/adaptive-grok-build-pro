from __future__ import annotations

import json
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
    extract_citations,
    is_identifier_like,
)
from adaptive_grok.receipts import receipt_echo, write_receipt
from adaptive_grok.router import build_route
from adaptive_grok.state import set_active_route
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
FABRICATED_TAIL = REAL_ID[:12] + '0000'
FABRICATED_WHOLE = _synthetic_hex(0xF00D, 16)
FOREIGN_CORPUS_ID = _synthetic_hex(0xC0FFEE, 16)


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

    def test_a_token_only_repeated_in_report_prose_stays_unresolved(self) -> None:
        evidence = self.root / 'engineering/changes/20260924-x/evidence'
        evidence.mkdir(parents=True)
        (evidence / 'verification.md').write_text(f'prior report cited {FABRICATED_WHOLE}\n', encoding='utf-8')

        result = audit_documents(self.root, [('brief.md', f'as recorded {FABRICATED_WHOLE}\n')])

        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['unresolved'][0]['token'], FABRICATED_WHOLE)

    def test_corpus_reads_only_machine_state_files(self) -> None:
        identifiers, files = corpus_identifiers(self.root)

        self.assertIn(REAL_ID, identifiers)
        self.assertEqual(files, 1)

    def test_symlinked_and_oversized_corpus_entries_are_skipped(self) -> None:
        outside = self.root.parent / 'outside-secret.json'
        outside.write_text(json.dumps({'leak': FOREIGN_CORPUS_ID}), encoding='utf-8')
        try:
            (self.root / '.grok-stack/runtime/leak.json').symlink_to(outside)
            result = audit_documents(self.root, [('report.md', f'cite {FOREIGN_CORPUS_ID}\n')])

            self.assertEqual(result['status'], 'fail')
            self.assertEqual(result['unresolved'][0]['token'], FOREIGN_CORPUS_ID)
        finally:
            outside.unlink(missing_ok=True)


class GitObjectResolutionTests(unittest.TestCase):
    def test_a_real_commit_prefix_resolves_even_though_no_receipt_repeats_it(self) -> None:
        with project_copy(git=True) as root:
            head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True)
            commit = head.stdout.strip()

            result = audit_documents(root, [('report.md', f'landed as {commit[:12]}\n')])

            self.assertEqual(result['status'], 'pass')
            self.assertEqual(result['unresolved'], [])

    def test_an_unknown_object_id_is_not_resolved_by_git(self) -> None:
        with project_copy(git=True) as root:
            result = audit_documents(root, [('report.md', 'landed as deadbeefcafe01234242\n')])

            self.assertEqual(result['status'], 'fail')


class ReceiptEchoTests(unittest.TestCase):
    def test_echo_is_one_line_carrying_the_bound_fingerprint(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')

            line = receipt_echo(root, 'verification')

            self.assertNotIn('\n', line)
            self.assertTrue(line.startswith('RECEIPT kind=verification status=pass '))
            self.assertIn('fingerprint=', line)
            self.assertIn('path=.grok-stack/runtime/receipts/', line)
            self.assertIn(f'route={route["route_id"]}', line)
            fingerprint = line.split('fingerprint=')[1].split(' ')[0]
            self.assertRegex(fingerprint, r'^[0-9a-f]{64}$')

    def test_echo_reports_unavailable_instead_of_printing_nothing(self) -> None:
        with project_copy(git=True) as root:
            line = receipt_echo(root, 'verification')

            self.assertTrue(line.startswith('RECEIPT kind=verification status=unavailable'))
            self.assertIn('reason=no-active-route', line)

    def test_echo_refuses_to_present_an_older_receipt_as_this_run(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')

            (root / 'README-echo-probe.md').write_text('drift\n', encoding='utf-8')
            line = receipt_echo(root, 'verification', expect_tree_fingerprint='e' * 64)

            self.assertIn('status=unavailable', line)
            self.assertIn('reason=tree-fingerprint-mismatch', line)

    def test_a_cited_echo_fingerprint_resolves_against_the_checker(self) -> None:
        with project_copy(git=True) as root:
            route = build_route(root, 'Fix cited identifiers', 's1').to_dict()
            set_active_route(root, route)
            write_receipt(root, 'verification', 'pass')
            line = receipt_echo(root, 'verification')
            fingerprint = line.split('fingerprint=')[1].split(' ')[0]

            pasted = audit_documents(root, [('report.md', f'receipt {fingerprint} bound the tree\n')])
            invented = audit_documents(root, [('report.md', f'receipt {fingerprint[:12]}dead bound the tree\n')])

            self.assertEqual(pasted['status'], 'pass')
            self.assertEqual(invented['status'], 'fail')
            self.assertEqual(invented['unresolved'][0]['token'], fingerprint[:12] + 'dead')


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
            copy2(ROOT / '.grok-stack/adaptive_grok/citations.py', package / 'citations.py')

    def test_cli_exits_nonzero_and_names_the_missing_token(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            (root / '.grok-stack/runtime/receipts/r1').mkdir(parents=True, exist_ok=True)
            (root / '.grok-stack/runtime/receipts/r1/verification.json').write_text(
                json.dumps({'tree_fingerprint': REAL_ID}), encoding='utf-8'
            )
            report = root / 'report.md'
            report.write_text(
                f'real {REAL_ID}\nfake {FABRICATED_TAIL}\n',
                encoding='utf-8',
            )

            proc = self._cli(root, str(report))

            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn(f'MISSING {FABRICATED_TAIL} cited at report.md:2', proc.stdout)
            self.assertIn('CITATION FAIL', proc.stdout)
            self.assertNotIn(f'MISSING {REAL_ID}', proc.stdout)

    def test_warn_only_and_clean_documents_exit_zero(self) -> None:
        with project_copy(git=True) as root:
            self._installed(root)
            (root / '.grok-stack/runtime/receipts/r1').mkdir(parents=True, exist_ok=True)
            (root / '.grok-stack/runtime/receipts/r1/verification.json').write_text(
                json.dumps({'tree_fingerprint': REAL_ID}), encoding='utf-8'
            )
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


if __name__ == '__main__':
    unittest.main()
