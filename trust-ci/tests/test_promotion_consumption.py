from __future__ import annotations

import base64
import ast
import hashlib
import json
import tempfile
import threading
import unittest
import uuid
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from _support import digest, now, policy_data, sha
from adaptive_trust_ci.models import PromotionPayload, ProtectedBranchAttestationPayload
from adaptive_trust_ci.policy import Policy
from adaptive_trust_ci.promotion_consumer import (
    PromotionAlreadyConsumed,
    PromotionConsumer,
    PromotionDenied,
    PromotionTarget,
    PromotionUnavailable,
    authorize_exact_artifact,
)
from adaptive_trust_ci.provenance import MergedPullRequestFact
from adaptive_trust_ci.signing import Signer, sign_promotion, sign_protected_branch_attestation
from adaptive_trust_ci.store import MemoryStore


class FailingConsumeStore(MemoryStore):
    def consume_promotion(self, *args, **kwargs):
        raise ConnectionError('database unavailable')


class PromotionConsumptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.bundle = Path(self.temp.name)
        self.artifact = self.bundle / 'artifact.zip'
        self.artifact.write_bytes(b'exact production artifact')
        self.artifact_digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.policy_source = policy_data()
        self.policy = Policy.from_dict(self.policy_source)
        policy_path = self.bundle / 'policy.json'
        policy_path.write_text(json.dumps(self.policy_source, sort_keys=True), encoding='utf-8')
        artifacts_path = self.bundle / 'artifacts.sha256'
        artifacts_path.write_text(
            f'{self.artifact_digest}  {self.artifact.name}\n', encoding='utf-8'
        )
        self.manifest = self.bundle / 'supply-chain.manifest.json'
        self.manifest.write_text(
            json.dumps(
                {
                    'schema_version': 1,
                    'created_at': '2026-08-30T00:00:00+00:00',
                    'git_head': sha('a'),
                    'policy_file': policy_path.name,
                    'policy_sha256': hashlib.sha256(policy_path.read_bytes()).hexdigest(),
                    'artifacts_file': artifacts_path.name,
                    'artifacts_sha256': hashlib.sha256(artifacts_path.read_bytes()).hexdigest(),
                    'images': {
                        'api': 'registry.example/api@sha256:' + digest('1'),
                        'worker': 'registry.example/worker@sha256:' + digest('2'),
                        'runner': self.policy.sandbox.image,
                    },
                    'sbom_directory': 'sbom',
                    'scan_directory': 'scan',
                },
                sort_keys=True,
                separators=(',', ':'),
            )
            + '\n',
            encoding='utf-8',
        )
        self.manifest_sha256 = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.store = MemoryStore()
        self.target, self.promotion_id = self._seed(self.store)
        self.consumer = PromotionConsumer(
            self.store,
            manifest_path=self.manifest,
            artifact_path=self.artifact,
            expected_manifest_sha256=self.manifest_sha256,
            stopped=lambda: False,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _seed(self, store: MemoryStore) -> tuple[PromotionTarget, str]:
        signer = Signer.generate()
        fact = MergedPullRequestFact.create(
            delivery_id='delivery-consume-1',
            payload_sha256=digest('d'),
            repository_id=123,
            repository='dimkox/adaptive-grok-build-pro',
            installation_id=456,
            pr_number=701,
            head_sha=sha('e'),
            base_sha=sha('f'),
            protected_ref='refs/heads/main',
            merged_commit_sha=sha('a'),
            merged_at='2026-08-23T11:59:00Z',
            received_at=now(),
        )
        attestation = ProtectedBranchAttestationPayload(
            schema_version=1,
            source_attestation_id=str(uuid.uuid4()),
            merge_fact_id=fact.merge_fact_id,
            repository=fact.repository,
            protected_ref=fact.protected_ref,
            merged_commit_sha=fact.merged_commit_sha,
            policy_epoch=self.policy.digest,
            runner_digest=digest('1'),
            holdout_digest=digest('2'),
            image_digest=digest('3'),
            artifact_sha256=self.artifact_digest,
            result='passed',
            issued_at='2026-08-23T12:00:00Z',
            key_id=signer.key_id,
        )
        promotion = PromotionPayload(
            schema_version=1,
            promotion_id=str(uuid.uuid4()),
            nonce=base64.urlsafe_b64encode(b'n' * 32).decode().rstrip('='),
            actor='dmitry',
            key_id=signer.key_id,
            repository=fact.repository,
            merged_commit_sha=fact.merged_commit_sha,
            artifact_sha256=self.artifact_digest,
            target_environment='production',
            policy_epoch=self.policy.digest,
            source_attestation_id=attestation.source_attestation_id,
            reason='Deploy exact artifact',
            issued_at=(now() - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            expires_at=(now() + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        )
        target = PromotionTarget(
            repository=promotion.repository,
            merged_commit_sha=promotion.merged_commit_sha,
            artifact_sha256=promotion.artifact_sha256,
            target_environment=promotion.target_environment,
            policy_epoch=promotion.policy_epoch,
            source_attestation_id=promotion.source_attestation_id,
        )
        store.activate_policy(self.policy.digest)
        store.record_merge_fact(fact)
        store.record_protected_branch_evidence(
            sign_protected_branch_attestation(attestation, signer)
        )
        store.accept_promotion(
            sign_promotion(promotion, signer),
            'request-consume-0001',
            'correlation-consume',
            now(),
        )
        return target, promotion.promotion_id

    def test_two_consumers_have_one_winner_and_denial_has_no_external_effect(self) -> None:
        barrier = threading.Barrier(3)
        operation_id = str(uuid.uuid4())
        results: list[object] = []
        def consume() -> None:
            barrier.wait(timeout=5)
            try:
                results.append(
                    self.consumer.consume(self.promotion_id, self.target, operation_id, now())
                )
            except BaseException as exc:
                results.append(exc)

        threads = [threading.Thread(target=consume) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)

        self.assertEqual(sum(not isinstance(item, BaseException) for item in results), 1)
        with self.assertRaises(PromotionDenied):
            self.consumer.consume(
                self.promotion_id,
                replace(self.target, artifact_sha256=digest('f')),
                str(uuid.uuid4()),
                now(),
            )
        self.assertEqual(len(self.store._promotion_consumptions), 1)

    def test_deployer_can_append_exactly_one_constrained_terminal_event(self) -> None:
        operation_id = str(uuid.uuid4())
        self.consumer.consume(self.promotion_id, self.target, operation_id, now())
        terminal = self.store.record_deployment_terminal(
            self.promotion_id, operation_id, 'deployment.completed',
            reason_code='completed', details={'deployment_id': 'local-drill-1'},
            now=now(),
        )
        self.assertEqual(terminal.event_type, 'deployment.completed')
        with self.assertRaises(RuntimeError):
            self.store.record_deployment_terminal(
                self.promotion_id, operation_id, 'deployment.failed',
                reason_code='failed', details={}, now=now(),
            )
        with self.assertRaises(ValueError):
            self.store.record_deployment_terminal(
                self.promotion_id, operation_id, 'promotion.accepted',
                reason_code='accepted', details={}, now=now(),
            )
        self.assertEqual(
            [event.event_type for event in self.store.list_promotion_events(
                self.promotion_id, limit=10
            )],
            ['promotion.accepted', 'promotion.consumed', 'deployment.completed'],
        )

    def test_exact_artifact_authorization_rejects_manifest_and_byte_substitution(self) -> None:
        self.assertEqual(
            authorize_exact_artifact(
                self.manifest, self.artifact, self.target, self.manifest_sha256
            ),
            self.target,
        )
        self.artifact.write_bytes(b'substituted after human signing')
        with self.assertRaises(PromotionDenied):
            authorize_exact_artifact(
                self.manifest, self.artifact, self.target, self.manifest_sha256
            )

    def test_manifest_bytes_are_immutably_bound_and_structure_is_exact(self) -> None:
        original = json.loads(self.manifest.read_text(encoding='utf-8'))
        for mutation in (
            {**original, 'unknown': True},
            {**original, 'policy_sha256': digest('f')},
            {**original, 'artifacts_sha256': digest('e')},
        ):
            self.manifest.write_text(
                json.dumps(mutation, sort_keys=True, separators=(',', ':')) + '\n',
                encoding='utf-8',
            )
            with self.assertRaises(PromotionDenied):
                self.consumer.consume(
                    self.promotion_id, self.target, str(uuid.uuid4()), now()
                )
            self.assertEqual(len(self.store._promotion_consumptions), 0)
            self.assertEqual(
                [event.event_type for event in self.store.list_promotion_events(self.promotion_id, limit=10)],
                ['promotion.accepted'],
            )
        unknown = json.dumps(
            {**original, 'unknown': True}, sort_keys=True, separators=(',', ':')
        ).encode() + b'\n'
        self.manifest.write_bytes(unknown)
        with self.assertRaises(PromotionDenied):
            authorize_exact_artifact(
                self.manifest,
                self.artifact,
                self.target,
                hashlib.sha256(unknown).hexdigest(),
            )
        canonical = json.dumps(
            original, sort_keys=True, separators=(',', ':')
        ) + '\n'
        duplicate = canonical.rstrip()[:-1] + ',"git_head":"' + sha('a') + '"}\n'
        self.manifest.write_text(duplicate, encoding='utf-8')
        with self.assertRaises(PromotionDenied):
            authorize_exact_artifact(
                self.manifest,
                self.artifact,
                self.target,
                hashlib.sha256(duplicate.encode()).hexdigest(),
            )
        self.assertEqual(len(self.store._promotion_consumptions), 0)

    def test_post_start_policy_and_index_substitution_leave_zero_authority(self) -> None:
        policy_path = self.bundle / 'policy.json'
        index_path = self.bundle / 'artifacts.sha256'
        for path, replacement in (
            (policy_path, b'{}\n'),
            (index_path, f'{digest("f")}  artifact.zip\n'.encode()),
        ):
            original = path.read_bytes()
            path.write_bytes(replacement)
            with self.assertRaises(PromotionDenied):
                self.consumer.consume(
                    self.promotion_id, self.target, str(uuid.uuid4()), now()
                )
            path.write_bytes(original)
            self.assertEqual(len(self.store._promotion_consumptions), 0)
            self.assertEqual(
                [event.event_type for event in self.store.list_promotion_events(
                    self.promotion_id, limit=10
                )],
                ['promotion.accepted'],
            )

    def test_expiry_future_and_stale_active_policy_deny_before_consumption(self) -> None:
        with self.assertRaises(PromotionDenied):
            self.consumer.consume(
                self.promotion_id, self.target, str(uuid.uuid4()), now() + timedelta(hours=1)
            )
        with self.assertRaises(PromotionDenied):
            self.consumer.consume(
                self.promotion_id, self.target, str(uuid.uuid4()), now() - timedelta(hours=1)
            )
        self.store.activate_policy(digest('f'))
        with self.assertRaises(PromotionDenied):
            self.consumer.consume(self.promotion_id, self.target, str(uuid.uuid4()), now())
        self.assertEqual(
            [event.event_type for event in self.store.list_promotion_events(self.promotion_id, limit=10)],
            ['promotion.accepted'],
        )

    def test_database_loss_and_kill_switch_fail_closed(self) -> None:
        failed_store = FailingConsumeStore()
        failed_consumer = PromotionConsumer(
            failed_store,
            manifest_path=self.manifest,
            artifact_path=self.artifact,
            expected_manifest_sha256=self.manifest_sha256,
            stopped=lambda: False,
        )
        with self.assertRaises(PromotionUnavailable):
            failed_consumer.consume(self.promotion_id, self.target, str(uuid.uuid4()), now())
        stopped_consumer = PromotionConsumer(
            self.store,
            manifest_path=self.manifest,
            artifact_path=self.artifact,
            expected_manifest_sha256=self.manifest_sha256,
            stopped=lambda: True,
        )
        with self.assertRaises(PromotionUnavailable):
            stopped_consumer.consume(self.promotion_id, self.target, str(uuid.uuid4()), now())

    def test_crash_after_consume_never_unconsumes_and_retry_exposes_operation(self) -> None:
        operation_id = str(uuid.uuid4())
        consumed = self.consumer.consume(self.promotion_id, self.target, operation_id, now())
        self.assertEqual(consumed.operation_id, operation_id)
        with self.assertRaises(PromotionAlreadyConsumed) as caught:
            self.consumer.consume(self.promotion_id, self.target, operation_id, now())
        self.assertEqual(caught.exception.operation_id, operation_id)
        with self.assertRaises(PromotionAlreadyConsumed) as conflicting:
            self.consumer.consume(
                self.promotion_id, self.target, str(uuid.uuid4()), now()
            )
        self.assertIsNone(conflicting.exception.operation_id)
        self.assertEqual(
            [event.event_type for event in self.store.list_promotion_events(self.promotion_id, limit=10)],
            ['promotion.accepted', 'promotion.consumed'],
        )

    def test_consumer_modules_have_no_external_effect_capabilities(self) -> None:
        source_root = Path(__file__).resolve().parents[1] / 'src' / 'adaptive_trust_ci'
        forbidden_imports = {'subprocess', 'socket', 'requests', 'httpx', 'urllib'}
        forbidden_calls = {'system', 'popen', 'Popen', 'run', 'urlopen', 'deploy', 'publish'}
        for name in ('api.py', 'promotion_consumer.py'):
            tree = ast.parse((source_root / name).read_text(encoding='utf-8'))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split('.')[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split('.')[0])
            called = {
                node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, (ast.Attribute, ast.Name))
            }
            self.assertFalse(imported & forbidden_imports, name)
            self.assertFalse(called & forbidden_calls, name)


if __name__ == '__main__':
    unittest.main()
