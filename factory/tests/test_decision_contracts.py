from copy import deepcopy
import importlib
import importlib.util
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.migrations import discover_migrations
from adaptive_factory.store import PostgresFactoryStore


def decision_facts():
    return dict(schema_version=1, decision_id='decision-1', repository_id='owner/project',
                task_id='00000000-0000-0000-0000-000000000001',
                run_id='00000000-0000-0000-0000-000000000002', attempt_id='attempt-1', fence=1,
                observed_at='2026-09-30T12:00:00Z', decision_kind='state', rule_id='RULE-1',
                rule_version='1', facts=[dict(name='from_state', value='leased'), dict(name='target', value='analyzing')],
                outcome='observed', reason_code='phase_started', base_sha='1'*40, head_sha='2'*40,
                context_digest='3'*64, spec_digest='4'*64, profile_digest='5'*64,
                evidence_refs=['evidence/report.json'], constraints=['scope_bound'], next_step='verify', supersedes=None)


class DecisionContractTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('adaptive_factory.decision_contracts'), 'decision contract missing')
        return importlib.import_module('adaptive_factory.decision_contracts')

    def test_strict_factual_record_and_supersession_identity(self):
        module = self.module(); facts = decision_facts(); record = module.DecisionRecordV1.from_dict(facts)
        self.assertEqual(record.to_dict()['next_step'], 'verify')
        self.assertEqual(record.record_digest, module.DecisionRecordV1.from_dict(deepcopy(facts)).record_digest)
        for key, value in [('outcome','success'), ('fence',True), ('head_sha','bad'), ('supersedes','decision-1')]:
            changed = deepcopy(facts); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError): module.DecisionRecordV1.from_dict(changed)
        facts['facts'][0]['value'] = 'password=synthetic-secret'
        with self.assertRaises(ContractError): module.DecisionRecordV1.from_dict(facts)

    def test_missing_or_estimated_cost_is_explicitly_incomplete(self):
        module = self.module()
        entries = [dict(usage_id='call-1', source='provider', currency='USD', pricing_version='p1',
                        amount_usd_micros=120, status='actual'),
                   dict(usage_id='call-2', source='runner', currency='USD', pricing_version=None,
                        amount_usd_micros=None, status='unknown')]
        self.assertEqual(module.summarize_cost(entries), dict(known_usd_micros=120, complete=False,
                         total_usd_micros=None, unknown_items=1, estimated_items=0))
        self.assertIsNone(module.summarize_cost([])['total_usd_micros'])
        entries[1].update(amount_usd_micros=20, status='estimated', pricing_version='p2')
        self.assertFalse(module.summarize_cost(entries)['complete'])
        entries[1]['status'] = 'actual'
        self.assertEqual(module.summarize_cost(entries, expected_usage_ids=['call-1','call-2'])['total_usd_micros'], 140)
        entries.append(deepcopy(entries[0]))
        with self.assertRaises(ContractError): module.summarize_cost(entries)

    def test_parallel_timing_uses_union_not_sum_and_never_invents_acceptance(self):
        module = self.module()
        intervals = [dict(phase='analysis', start='2026-09-30T12:00:00Z', end='2026-09-30T12:00:10Z'),
                     dict(phase='execution', start='2026-09-30T12:00:05Z', end='2026-09-30T12:00:15Z')]
        summary = module.summarize_timing('2026-09-30T12:00:00Z', '2026-09-30T12:00:20Z', intervals)
        self.assertEqual(summary, dict(age_seconds=20, accepted_seconds=None, observed_wall_seconds=15,
                         resource_seconds=20, human_seconds=None))
        intervals[0]['end'] = '2026-09-30T11:00:00Z'
        with self.assertRaises(ContractError): module.summarize_timing('2026-09-30T12:00:00Z', '2026-09-30T12:00:20Z', intervals)

    def test_cost_completeness_requires_declared_usage_coverage(self):
        module = self.module()
        entry = dict(usage_id='call-1', source='provider', currency='USD', pricing_version='p1',
                     amount_usd_micros=120, status='actual')
        self.assertFalse(module.summarize_cost([entry])['complete'], 'known subset is not full cost')
        self.assertFalse(module.summarize_cost([entry], expected_usage_ids=['call-1','call-2'])['complete'])
        self.assertTrue(module.summarize_cost([entry], expected_usage_ids=['call-1'])['complete'])

    def test_append_only_migration_and_transactional_store_seam_exist(self):
        self.module()
        versions = {m.version: m for m in discover_migrations()}
        self.assertIn(23, versions, 'additive decision migration missing')
        self.assertTrue(hasattr(PostgresFactoryStore, 'append_decision'), 'durable decision consumer missing')
