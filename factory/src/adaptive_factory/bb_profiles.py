"""Pinned discovery/workflow/recovery contracts; installation remains a separate port."""
from typing import Protocol
from .contracts import ContractError
from .v15_contracts import FrozenWire, closed, version, identity, integer, digest, sha, sequence


class BBDiscoveryV1(FrozenWire):
    @classmethod
    def from_dict(cls,data):
        closed(data,('schema_version','source_commit','binary_digest','daemon_digest','provider_cli_digest',
            'adapter_digest','plugin_digests','os','architecture','api_version','provider','model','reasoning',
            'permission','capabilities','listeners','network_destinations','telemetry','auto_update','install_hooks',
            'license_review_digest'))
        version(data); sha(data['source_commit'])
        for field in ('binary_digest','daemon_digest','provider_cli_digest','adapter_digest','license_review_digest'): digest(data[field])
        for field in ('os','architecture','api_version','provider','model','reasoning','permission'): identity(data[field])
        if not isinstance(data['plugin_digests'],dict) or len(data['plugin_digests'])>16: raise ContractError('bb_invalid_plugin_inventory')
        for name,value in data['plugin_digests'].items(): identity(name); digest(value)
        for field in ('capabilities','listeners','network_destinations'):
            values=sequence(data[field],32)
            if len(set(values))!=len(values): raise ContractError('bb_duplicate_discovery')
            for value in values: identity(value)
        if not data['listeners'] or any(value not in ('loopback_authenticated','private_authenticated') for value in data['listeners']): raise ContractError('bb_unsafe_listener')
        for field in ('telemetry','auto_update','install_hooks'):
            if data[field] is not False: raise ContractError('bb_unapproved_install_or_egress')
        return cls.freeze(data)


def check_discovery(requested,resolved,*,required_capabilities):
    requested=BBDiscoveryV1.from_dict(requested); resolved=BBDiscoveryV1.from_dict(resolved)
    required=set(sequence(required_capabilities,32))
    if requested.record_digest!=resolved.record_digest or not required<=set(resolved.to_dict()['capabilities']): raise ContractError('bb_unsupported_or_unresolved_profile')
    return dict(status='supported',profile_digest=resolved.record_digest,
        requested_digest=requested.record_digest,resolved_digest=resolved.record_digest,
        qualification='not_run',authority_effect='none')


class BBWorkflowSnapshotV1(FrozenWire):
    @classmethod
    def from_dict(cls,data):
        closed(data,('schema_version','workflow_id','script_digest','schema_digest','provider_profile_digest',
            'steps','max_agents','max_depth','max_physical_attempts','max_notifications','retry_owner',
            'max_cost_usd_micros','wall_seconds','orchestra_enabled','orchestra_plugin_digest'))
        version(data); identity(data['workflow_id'])
        for field in ('script_digest','schema_digest','provider_profile_digest'): digest(data[field])
        steps=sequence(data['steps'],32)
        if not steps or any(step not in ('implement','test','review','fixed_fanout') for step in steps): raise ContractError('bb_unknown_workflow_step')
        for field in ('max_agents','max_depth','max_physical_attempts','max_notifications','max_cost_usd_micros','wall_seconds'): integer(data[field],field,1,1000000000)
        if data['retry_owner'] not in ('factory','bb'): raise ContractError('bb_multiple_retry_owners')
        if data['orchestra_enabled'] is not False or data['orchestra_plugin_digest'] is not None: raise ContractError('bb_orchestra_unqualified')
        return cls.freeze(data)


def workflow_call_allowed(workflow,*,physical_attempts,notifications,agents,depth,reserved_cost_usd_micros):
    data=BBWorkflowSnapshotV1.from_dict(workflow.to_dict()).to_dict()
    for name,value in (('physical_attempts',physical_attempts),('notifications',notifications),('agents',agents),('depth',depth),('reserved_cost',reserved_cost_usd_micros)): integer(value,name)
    if (physical_attempts>=data['max_physical_attempts'] or notifications>=data['max_notifications'] or
        agents>=data['max_agents'] or depth>data['max_depth'] or reserved_cost_usd_micros>=data['max_cost_usd_micros']): raise ContractError('bb_workflow_budget_exceeded')
    return True


class BBRecoverySnapshotV1(FrozenWire):
    @classmethod
    def from_dict(cls,data):
        closed(data,('schema_version','version','source_commit','archive_digest','data_schema_version',
            'data_digest','config_digest','mappings_digest','artifacts_digest','external_receipts_digest'))
        version(data); identity(data['version']); sha(data['source_commit']); integer(data['data_schema_version'],'data_schema_version',1)
        for name in ('archive_digest','data_digest','config_digest','mappings_digest','artifacts_digest','external_receipts_digest'): digest(data[name])
        return cls.freeze(data)


def validate_recovery(snapshot,*,compatible_schema_versions,restored_digests):
    data=BBRecoverySnapshotV1.from_dict(snapshot.to_dict()).to_dict()
    versions=sequence(compatible_schema_versions,32)
    for value in versions: integer(value,'data_schema_version',1)
    names=('data_digest','config_digest','mappings_digest','artifacts_digest','external_receipts_digest')
    closed(restored_digests,names)
    if data['data_schema_version'] not in versions or any(restored_digests[name]!=data[name] for name in names): raise ContractError('bb_recovery_incompatible_or_unreconciled')
    return dict(status='compatible',external_effects='receipts_reconciled',authority_effect='none')


class BBPayloadLifecycle(Protocol):
    """Port for a separately admitted generic installer, not an upstream BB API claim.

    Implementations must verify detached archive identity before mutation, preserve immutable
    version directories, health-gate the atomic current pointer, and retain data/receipts.
    A rollback must validate schema compatibility and reconcile external effects, not silently
    run an old binary on a new SQLite schema. No method conveys execution/merge authority.
    """
    def status(self) -> dict: ...
    def verify_archive(self,archive_identity: dict) -> dict: ...
    def backup(self,snapshot: BBRecoverySnapshotV1) -> dict: ...
    def switch(self,version: str) -> dict: ...
    def rollback(self,snapshot: BBRecoverySnapshotV1) -> dict: ...


class UnavailableBBPayloadLifecycle:
    def status(self): return dict(status='unavailable',enabled=False,authority_effect='none')
    def verify_archive(self,archive_identity): raise ContractError('bb_payload_lifecycle_unavailable')
    def backup(self,snapshot): raise ContractError('bb_payload_lifecycle_unavailable')
    def switch(self,version): raise ContractError('bb_payload_lifecycle_unavailable')
    def rollback(self,snapshot): raise ContractError('bb_payload_lifecycle_unavailable')
