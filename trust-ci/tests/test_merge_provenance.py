from __future__ import annotations

import hashlib
import base64
import json
import unittest
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from _support import digest, sha
from adaptive_trust_ci.github import GitHubTransportError
from adaptive_trust_ci.github_app import GitHubAppClient, RetryableGitHubError
from adaptive_trust_ci.provenance import (
    ClaimedMergeFact,
    CorroboratedMerge,
    DeliveryConflict,
    MergeFactLedger,
    ProtectedBranchJobRequest,
    ProvenanceMismatch,
)
from adaptive_trust_ci.webhooks import parse_merged_pull_request
from adaptive_trust_ci.worker import MergeReconciler, ReconciliationIncomplete
from adaptive_trust_ci.worker import _cosign_verifier


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def merged_payload(*, merged=True, merge_sha=None, repository='Dimkox/adaptive-grok-build-pro', base_ref='main') -> bytes:
    return json.dumps(
        {
            'action': 'closed',
            'installation': {'id': 42},
            'repository': {'id': 101, 'full_name': repository},
            'pull_request': {
                'number': 12,
                'merged': merged,
                'merged_at': '2026-08-30T11:59:00Z' if merged else None,
                'merge_commit_sha': merge_sha or sha('c'),
                'head': {'sha': sha('b'), 'ref': 'feat/x'},
                'base': {'sha': sha('a'), 'ref': base_ref},
            },
        },
        separators=(',', ':'),
    ).encode()


class FakeTransport:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers, body=None):
        self.calls.append((method, url, headers, body))
        return self.responses.pop(0)


def api_pull(*, merge_sha=None, repository='Dimkox/adaptive-grok-build-pro', base_ref='main'):
    return {
        'number': 12,
        'merged': True,
        'merged_at': '2026-08-30T11:59:00Z',
        'merge_commit_sha': merge_sha or sha('c'),
        'head': {'sha': sha('b')},
        # The base SHA may advance after a merge and is intentionally not authority.
        'base': {'sha': sha('f'), 'ref': base_ref, 'repo': {'id': 101, 'full_name': repository}},
    }


def required_checks():
    return {
        'strict': True,
        'checks': [{'context': 'adaptive-trust-ci/verified@policy', 'app_id': 123}],
    }


def provenance_client(responses):
    return GitHubAppClient(
        token_provider=lambda: 'token',
        transport=FakeTransport(responses),
        api_url='https://example.test',
        now_fn=lambda: NOW,
        expected_protected_ref='refs/heads/main',
        required_check_name='adaptive-trust-ci/verified@policy',
        required_check_app_id=123,
    )


class MergeProvenanceTests(unittest.TestCase):
    def test_unmerged_closure_is_not_a_merge_fact(self) -> None:
        self.assertIsNone(parse_merged_pull_request(merged_payload(merged=False), 'delivery-1', now=NOW))

    def test_worker_processes_only_claimed_fact_through_corroboration_then_exact_runner(self) -> None:
        fact = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        assert fact is not None
        claimed = ClaimedMergeFact(fact=fact, claim_id=str(uuid.uuid4()), attempt=1)
        calls = []
        corroborated = CorroboratedMerge.from_fact(
            fact,
            required_check_name='adaptive-trust-ci/verified@policy',
            required_check_app_id=123,
            now=NOW,
        )

        class App:
            def corroborate_merge(self, value):
                calls.append(('corroborate', value))
                return corroborated

        class Runner:
            def run_protected_branch(self, request):
                calls.append(('run', request))
                return 'envelope'

        worker = type('Settings', (), {})()
        composed = __import__('adaptive_trust_ci.worker', fromlist=['Worker']).Worker(
            settings=worker,
            store=object(),
            runner=Runner(),
            stop_event=threading.Event(),
            merge_client=App(),
            protected_ref='refs/heads/main',
        )
        def request_for(value):
            return ProtectedBranchJobRequest(
                job_id=str(uuid.uuid4()), merge=value, policy_epoch=digest('a'),
                supply_chain_dir='/verified/supply-chain', artifact_path='/verified/supply-chain/artifact.zip',
                started_at=NOW,
            )

        result = composed.process_claimed_merge_fact(claimed, request_for)
        self.assertEqual(result, 'envelope')
        self.assertEqual([name for name, _ in calls], ['corroborate', 'run'])

        with self.assertRaises(TypeError):
            composed.process_claimed_merge_fact(fact, lambda value: value)

        other_fact = parse_merged_pull_request(merged_payload(merge_sha=sha('d')), 'delivery-2', now=NOW)
        assert other_fact is not None
        other = CorroboratedMerge.from_fact(
            other_fact, required_check_name='adaptive-trust-ci/verified@policy',
            required_check_app_id=123, now=NOW,
        )
        with self.assertRaisesRegex(RuntimeError, 'request does not match'):
            composed.process_claimed_merge_fact(claimed, lambda _value: request_for(other))

    def test_worker_claims_records_and_completes_durable_merge_fact(self) -> None:
        fact = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        assert fact is not None
        claimed = ClaimedMergeFact(fact=fact, claim_id=str(uuid.uuid4()), attempt=1)
        corroborated = CorroboratedMerge.from_fact(
            fact,
            required_check_name='adaptive-trust-ci/verified@policy',
            required_check_app_id=123,
            now=NOW,
        )
        calls = []

        class Store:
            def claim_merge_fact(self, worker_id, lease_seconds, *, now):
                calls.append(('claim', worker_id, lease_seconds, now))
                return claimed

            def record_protected_branch_evidence(self, evidence):
                calls.append(('record', evidence))
                return True

            def record_or_get_protected_branch_evidence(self, evidence):
                calls.append(('record-or-get', evidence))
                return evidence

            def complete_merge_fact(self, value, *, now):
                calls.append(('complete', value, now))

            def retry_merge_fact(self, value, error, *, now):
                calls.append(('retry', value, error, now))

        class App:
            def corroborate_merge(self, value):
                return corroborated

        class Runner:
            policy = SimpleNamespace(lease_seconds=90)

            def run_protected_branch(self, request):
                calls.append(('run', request))
                return 'signed-evidence'

            def publish_protected_success(self, evidence):
                calls.append(('publish', evidence))

        composed = __import__('adaptive_trust_ci.worker', fromlist=['Worker']).Worker(
            settings=SimpleNamespace(worker_id='worker-durable'),
            store=Store(),
            runner=Runner(),
            stop_event=threading.Event(),
            merge_client=App(),
            protected_ref='refs/heads/main',
        )

        def request_for(value):
            return ProtectedBranchJobRequest(
                job_id=str(uuid.uuid4()),
                merge=value,
                policy_epoch=digest('a'),
                supply_chain_dir='/verified/supply-chain',
                artifact_path='/verified/supply-chain/artifact.zip',
                started_at=NOW,
            )

        self.assertTrue(composed.process_next_merge_fact(request_for, now=NOW))
        self.assertEqual(
            [call[0] for call in calls], ['claim', 'run', 'record-or-get', 'publish', 'complete']
        )

    def test_worker_marks_provenance_mismatch_permanent_without_retry(self) -> None:
        fact = parse_merged_pull_request(merged_payload(), 'delivery-permanent', now=NOW)
        assert fact is not None
        claimed = ClaimedMergeFact(fact=fact, claim_id=str(uuid.uuid4()), attempt=1)
        calls = []

        class Store:
            def claim_merge_fact(self, *_args, **_kwargs):
                return claimed

            def fail_merge_fact(self, value, error, *, now):
                calls.append(('fail', value, error, now))

            def retry_merge_fact(self, *_args, **_kwargs):
                calls.append(('retry',))

        class App:
            def corroborate_merge(self, _value):
                raise ProvenanceMismatch('exact identity mismatch')

        composed = __import__('adaptive_trust_ci.worker', fromlist=['Worker']).Worker(
            settings=SimpleNamespace(worker_id='worker-durable'), store=Store(),
            runner=SimpleNamespace(policy=SimpleNamespace(lease_seconds=90)),
            stop_event=threading.Event(), merge_client=App(), protected_ref='refs/heads/main',
        )
        with self.assertRaises(ProvenanceMismatch):
            composed.process_next_merge_fact(lambda value: value, now=NOW)
        self.assertEqual([call[0] for call in calls], ['fail'])

    def test_worker_build_uses_provenance_capable_github_app_client(self) -> None:
        source = (Path(__file__).resolve().parents[1] / 'src/adaptive_trust_ci/worker.py').read_text(encoding='utf-8')
        self.assertIn('GitHubAppClient(', source)
        self.assertIn('process_claimed_merge_fact(', source)

    def test_worker_run_waits_after_transient_merge_failure_instead_of_hot_looping(self) -> None:
        waits = []

        class Stop:
            stopped = False

            def is_set(self):
                return self.stopped

            def wait(self, seconds):
                waits.append(seconds)
                self.stopped = True

        class Store:
            def ping(self):
                pass

            def claim(self, *_args, **_kwargs):
                return None

        worker = __import__('adaptive_trust_ci.worker', fromlist=['Worker']).Worker(
            settings=SimpleNamespace(
                worker_id='worker-durable', poll_interval_seconds=7,
                reconciliation_interval_seconds=60,
                common=SimpleNamespace(stopped=False),
            ),
            store=Store(), runner=SimpleNamespace(policy=SimpleNamespace(lease_seconds=90)),
            stop_event=Stop(),
        )
        attempts = []

        def fail_once(*_args, **_kwargs):
            attempts.append('failed')
            raise RuntimeError('temporary outage')

        worker.process_next_merge_fact = fail_once
        worker.reconcile_merges = lambda: 0
        self.assertEqual(worker.run(), 0)
        self.assertEqual(attempts, ['failed'])
        self.assertEqual(waits, [7])

    def test_runtime_supply_chain_verifier_uses_mounted_public_key_without_cosign_binary(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / 'supply-chain.manifest.json'
            manifest.write_bytes(b'{"schema_version":1}\n')
            private = ec.generate_private_key(ec.SECP256R1())
            public_path = root / 'cosign.pub'
            public_path.write_bytes(private.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ))
            signature = private.sign(manifest.read_bytes(), ec.ECDSA(hashes.SHA256()))
            (root / 'supply-chain.manifest.json.sig').write_bytes(
                base64.b64encode(signature) + b'\n'
            )
            verify = _cosign_verifier(public_path)
            self.assertTrue(verify(root))
            manifest.write_bytes(b'{"schema_version":2}\n')
            self.assertFalse(verify(root))

    def test_merge_squash_and_rebase_result_shas_are_preserved_exactly(self) -> None:
        for character in ('c', 'd', 'e'):
            with self.subTest(strategy=character):
                raw = merged_payload(merge_sha=sha(character))
                fact = parse_merged_pull_request(raw, f'delivery-{character}', now=NOW)
                assert fact is not None
                self.assertEqual(fact.merged_commit_sha, sha(character))
                self.assertEqual(fact.payload_sha256, hashlib.sha256(raw).hexdigest())
                self.assertEqual(fact.protected_ref, 'refs/heads/main')

    def test_delivery_guid_duplicate_is_idempotent_but_conflict_is_rejected(self) -> None:
        first = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        duplicate = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        conflict = parse_merged_pull_request(merged_payload(merge_sha=sha('d')), 'delivery-1', now=NOW)
        assert first is not None and duplicate is not None and conflict is not None
        ledger = MergeFactLedger()
        self.assertTrue(ledger.record(first))
        self.assertFalse(ledger.record(duplicate))
        with self.assertRaises(DeliveryConflict):
            ledger.record(conflict)

    def test_github_app_corroborates_pull_and_exact_commit_without_branch_tip_lookup(self) -> None:
        fact = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        assert fact is not None
        transport = FakeTransport([(200, api_pull()), (200, required_checks()), (200, {'sha': sha('c')})])
        client = GitHubAppClient(
            token_provider=lambda: 'token', transport=transport, api_url='https://example.test', now_fn=lambda: NOW,
            expected_protected_ref='refs/heads/main', required_check_name='adaptive-trust-ci/verified@policy',
            required_check_app_id=123,
        )
        corroborated = client.corroborate_merge(fact)
        self.assertEqual(corroborated.merged_commit_sha, sha('c'))
        self.assertEqual(corroborated.base_sha, sha('a'))
        self.assertEqual(len(transport.calls), 3)
        self.assertTrue(any('/branches/main/protection/required_status_checks' in call[1] for call in transport.calls))
        self.assertFalse(any('/git/ref/' in call[1] for call in transport.calls))
        self.assertEqual(corroborated.required_check_app_id, 123)

    def test_repository_ref_or_merge_sha_mismatch_is_denied(self) -> None:
        fact = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        assert fact is not None
        for pull in (
            api_pull(repository='other/repository'),
            api_pull(base_ref='release'),
            api_pull(merge_sha=sha('d')),
        ):
            with self.subTest(pull=pull):
                client = provenance_client([(200, pull)])
                with self.assertRaises(ProvenanceMismatch):
                    client.corroborate_merge(fact)

    def test_exact_commit_404_is_a_provenance_denial(self) -> None:
        fact = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        assert fact is not None
        client = provenance_client(
            [(200, api_pull()), (200, required_checks()), (404, {'message': 'not found'})]
        )
        with self.assertRaisesRegex(ProvenanceMismatch, 'exact commit'):
            client.corroborate_merge(fact)

    def test_corroboration_denies_unconfigured_or_wrong_app_branch_protection(self) -> None:
        fact = parse_merged_pull_request(merged_payload(), 'delivery-1', now=NOW)
        assert fact is not None
        unconfigured = GitHubAppClient(
            token_provider=lambda: 'token', transport=FakeTransport([]), api_url='https://example.test'
        )
        with self.assertRaisesRegex(ProvenanceMismatch, 'protection'):
            unconfigured.corroborate_merge(fact)

        wrong_app = required_checks()
        wrong_app['checks'][0]['app_id'] = 999
        client = provenance_client([(200, api_pull()), (200, wrong_app)])
        with self.assertRaisesRegex(ProvenanceMismatch, 'protection'):
            client.corroborate_merge(fact)

    def test_lost_webhook_is_repaired_from_bounded_watermarked_pages(self) -> None:
        pull = api_pull()
        pull['updated_at'] = '2026-08-30T11:59:30Z'

        class FakeApp:
            def __init__(self):
                self.pages = []

            def list_closed_pulls(self, repository, *, updated_after, page, per_page):
                self.pages.append((updated_after, page, per_page))
                return [pull] if page == 1 else []

            def corroborate_merge(self, fact):
                return type('Result', (), {'merge_fact_id': fact.merge_fact_id})()

        saved = []
        recorded = []
        app = FakeApp()
        reconciler = MergeReconciler(
            github=app,
            load_watermark=lambda _repository: ('2026-08-30T11:00:00Z', 0),
            save_watermark=lambda repository, watermark: saved.append((repository, watermark)),
            record_fact=lambda fact, corroborated: recorded.append((fact, corroborated)),
            now_fn=lambda: NOW,
        )
        repaired = reconciler.run(
            repository='dimkox/adaptive-grok-build-pro',
            repository_id=101,
            installation_id=42,
            protected_ref='refs/heads/main',
            max_pages=2,
            per_page=1,
        )
        self.assertEqual(repaired, 1)
        self.assertEqual(len(recorded), 1)
        self.assertEqual([page[1] for page in app.pages], [1, 2])
        self.assertEqual({page[0] for page in app.pages}, {'2026-08-30T11:00:00Z'})
        self.assertEqual(saved[-1][1], ('2026-08-30T11:59:30Z', 12))

    def test_reconciliation_page_limit_is_a_hard_request_cap(self) -> None:
        class EndlessApp:
            def __init__(self):
                self.calls = 0

            def list_closed_pulls(self, repository, *, updated_after, page, per_page):
                self.calls += 1
                value = api_pull(merge_sha=sha('c' if page == 1 else 'd'))
                value['number'] = 10 + page
                value['updated_at'] = f'2026-08-30T11:59:0{page}Z'
                return [value]

            def corroborate_merge(self, fact):
                return fact

        app = EndlessApp()
        saved = []
        recorded = []
        reconciler = MergeReconciler(
            github=app,
            load_watermark=lambda _repository: ('2026-08-30T11:00:00Z', 0),
            save_watermark=lambda *args: saved.append(args),
            record_fact=lambda *args: recorded.append(args),
            now_fn=lambda: NOW,
        )
        with self.assertRaises(ReconciliationIncomplete):
            reconciler.run(
                repository='dimkox/adaptive-grok-build-pro', repository_id=101,
                installation_id=42, protected_ref='refs/heads/main', max_pages=2, per_page=1,
            )
        self.assertEqual(app.calls, 2)
        self.assertEqual(saved, [])
        self.assertEqual(recorded, [])

    def test_reconciliation_globally_sorts_same_second_results_before_advancing(self) -> None:
        timestamp = '2026-08-30T11:59:30Z'
        high = api_pull(merge_sha=sha('d'))
        high.update({'number': 20, 'updated_at': timestamp})
        low = api_pull(merge_sha=sha('c'))
        low.update({'number': 10, 'updated_at': timestamp})

        class ReversedApp:
            def list_closed_pulls(self, repository, *, updated_after, page, per_page):
                return [high, low] if page == 1 else []

            def corroborate_merge(self, fact):
                return fact

        recorded = []
        saved = []
        reconciler = MergeReconciler(
            github=ReversedApp(),
            load_watermark=lambda _repository: ('2026-08-30T11:00:00Z', 0),
            save_watermark=lambda _repository, watermark: saved.append(watermark),
            record_fact=lambda fact, _corroborated: recorded.append(fact.pr_number),
            now_fn=lambda: NOW,
        )
        repaired = reconciler.run(
            repository='dimkox/adaptive-grok-build-pro', repository_id=101,
            installation_id=42, protected_ref='refs/heads/main', max_pages=2, per_page=2,
        )
        self.assertEqual(repaired, 2)
        self.assertEqual(recorded, [10, 20])
        self.assertEqual(saved, [(timestamp, 10), (timestamp, 20)])

    def test_reconciliation_retries_transient_failures_with_a_hard_attempt_cap(self) -> None:
        class FailingApp:
            def __init__(self):
                self.calls = 0

            def list_closed_pulls(self, *args, **kwargs):
                self.calls += 1
                raise RetryableGitHubError('rate limited', retry_after_seconds=7)

        app = FailingApp()
        sleeps = []
        reconciler = MergeReconciler(
            github=app,
            load_watermark=lambda _repository: ('2026-08-30T11:00:00Z', 0),
            save_watermark=lambda *_args: None,
            record_fact=lambda *_args: None,
            now_fn=lambda: NOW,
            sleep_fn=sleeps.append,
            jitter_fn=lambda: 0.0,
            max_attempts=3,
        )
        with self.assertRaises(RetryableGitHubError):
            reconciler.run(
                repository='dimkox/adaptive-grok-build-pro', repository_id=101,
                installation_id=42, protected_ref='refs/heads/main', max_pages=2, per_page=1,
            )
        self.assertEqual(app.calls, 3)
        self.assertEqual(sleeps, [7, 7])

    def test_github_reconciliation_uses_server_side_watermark_on_mature_repository(self) -> None:
        pull = api_pull()
        pull['updated_at'] = '2026-08-30T11:59:30Z'
        transport = FakeTransport(
            [
                (200, {'items': [{'number': 12, 'updated_at': pull['updated_at']}]}),
                (200, pull),
            ]
        )
        client = GitHubAppClient(token_provider=lambda: 'token', transport=transport, api_url='https://example.test')
        values = client.list_closed_pulls(
            'dimkox/adaptive-grok-build-pro',
            updated_after='2026-08-30T11:00:00Z',
            page=1,
            per_page=10,
        )
        self.assertEqual(values, [pull])
        self.assertIn('/search/issues?', transport.calls[0][1])
        self.assertIn('updated%3A%3E%3D2026-08-30T11%3A00%3A00Z', transport.calls[0][1])

    def test_incomplete_github_search_fails_before_watermark_can_advance(self) -> None:
        transport = FakeTransport(
            [(200, {'incomplete_results': True, 'items': [{'number': 12}]})]
        )
        client = GitHubAppClient(
            token_provider=lambda: 'token', transport=transport,
            api_url='https://example.test',
        )
        saved = []
        reconciler = MergeReconciler(
            github=client,
            load_watermark=lambda _repository: ('2026-08-30T11:00:00Z', 0),
            save_watermark=lambda *args: saved.append(args),
            record_fact=lambda *_args: None,
        )
        with self.assertRaises(ReconciliationIncomplete):
            reconciler.run(
                repository='dimkox/adaptive-grok-build-pro', repository_id=101,
                installation_id=42, protected_ref='refs/heads/main',
            )
        self.assertEqual(saved, [])

    def test_github_retry_error_uses_actual_retry_after_header_and_network_failures(self) -> None:
        client = GitHubAppClient(
            token_provider=lambda: 'token',
            transport=FakeTransport([(429, {}, {'Retry-After': '9'})]),
            api_url='https://example.test',
        )
        with self.assertRaises(RetryableGitHubError) as caught:
            client.list_closed_pulls('dimkox/repo', updated_after='2026-08-30T11:00:00Z', page=1, per_page=1)
        self.assertEqual(caught.exception.retry_after_seconds, 9)

        class NetworkTransport:
            def request(self, *args, **kwargs):
                raise GitHubTransportError('temporary network failure')

        network_client = GitHubAppClient(token_provider=lambda: 'token', transport=NetworkTransport())
        with self.assertRaises(RetryableGitHubError):
            network_client.list_closed_pulls('dimkox/repo', updated_after='2026-08-30T11:00:00Z', page=1, per_page=1)


if __name__ == '__main__':
    unittest.main()
