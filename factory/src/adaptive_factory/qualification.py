"""Read-only v1.5 qualification composed from existing task authority and evidence."""
from .contracts import ContractError
from .context_contracts import ContextManifestV1
from .decision_contracts import DecisionRecordV1, summarize_cost
from .prediction_contracts import PredictionObservationV1
from .result_contracts import ToolResultEnvelopeV1, SemanticExecutionEvidenceV2
from .v15_contracts import FrozenWire, closed, identity, digest, sha, sequence


class FactoryV15QualificationV1(FrozenWire):
    pass


def qualify(repository_id, task_id, evidence):
    identity(repository_id); identity(task_id)
    allowed = {'context', 'decisions', 'result', 'semantic', 'technical', 'prediction', 'cost_entries', 'expected_usage_ids'}
    if not isinstance(evidence, dict) or set(evidence)-allowed: raise ContractError('unknown_qualification_evidence')
    missing = []; digests = []; candidate = None; context_digest = None; statuses = []
    context = evidence.get('context'); result = evidence.get('result')
    if context is not None:
        context = ContextManifestV1.from_dict(context.to_dict(), expected_repository=repository_id)
        source = context.to_dict(); candidate = source['source_snapshot']['head_sha']; context_digest = context.context_digest
        digests.append(context.context_digest)
    else: missing.append('context')
    decisions = sequence(evidence.get('decisions', []))
    if not decisions: missing.append('decisions')
    for record in decisions:
        record = DecisionRecordV1.from_dict(record.to_dict()); facts = record.to_dict()
        if (facts['repository_id'], facts['task_id'], facts['head_sha'], facts['context_digest']) != (repository_id, task_id, candidate, context_digest):
            raise ContractError('decision_qualification_binding_mismatch')
        if context and facts['spec_digest'] != context.to_dict()['change_spec_digest']:
            raise ContractError('decision_spec_mismatch')
        digests.append(record.record_digest)
    if result is None: missing.append('result')
    else:
        result = ToolResultEnvelopeV1.from_dict(result.to_dict()); digests.append(result.record_digest)
        if result.to_dict()['outcome'] != 'allow': missing.append('complete_result')
    semantic = sequence(evidence.get('semantic', [])); checked = set()
    if not semantic: missing.append('semantic')
    for record in semantic:
        record = SemanticExecutionEvidenceV2.from_dict(record.to_dict()); facts = record.to_dict()
        if (facts['repository_id'], facts['task_id'], facts['candidate_sha'], facts['context_digest']) != (repository_id, task_id, candidate, context_digest):
            raise ContractError('semantic_qualification_binding_mismatch')
        if result is None: missing.append('semantic_result')
        else: record.bind_result(result)
        binding = (facts['criterion_id'], facts['rule_id'], facts['rule_revision'])
        if binding in checked: raise ContractError('duplicate_semantic_evidence')
        checked.add(binding); statuses.append(facts['result']); digests.append(record.record_digest)
    if context:
        required = {(b['criterion_id'], b['rule_id'], b['revision']) for b in context.to_dict()['rule_bindings']}
        if checked-required: raise ContractError('semantic_rule_mismatch')
        if required-checked: missing.append('rule_execution')
    technical = evidence.get('technical')
    if technical is None: missing.append('technical')
    else:
        closed(technical, ('candidate_sha', 'result', 'report_digest')); sha(technical['candidate_sha']); digest(technical['report_digest'])
        if technical['candidate_sha'] != candidate: raise ContractError('technical_candidate_mismatch')
        if technical['result'] not in ('pass', 'fail', 'blocked', 'not_evaluated'): raise ContractError('invalid_technical_result')
        statuses.append(technical['result']); digests.append(technical['report_digest'])
    prediction_status = 'not_qualified'
    if evidence.get('prediction') is not None:
        prediction = PredictionObservationV1.from_dict(evidence['prediction'].to_dict()); facts = prediction.to_dict()
        if (facts['repository_id'], facts['candidate_sha']) != (repository_id, candidate): raise ContractError('prediction_candidate_mismatch')
        prediction_status = prediction.status; digests.append(prediction.record_digest)
    if 'fail' in statuses: core = 'fail'
    elif 'blocked' in statuses: core = 'blocked'
    elif missing or 'not_evaluated' in statuses or not statuses: core = 'not_evaluated'
    else: core = 'ready_for_human'
    return FactoryV15QualificationV1.freeze(dict(schema_version=1, repository_id=repository_id, task_id=task_id,
        candidate_sha=candidate, context_digest=context_digest, implementation_status='implemented', core_status=core,
        missing_evidence=sorted(set(missing)), evidence_digests=sorted(set(digests)),
        cost=summarize_cost(evidence.get('cost_entries', []), expected_usage_ids=evidence.get('expected_usage_ids')), prediction_status=prediction_status,
        apple_status='excluded_by_owner', bb_status='not_run', fpf_status='not_evaluated', vibevm_status='not_evaluated',
        m8_status='inactive', external_trust_status='pending', human_acceptance='awaiting_human', authority_effect='none'))


class FactoryV15QualificationService:
    def __init__(self, factory_service, evidence_reader):
        self.factory_service = factory_service
        self.evidence_reader = evidence_reader

    def get_qualification(self, task_id, *, actor):
        # Existing factory access check happens before reading any evidence.
        task = self.factory_service.get_task(task_id, actor=actor)
        return qualify(task.repository_id, task.task_id, self.evidence_reader(task))
