import importlib
import importlib.util
import json
import unittest

from adaptive_factory.contracts import ContractError


class ResultContractTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('adaptive_factory.result_contracts'), 'pre-model contract missing')
        return importlib.import_module('adaptive_factory.result_contracts')

    def test_every_supported_channel_cleans_before_model_and_sinks(self):
        module = self.module()
        for channel in ('structured','stdout','stderr','error','stream','attachment','cache','resume'):
            secret = 'ghp_' + 'syntheticCanary123456'
            payload = {'message': secret, 'safe': 7} if channel == 'structured' else secret
            if channel == 'stream': payload = ['gh', 'p_', 'syntheticCanary123456']
            received = []; reports = []
            envelope, result = module.reuse_tool_result(payload, channel=channel,
                profile='native-fixture-1', before_model=True, model=lambda data: received.append(data) or 'model-result',
                sinks=(reports.append,))
            self.assertEqual(envelope.to_dict()['outcome'], 'redacted')
            self.assertEqual(result, 'model-result')
            self.assertNotIn(secret, json.dumps(received + reports))
            self.assertIn('[REDACTED]', json.dumps(received))

    def test_unsupported_oversized_and_invalid_results_never_reach_model(self):
        module = self.module(); received = []
        cases = [dict(payload='safe', before_model=False), dict(payload='x'*65537, before_model=True),
                 dict(payload=b'\xff', before_model=True), dict(payload=object(), before_model=True)]
        for case in cases:
            envelope, result = module.reuse_tool_result(case.pop('payload'), channel='stdout', profile='native-1',
                model=received.append, **case)
            self.assertIn(envelope.to_dict()['outcome'], ('rejected','unavailable'))
            self.assertIsNone(result); self.assertIsNone(envelope.to_dict()['payload'])
        self.assertEqual(received, [])

    def test_result_replay_identity_is_sanitized_and_policy_bound(self):
        module = self.module()
        first = module.ToolResultEnvelopeV1.from_result('safe', channel='cache', profile='native-1', before_model=True)
        replay = module.ToolResultEnvelopeV1.from_result('safe', channel='cache', profile='native-1', before_model=True)
        changed = module.ToolResultEnvelopeV1.from_result('safe', channel='cache', profile='native-2', before_model=True)
        self.assertEqual(first.record_digest, replay.record_digest)
        self.assertNotEqual(first.record_digest, changed.record_digest)

    def test_semantic_execution_evidence_binds_candidate_context_rule_command_and_result(self):
        module = self.module()
        envelope = module.ToolResultEnvelopeV1.from_result('safe', channel='stdout', profile='native-1', before_model=True)
        facts = dict(schema_version=2, repository_id='owner/project', task_id='task-1', candidate_sha='1'*40,
                     context_digest='2'*64, criterion_id='AC-001', rule_id='RULE-1', rule_revision='1',
                     command=['python3','tests/check.py'], selector='check_rule', result='pass',
                     tool_result_digest=envelope.record_digest, report_digest='3'*64)
        record = module.SemanticExecutionEvidenceV2.from_dict(facts)
        record.bind_result(envelope)
        facts['tool_result_digest'] = '4'*64
        with self.assertRaises(ContractError): module.SemanticExecutionEvidenceV2.from_dict(facts).bind_result(envelope)
        facts['authority'] = True
        with self.assertRaises(ContractError): module.SemanticExecutionEvidenceV2.from_dict(facts)
