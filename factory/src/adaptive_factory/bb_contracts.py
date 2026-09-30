"""BB-01 admission boundary only. Live backends are deliberately unqualified."""
from .contracts import ContractError, canonical_digest
from .v15_contracts import FrozenWire, closed, version, identity, digest, sha, integer, sequence


class BBBackendProfileV1(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(data, ('schema_version', 'profile_id', 'enabled', 'source_commit', 'binary_digest',
                     'workflows_digest', 'orchestra_digest', 'capabilities', 'max_agents', 'max_depth',
                     'max_cost_usd_micros', 'wall_seconds', 'lease_seconds', 'stop_seconds'))
        version(data); identity(data['profile_id'])
        if data['enabled'] is not False: raise ContractError('bb_live_profile_unqualified')
        if data['source_commit'] is not None: sha(data['source_commit'])
        for key in ('binary_digest', 'workflows_digest', 'orchestra_digest'):
            if data[key] is not None: digest(data[key])
        capabilities = sequence(data['capabilities'], 16)
        if len(set(capabilities)) != len(capabilities): raise ContractError('duplicate_capability')
        for capability in capabilities:
            if capability not in ('observe', 'pause', 'resume', 'cancel', 'pre_model_interception'):
                raise ContractError('unknown_capability')
        for key in ('max_agents', 'max_depth', 'max_cost_usd_micros', 'wall_seconds', 'lease_seconds', 'stop_seconds'):
            integer(data[key], key, 1, 1000000000)
        if data['lease_seconds'] > data['wall_seconds'] or data['stop_seconds'] > data['lease_seconds']:
            raise ContractError('invalid_deadlines')
        return cls.freeze(data)


def select_backend(profile):
    BBBackendProfileV1.from_dict(profile.to_dict())
    return dict(backend='native', bb_qualification='not_run', authority_effect='none')


class BBLifecycleObservationV1(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(data, ('schema_version', 'repository_id', 'task_id', 'run_id', 'attempt_id', 'fence',
                     'context_digest', 'policy_digest', 'operation_id', 'command_digest', 'acknowledged',
                     'effect_outcome', 'stop_outcome', 'evidence_digest'))
        version(data)
        for key in ('repository_id', 'task_id', 'run_id', 'attempt_id', 'operation_id'): identity(data[key])
        integer(data['fence'], 'fence', 1)
        for key in ('context_digest', 'policy_digest', 'command_digest'): digest(data[key])
        if type(data['acknowledged']) is not bool: raise ContractError('invalid_acknowledgement')
        for key in ('effect_outcome', 'stop_outcome'):
            if data[key] not in ('unknown', 'observed', 'rejected', 'unavailable'): raise ContractError('invalid_observation')
        if data['evidence_digest'] is not None: digest(data['evidence_digest'])
        if 'observed' in (data['effect_outcome'], data['stop_outcome']) and data['evidence_digest'] is None:
            raise ContractError('effect_evidence_missing')
        return cls.freeze(data)

    @property
    def operation_key(self):
        data = self.to_dict()
        return canonical_digest({key: data[key] for key in ('repository_id', 'task_id', 'run_id', 'attempt_id', 'fence',
            'context_digest', 'policy_digest', 'operation_id', 'command_digest')})

    def validate_binding(self, *, repository_id, task_id, run_id, fence):
        data = self.to_dict()
        if (data['repository_id'], data['task_id'], data['run_id'], data['fence']) != (repository_id, task_id, run_id, fence):
            raise ContractError('bb_identity_mismatch')

    def validate_replay(self, other):
        other = BBLifecycleObservationV1.from_dict(other.to_dict())
        if self.operation_key != other.operation_key: raise ContractError('bb_idempotency_conflict')
