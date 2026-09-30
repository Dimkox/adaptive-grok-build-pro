"""Factory-owned BB lifecycle seam. Real upstream profiles remain unsupported/default-off.

The deterministic transport exercise is explicitly synthetic; no HTTP route, process launch,
listener, install hook, or credential fallback is implemented or inferred from upstream docs.
Intent/event facts persist in the existing append-only Factory decision journal. Budget and
physical usage use the existing Factory ledger, never a second backend ledger.
"""
from .contracts import ContractError, canonical_digest
from .decision_contracts import DecisionRecordV1
from .bb_contracts import BBBackendProfileV1, BBLifecycleObservationV1
from .v15_contracts import FrozenWire, closed, version, identity, integer, digest, sha, path, timestamp, sequence, safe_text
import hashlib


class BBUsageObservationV1(FrozenWire):
    @classmethod
    def from_dict(cls,data):
        closed(data,('schema_version','provider_request_id','provider','model','binding_digest',
            'input_tokens','output_tokens','reasoning_tokens','cached_input_tokens','cache_write_tokens',
            'missing_reason','provider_cost_usd_micros','calculated_cost_usd_micros','confirmed_cost_usd_micros',
            'price_table_digest','usage_source','cost_status','reasoning_in_output','cache_in_input'))
        version(data)
        for field in ('provider_request_id','provider','model','usage_source'): identity(data[field])
        digest(data['binding_digest'])
        if data['price_table_digest'] is not None: digest(data['price_table_digest'])
        for field in ('reasoning_in_output','cache_in_input'):
            if type(data[field]) is not bool: raise ContractError('bb_invalid_counter_semantics')
        nullable=('input_tokens','output_tokens','reasoning_tokens','cached_input_tokens','cache_write_tokens',
                  'provider_cost_usd_micros','calculated_cost_usd_micros','confirmed_cost_usd_micros')
        for field in nullable:
            if data[field] is not None: integer(data[field],field)
        if any(data[field] is None for field in nullable) and data['missing_reason'] is None: raise ContractError('bb_missing_usage_reason')
        if data['missing_reason'] is not None: identity(data['missing_reason'])
        for subset,total,flag in (('reasoning_tokens','output_tokens','reasoning_in_output'),('cached_input_tokens','input_tokens','cache_in_input')):
            if data[flag] and data[subset] is not None and data[total] is not None and data[subset]>data[total]: raise ContractError('bb_invalid_counter_subset')
        if data['cost_status'] not in ('actual','estimated','unknown'): raise ContractError('bb_invalid_cost_status')
        if data['cost_status']=='actual' and data['confirmed_cost_usd_micros'] is None: raise ContractError('bb_unconfirmed_actual_cost')
        if data['cost_status']=='estimated' and (data['calculated_cost_usd_micros'] is None or data['price_table_digest'] is None): raise ContractError('bb_unpriced_estimate')
        return cls.freeze(data)

    @property
    def token_units(self):
        data=self.to_dict()
        if data['input_tokens'] is None or data['output_tokens'] is None: return None
        total=data['input_tokens']+data['output_tokens']
        for field,flag in (('reasoning_tokens','reasoning_in_output'),('cached_input_tokens','cache_in_input')):
            if not data[flag]:
                if data[field] is None: return None
                total+=data[field]
        return total


class BBExecutionBindingV1(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(data, ('schema_version','repository_id','task_id','run_id','attempt_id','fence',
            'contract_digest','policy_digest','context_digest','profile_digest','base_sha','candidate_sha',
            'branch','workspace','environment_id','host_id','project_id','thread_id','workflow_id',
            'provider','model','reasoning','permission','revision','lease_deadline','snapshots','children',
            'exported_evidence_digest'))
        version(data)
        for key in ('repository_id','task_id','run_id','attempt_id','environment_id','host_id','project_id',
                    'thread_id','workflow_id','provider','model','reasoning','permission'): identity(data[key])
        for key in ('contract_digest','policy_digest','context_digest','profile_digest'): digest(data[key])
        for key in ('base_sha','candidate_sha'): sha(data[key])
        for key in ('branch','workspace'): path(data[key])
        integer(data['fence'],'fence',1); integer(data['revision'],'revision',1); timestamp(data['lease_deadline'])
        closed(data['snapshots'],('workflow','schema','environment'))
        for value in data['snapshots'].values(): digest(value)
        children=sequence(data['children'],128); seen=set()
        for child in children:
            closed(child,('attempt_id','thread_id','parent_attempt_id','depth','budget_usd_micros'))
            for key in ('attempt_id','thread_id','parent_attempt_id'): identity(child[key])
            if child['attempt_id'] in seen or child['parent_attempt_id'] != data['attempt_id']: raise ContractError('bb_child_ownership_mismatch')
            seen.add(child['attempt_id']); integer(child['depth'],'depth',1); integer(child['budget_usd_micros'],'budget')
        if data['exported_evidence_digest'] is not None: digest(data['exported_evidence_digest'])
        return cls.freeze(data)


class BBAdapter:
    REQUIRED = frozenset({'submit','status','events','stop','reconcile','artifacts','usage','pre_model_interception'})

    def __init__(self, store, transport, profile, *, synthetic=False):
        self.profile=BBBackendProfileV1.from_dict(profile).to_dict()
        if type(synthetic) is not bool: raise ContractError('invalid_synthetic_mode')
        self.store=store; self.transport=transport; self.synthetic=synthetic; self.disabled=False

    def capabilities(self):
        if self.disabled or not self.synthetic:
            return dict(backend='native',bb_qualification='not_run',supported=False,authority_effect='none')
        if getattr(self.transport,'synthetic',False) is not True or not self.REQUIRED <= set(self.transport.capabilities()):
            raise ContractError('bb_unsupported_profile')
        return dict(backend='bb_synthetic',bb_qualification='not_run',supported=True,authority_effect='none')

    def _validate(self,binding,grant,actor,seed,now,*,observation_only=False):
        binding=BBExecutionBindingV1.from_dict(binding.to_dict()); data=binding.to_dict()
        seed=DecisionRecordV1.from_dict(seed.to_dict()); facts=seed.to_dict()
        if not observation_only and not self.capabilities()['supported']: raise ContractError('bb_live_profile_unqualified')
        if (data['task_id'],data['run_id'],data['fence']) != (grant.task_id,grant.run_id,grant.fence): raise ContractError('bb_stale_fence')
        if (actor.actor_id != grant.owner or 'task:release' not in actor.scopes or
            not ({'*',data['repository_id']} & actor.repositories)): raise ContractError('bb_actor_denied')
        if (facts['repository_id'],facts['task_id'],facts['run_id'],facts['attempt_id'],facts['fence'],facts['context_digest'],facts['profile_digest'],facts['base_sha'],facts['head_sha']) != (data['repository_id'],data['task_id'],data['run_id'],data['attempt_id'],data['fence'],data['context_digest'],data['profile_digest'],data['base_sha'],data['candidate_sha']): raise ContractError('bb_seed_binding_mismatch')
        if not observation_only and now >= min(grant.expires_at,timestamp(data['lease_deadline'])): raise ContractError('bb_lease_expired')
        if len(data['children'])+1 > self.profile['max_agents'] or any(child['depth'] > self.profile['max_depth'] for child in data['children']): raise ContractError('bb_delegation_exceeded')
        if sum(child['budget_usd_micros'] for child in data['children']) > self.profile['max_cost_usd_micros']: raise ContractError('bb_child_budget_exceeded')
        return data,facts

    @staticmethod
    def _operation_key(binding,operation_id):
        identity(operation_id)
        return canonical_digest(dict(binding_digest=binding.record_digest,operation_id=operation_id))

    @staticmethod
    def _record(seed,key,stage,facts,*,outcome='unknown'):
        record=dict(seed); record.update(decision_id='bb-'+stage+'-'+key,decision_kind='qualification',
            rule_id='BB-ADAPTER',rule_version='1',facts=[dict(name='operation_key',value=key)]+
            [dict(name=name,value=value) for name,value in sorted(facts.items())],outcome=outcome,
            reason_code='bb_'+stage,next_step='reconcile' if outcome=='unknown' else 'verify',supersedes=None)
        return DecisionRecordV1.from_dict(record)

    @staticmethod
    def _observation(data,operation_id,command_digest,result):
        closed(result,('acknowledged','effect_outcome','stop_outcome','evidence_digest'))
        return BBLifecycleObservationV1.from_dict(dict(schema_version=1,operation_id=operation_id,
            command_digest=command_digest,**{key:data[key] for key in ('repository_id','task_id','run_id','attempt_id','fence','context_digest','policy_digest')},**result))

    def _command(self,operation,binding,grant,actor,seed,*,operation_id,now,cost=0,tokens=0):
        data,facts=self._validate(binding,grant,actor,seed,now)
        if operation not in self.transport.capabilities(): raise ContractError('bb_operation_unsupported')
        integer(cost,'cost',0,self.profile['max_cost_usd_micros']); integer(tokens,'tokens')
        if operation=='submit' and 'task:budget' not in actor.scopes: raise ContractError('bb_budget_denied')
        key=self._operation_key(binding,operation_id)
        command_digest=canonical_digest(dict(operation=operation,binding_digest=binding.record_digest,cost=cost,tokens=tokens))
        intent=self._record(facts,key,'intent',dict(command_digest=command_digest,operation=operation,binding_digest=binding.record_digest))
        fresh=self.store.begin_bb_operation(grant,intent,actor)
        if not fresh:
            records=self.store.bb_operation_records(grant,actor,key)
            for record in reversed(records):
                stored={fact['name']:fact['value'] for fact in record.to_dict()['facts']}
                if record.to_dict()['reason_code']=='bb_result' or record.to_dict()['reason_code'].startswith('bb_reconciled-'):
                    return self._observation(data,operation_id,command_digest,{field:stored[field] for field in ('acknowledged','effect_outcome','stop_outcome','evidence_digest')})
            return self._observation(data,operation_id,command_digest,dict(acknowledged=False,effect_outcome='unknown',stop_outcome='unknown',evidence_digest=None))
        # Reservation failure leaves intent unknown; reconciliation is mandatory, not retry.
        if operation=='submit':
            self.store.reserve_budget(grant,cost,tokens,self.profile['wall_seconds'],command_digest,key,actor)
        timeout=min(self.profile['stop_seconds'] if operation in ('stop','pause') else self.profile['wall_seconds'],int((min(grant.expires_at,timestamp(data['lease_deadline']))-now).total_seconds()))
        if timeout <= 0: raise ContractError('bb_lease_expired')
        try:
            result=self.transport.command(operation,binding,dict(operation_id=operation_id,command_digest=command_digest),timeout_seconds=timeout)
        except (TimeoutError,ConnectionError):
            result=dict(acknowledged=False,effect_outcome='unknown',stop_outcome='unknown',evidence_digest=None)
        observation=self._observation(data,operation_id,command_digest,result)
        self.store.append_decision(grant,self._record(facts,key,'result',dict(command_digest=command_digest,**result),outcome='observed' if result['effect_outcome']=='observed' else 'unknown'),actor)
        return observation

    def submit(self,binding,grant,actor,seed,*,operation_id,cost_usd_micros,token_units,now):
        return self._command('submit',binding,grant,actor,seed,operation_id=operation_id,now=now,cost=cost_usd_micros,tokens=token_units)

    def stop(self,binding,grant,actor,seed,*,operation_id,now):
        return self._command('stop',binding,grant,actor,seed,operation_id=operation_id,now=now)

    def intervene(self,operation,binding,grant,actor,seed,*,operation_id,expected_revision,now):
        if operation not in ('pause','resume') or expected_revision != binding.to_dict()['revision']: raise ContractError('bb_stale_intervention')
        return self._command(operation,binding,grant,actor,seed,operation_id=operation_id,now=now)

    def reconcile(self,binding,grant,actor,seed,*,operation_id,now):
        data,facts=self._validate(binding,grant,actor,seed,now); key=self._operation_key(binding,operation_id)
        records=self.store.bb_operation_records(grant,actor,key)
        intents=[record for record in records if record.to_dict()['reason_code']=='bb_intent']
        if len(intents)!=1: raise ContractError('bb_intent_missing')
        command={fact['name']:fact['value'] for fact in intents[0].to_dict()['facts']}['command_digest']
        try: result=self.transport.reconcile(binding,operation_id,timeout_seconds=self.profile['stop_seconds'])
        except (TimeoutError,ConnectionError): result=dict(acknowledged=False,effect_outcome='unknown',stop_outcome='unknown',evidence_digest=None)
        observation=self._observation(data,operation_id,command,result)
        stage='reconciled-'+observation.record_digest[:16]
        self.store.append_decision(grant,self._record(facts,key,stage,dict(command_digest=command,**result),outcome='observed' if result['effect_outcome']=='observed' else 'unknown'),actor)
        return observation

    def ingest_event(self,binding,grant,actor,seed,event,*,now):
        self._validate(binding,grant,actor,seed,now)
        closed(event,('schema_version','event_id','source','occurred_at','received_at','binding_digest','type','payload_digest')); version(event)
        for field in ('event_id','source','type'): identity(event[field])
        digest(event['binding_digest']); digest(event['payload_digest'])
        if timestamp(event['occurred_at']) > timestamp(event['received_at']): raise ContractError('bb_invalid_event_time')
        if event['binding_digest'] != binding.record_digest: raise ContractError('bb_event_binding_mismatch')
        key=self._operation_key(binding,event['event_id'])
        return self.store.begin_bb_operation(grant,self._record(seed.to_dict(),key,'event',dict(event_digest=canonical_digest(event)),outcome='observed'),actor)

    def status(self,binding,grant,actor,seed,*,now):
        data,_=self._validate(binding,grant,actor,seed,now)
        result=self.transport.read('status',binding,timeout_seconds=self.profile['stop_seconds'])
        closed(result,('binding_digest','revision','observed_at','state','workers'))
        if result['binding_digest']!=binding.record_digest or result['revision']!=data['revision']: raise ContractError('bb_status_binding_mismatch')
        observed=timestamp(result['observed_at'])
        if observed>now: raise ContractError('bb_future_observation')
        if result['state'] not in ('queued','running','idle','completed','failed','unknown','stopped','waiting_human'): raise ContractError('bb_invalid_state')
        workers=sequence(result['workers'],self.profile['max_agents'])
        expected={data['attempt_id']}|{child['attempt_id'] for child in data['children']}
        if set(workers)!=expected or len(workers)!=len(set(workers)): raise ContractError('bb_worker_tree_mismatch')
        return dict(result,fresh=(now-observed).total_seconds()<=self.profile['lease_seconds'],
                    acceptance='awaiting_independent_review',authority_effect='none')

    def artifacts(self,binding,grant,actor,seed,*,now):
        self._validate(binding,grant,actor,seed,now)
        result=self.transport.read('artifacts',binding,timeout_seconds=self.profile['stop_seconds'])
        closed(result,('binding_digest','artifacts'))
        if result['binding_digest']!=binding.record_digest: raise ContractError('bb_artifact_binding_mismatch')
        artifacts=sequence(result['artifacts'],32); seen=set(); size=0
        for artifact in artifacts:
            closed(artifact,('path','content','sha256','size_bytes')); path(artifact['path']); digest(artifact['sha256'])
            safe_text(artifact['content'],'artifact',65536); integer(artifact['size_bytes'],'size_bytes',0,65536)
            raw=artifact['content'].encode('utf-8'); size+=len(raw)
            if artifact['path'] in seen or len(raw)!=artifact['size_bytes'] or hashlib.sha256(raw).hexdigest()!=artifact['sha256'] or size>1_048_576: raise ContractError('bb_artifact_integrity_mismatch')
            seen.add(artifact['path'])
        return artifacts

    def usage(self,binding,grant,actor,seed,*,now):
        self._validate(binding,grant,actor,seed,now)
        observations=sequence(self.transport.read('usage',binding,timeout_seconds=self.profile['stop_seconds']),128)
        result=[]; seen={}
        for data in observations:
            record=BBUsageObservationV1.from_dict(data); data=record.to_dict()
            if data['binding_digest']!=binding.record_digest or (data['provider'],data['model'])!=(binding.to_dict()['provider'],binding.to_dict()['model']): raise ContractError('bb_usage_binding_mismatch')
            key=data['provider_request_id']
            if key in seen:
                if seen[key]!=record.record_digest: raise ContractError('bb_usage_conflict')
                continue
            seen[key]=record.record_digest; result.append(record)
        return result

    def ingest_usage(self,binding,grant,actor,seed,usage,*,now):
        data,facts=self._validate(binding,grant,actor,seed,now,observation_only=True)
        if 'task:budget' not in actor.scopes: raise ContractError('bb_usage_actor_denied')
        record=BBUsageObservationV1.from_dict(usage); usage=record.to_dict()
        if usage['binding_digest']!=binding.record_digest or (usage['provider'],usage['model'])!=(data['provider'],data['model']): raise ContractError('bb_usage_binding_mismatch')
        key=self._operation_key(binding,'usage-'+usage['provider_request_id'])
        decision=self._record(facts,key,'usage',{name:value for name,value in usage.items() if name!='schema_version'},outcome='observed')
        return self.store.observe_bb_usage(grant,record,actor,decision)

    @staticmethod
    def validate_resume(original,current,*,actual_artifacts,expected_artifacts,access_allowed):
        if access_allowed is not True or original.record_digest != current.record_digest or actual_artifacts != expected_artifacts: raise ContractError('bb_resume_incompatible')
        for name,value in actual_artifacts.items(): path(name); digest(value)

    @staticmethod
    def cleanup_allowed(binding,*,stop_outcome):
        if stop_outcome!='observed' or binding.to_dict()['exported_evidence_digest'] is None: raise ContractError('bb_evidence_not_exported')
        return True

    def disable(self,observations):
        self.disabled=True; safe=[]; quarantined=[]
        for observation in observations:
            data=BBLifecycleObservationV1.from_dict(observation.to_dict()).to_dict()
            # Acknowledgement is not cancellation; only rejected/unavailable effects are safe.
            (safe if data['effect_outcome'] in ('rejected','unavailable') else quarantined).append(data['operation_id'])
        return dict(backend='native',safe_native_operations=sorted(safe),quarantined_operations=sorted(quarantined),authority_effect='none')

    def supervise(self,binding,grant,*,now):
        data=BBExecutionBindingV1.from_dict(binding.to_dict()).to_dict()
        expired=now >= min(grant.expires_at,timestamp(data['lease_deadline']))
        fenced=(data['task_id'],data['run_id'],data['fence']) != (grant.task_id,grant.run_id,grant.fence)
        return dict(state='quarantined' if expired or fenced else 'active',new_calls_allowed=not (expired or fenced or self.disabled),
            stop_outcome='unknown' if expired or fenced else 'not_requested',authority_effect='none')
