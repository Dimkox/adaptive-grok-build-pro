import importlib
import unittest
from copy import deepcopy
from adaptive_factory.contracts import ContractError


def discovery():
    return dict(schema_version=1,source_commit='1'*40,binary_digest='2'*64,daemon_digest='3'*64,
        provider_cli_digest='4'*64,adapter_digest='5'*64,plugin_digests={},os='linux',architecture='x86_64',
        api_version='fixture-v1',provider='fixture',model='fixture-v1',reasoning='none',permission='isolated',
        capabilities=['submit','status','events','stop','reconcile','artifacts','usage','pre_model_interception'],
        listeners=['loopback_authenticated'],network_destinations=['fixture.local'],telemetry=False,auto_update=False,
        install_hooks=False,license_review_digest='6'*64)


class BBProfileTests(unittest.TestCase):
    def module(self): return importlib.import_module('adaptive_factory.bb_profiles')

    def test_discovery_rejects_unpinned_unsafe_and_unresolved_profiles_before_execution(self):
        module=self.module(); requested=discovery(); resolved=deepcopy(requested)
        report=module.check_discovery(requested,resolved,required_capabilities=requested['capabilities'])
        self.assertEqual(report['status'],'supported'); self.assertEqual(report['authority_effect'],'none')
        for field,value in [('model','different'),('source_commit','main'),('telemetry',True),('listeners',['lan_unauthenticated']),('capabilities',[])]:
            data=deepcopy(resolved); data[field]=value
            with self.subTest(field=field), self.assertRaises(ContractError): module.check_discovery(requested,data,required_capabilities=requested['capabilities'])

    def test_workflow_snapshots_limits_and_retry_owner_are_immutable(self):
        module=self.module()
        facts=dict(schema_version=1,workflow_id='flow-1',script_digest='1'*64,schema_digest='2'*64,
            provider_profile_digest='3'*64,steps=['implement','test','review'],max_agents=3,max_depth=1,
            max_physical_attempts=4,max_notifications=1,retry_owner='factory',max_cost_usd_micros=100,
            wall_seconds=60,orchestra_enabled=False,orchestra_plugin_digest=None)
        workflow=module.BBWorkflowSnapshotV1.from_dict(facts)
        self.assertTrue(module.workflow_call_allowed(workflow,physical_attempts=3,notifications=0,agents=2,depth=1,reserved_cost_usd_micros=99))
        with self.assertRaises(ContractError): module.workflow_call_allowed(workflow,physical_attempts=4,notifications=0,agents=2,depth=1,reserved_cost_usd_micros=99)
        facts['retry_owner']='both'
        with self.assertRaises(ContractError): module.BBWorkflowSnapshotV1.from_dict(facts)
        facts['retry_owner']='factory'; facts['orchestra_enabled']=True
        with self.assertRaises(ContractError): module.BBWorkflowSnapshotV1.from_dict(facts)

    def test_payload_lifecycle_default_off_and_recovery_requires_compatible_data_and_effect_receipts(self):
        module=self.module(); port=module.UnavailableBBPayloadLifecycle()
        self.assertEqual(port.status()['status'],'unavailable')
        with self.assertRaises(ContractError): port.switch('version-1')
        snapshot=dict(schema_version=1,version='bb-fixture-1',source_commit='1'*40,archive_digest='2'*64,
            data_schema_version=1,data_digest='3'*64,config_digest='4'*64,mappings_digest='5'*64,
            artifacts_digest='6'*64,external_receipts_digest='7'*64)
        record=module.BBRecoverySnapshotV1.from_dict(snapshot)
        module.validate_recovery(record,compatible_schema_versions=[1],restored_digests={name:snapshot[name] for name in ('data_digest','config_digest','mappings_digest','artifacts_digest','external_receipts_digest')})
        with self.assertRaises(ContractError): module.validate_recovery(record,compatible_schema_versions=[2],restored_digests={})
