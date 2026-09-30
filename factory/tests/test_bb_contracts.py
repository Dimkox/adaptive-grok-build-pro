from copy import deepcopy
import importlib
import importlib.util
import unittest
from adaptive_factory.contracts import ContractError


def bb_profile():
    return dict(schema_version=1, profile_id='bb-unqualified-1', enabled=False,
        source_commit=None, binary_digest=None, workflows_digest=None, orchestra_digest=None,
        capabilities=[], max_agents=1, max_depth=1, max_cost_usd_micros=100000,
        wall_seconds=60, lease_seconds=30, stop_seconds=10)


def bb_observation():
    return dict(schema_version=1, repository_id='owner/project', task_id='task-1', run_id='run-1',
        attempt_id='attempt-1', fence=1, context_digest='1'*64, policy_digest='2'*64,
        operation_id='op-1', command_digest='3'*64, acknowledged=True,
        effect_outcome='unknown', stop_outcome='unknown', evidence_digest=None)


class BBContractTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('adaptive_factory.bb_contracts'), 'BB boundary missing')
        return importlib.import_module('adaptive_factory.bb_contracts')

    def test_default_off_keeps_native_without_claiming_live_qualification(self):
        module = self.module(); profile = module.BBBackendProfileV1.from_dict(bb_profile())
        self.assertEqual(module.select_backend(profile), dict(backend='native', bb_qualification='not_run', authority_effect='none'))
        facts = bb_profile(); facts['enabled'] = True
        with self.assertRaises(ContractError): module.BBBackendProfileV1.from_dict(facts)
        for key, value in [('max_agents',0), ('wall_seconds',float('inf')), ('stop_seconds',True)]:
            facts = bb_profile(); facts[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError): module.BBBackendProfileV1.from_dict(facts)

    def test_acknowledgement_does_not_confirm_effect_or_stop(self):
        module = self.module(); facts = bb_observation(); record = module.BBLifecycleObservationV1.from_dict(facts)
        self.assertEqual(record.to_dict()['effect_outcome'], 'unknown')
        self.assertEqual(record.to_dict()['stop_outcome'], 'unknown')
        facts['effect_outcome'] = 'observed'
        with self.assertRaises(ContractError): module.BBLifecycleObservationV1.from_dict(facts)
        facts['evidence_digest'] = '4'*64
        module.BBLifecycleObservationV1.from_dict(facts)

    def test_factory_identity_fence_and_replay_conflicts_are_bound(self):
        module = self.module(); facts = bb_observation(); first = module.BBLifecycleObservationV1.from_dict(facts)
        first.validate_binding(repository_id='owner/project', task_id='task-1', run_id='run-1', fence=1)
        with self.assertRaises(ContractError): first.validate_binding(repository_id='other/project', task_id='task-1', run_id='run-1', fence=1)
        first.validate_replay(module.BBLifecycleObservationV1.from_dict(deepcopy(facts)))
        facts['command_digest'] = '5'*64
        with self.assertRaises(ContractError): first.validate_replay(module.BBLifecycleObservationV1.from_dict(facts))
