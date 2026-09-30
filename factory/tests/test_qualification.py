import importlib
import importlib.util
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.contracts import ContractError
from adaptive_factory.models import Actor, TaskProjection, TaskStatus
from adaptive_factory.context_contracts import ContextManifestV1
from adaptive_factory.decision_contracts import DecisionRecordV1
from adaptive_factory.result_contracts import ToolResultEnvelopeV1, SemanticExecutionEvidenceV2
from factory.tests.test_context_contracts import context_facts
from factory.tests.test_decision_contracts import decision_facts


def qualification_evidence():
    context = ContextManifestV1.from_dict(context_facts())
    facts = decision_facts(); facts['context_digest'] = context.context_digest
    decision = DecisionRecordV1.from_dict(facts)
    result = ToolResultEnvelopeV1.from_result('check passed', channel='stdout', profile='native-fixture-1', before_model=True)
    semantic = SemanticExecutionEvidenceV2.from_dict(dict(schema_version=2, repository_id='owner/project',
        task_id=facts['task_id'], candidate_sha='2'*40, context_digest=context.context_digest,
        criterion_id='AC-001', rule_id='RULE-1', rule_revision='1', command=['python3','check.py'],
        selector='check_rule', result='pass', tool_result_digest=result.record_digest, report_digest='6'*64))
    return dict(context=context, decisions=[decision], result=result, semantic=[semantic],
                technical=dict(candidate_sha='2'*40, result='pass', report_digest='7'*64), prediction=None)


class QualificationTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('adaptive_factory.qualification'), 'qualification consumer missing')
        return importlib.import_module('adaptive_factory.qualification')

    def test_bound_evidence_yields_human_handoff_without_external_authority(self):
        module = self.module(); data = module.qualify('owner/project', '00000000-0000-0000-0000-000000000001', qualification_evidence()).to_dict()
        self.assertEqual(data['core_status'], 'ready_for_human')
        self.assertEqual(data['apple_status'], 'excluded_by_owner')
        self.assertEqual(data['prediction_status'], 'not_qualified')
        self.assertEqual(data['bb_status'], 'not_run')
        self.assertEqual(data['m8_status'], 'inactive')
        self.assertEqual(data['external_trust_status'], 'pending')
        self.assertEqual(data['human_acceptance'], 'awaiting_human')
        self.assertEqual(data['authority_effect'], 'none')
        self.assertIsNone(data['cost']['total_usd_micros'])

    def test_missing_stale_cross_repository_or_mapped_only_evidence_never_passes(self):
        module = self.module(); task='00000000-0000-0000-0000-000000000001'
        empty = module.qualify('owner/project', task, {}).to_dict()
        self.assertEqual(empty['core_status'], 'not_evaluated')
        self.assertIn('context', empty['missing_evidence'])
        evidence = qualification_evidence(); evidence['semantic'] = []
        self.assertEqual(module.qualify('owner/project', task, evidence).to_dict()['core_status'], 'not_evaluated')
        evidence = qualification_evidence(); evidence['technical']['candidate_sha']='9'*40
        with self.assertRaises(ContractError): module.qualify('owner/project', task, evidence)
        with self.assertRaises(ContractError): module.qualify('other/project', task, qualification_evidence())

    def test_api_surface_is_default_off_authenticated_and_repository_checked(self):
        module = self.module(); task_id='00000000-0000-0000-0000-000000000001'
        actor=Actor('reader','client',frozenset({'task:read'}),frozenset({'owner/project'}))
        class ExistingFactory:
            def get_task(self, task_id, *, actor):
                if 'owner/project' not in actor.repositories: raise PermissionError('repository denied')
                return TaskProjection(task_id, 'owner/project', TaskStatus.REVIEWING, 1, 'a'*64, 'b'*64, datetime.now(timezone.utc))
        service = ExistingFactory(); auth = Authenticator({'local-test-token': actor})
        path = '/v1.5/tasks/'+task_id+'/qualification'
        with TestClient(create_app(service,auth)) as client:
            self.assertEqual(client.get(path,headers={'Authorization':'Bearer local-test-token'}).status_code,404)
        qualifier = module.FactoryV15QualificationService(service, lambda _task: qualification_evidence())
        with TestClient(create_app(service,auth,qualification_service=qualifier)) as client:
            self.assertEqual(client.get(path).status_code,401)
            response=client.get(path,headers={'Authorization':'Bearer local-test-token'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['external_trust_status'],'pending')
