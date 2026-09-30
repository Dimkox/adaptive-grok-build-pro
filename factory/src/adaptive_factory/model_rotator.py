"""Durable, authority-bound model rotation; no credential or host-settings access."""
from __future__ import annotations
from dataclasses import dataclass
import re, threading
from typing import Mapping
from .contracts import ContractError, HEX40, HEX64, _hex, _id, _text, _time, canonical_digest, canonical_json
from .v15_contracts import integer

_PROVIDERS=frozenset({"openrouter","qwen"})
_RETRYABLE=frozenset({"rate_limit","transport","deadline","unavailable"})
_TERMINAL=frozenset({"authentication","payment","daily_limit","permission","policy","protocol","accounting","input","configuration"})
_SENSITIVE=re.compile(r"(?i)(authorization|bearer|password|secret|api[_-]?key|access[_-]?token)")

def _closed(value,fields):
    if not isinstance(value,Mapping) or set(value)!=set(fields): raise ContractError("closed_object_required")
def _opaque(value,name):
    _id(value,name)
    if _SENSITIVE.search(value): raise ContractError("sensitive_identifier",name)
    return value

@dataclass(frozen=True)
class ModelEntry:
    provider_id:str; model_id:str; free_claim:bool|None; quota_mode:str; enabled:bool; priority:int
    def to_dict(self): return dict(provider_id=self.provider_id,model_id=self.model_id,free_claim=self.free_claim,quota_mode=self.quota_mode,enabled=self.enabled,priority=self.priority)
@dataclass(frozen=True)
class RotationPolicy:
    max_attempts:int; max_cooldown_seconds:int; token_quota:int; request_quota:int; per_attempt_token_limit:int
    def to_dict(self): return dict(max_attempts=self.max_attempts,max_cooldown_seconds=self.max_cooldown_seconds,token_quota=self.token_quota,request_quota=self.request_quota,per_attempt_token_limit=self.per_attempt_token_limit)
@dataclass(frozen=True)
class ProviderRegistryV1:
    schema_version:int; registry_id:str; registry_version:str; provenance:dict; models:tuple[ModelEntry,...]; policy:RotationPolicy
    @classmethod
    def from_dict(cls,data):
        _closed(data,{"schema_version","registry_id","registry_version","provenance","models","policy"})
        if data["schema_version"]!=1: raise ContractError("unsupported_version")
        _opaque(data["registry_id"],"registry_id"); _text(data["registry_version"],"registry_version",32)
        p=data["provenance"]; _closed(p,{"repository","commit","observed_at","source_sha256"})
        _opaque(p["repository"],"repository"); _hex(p["commit"],"commit",HEX40); _time(p["observed_at"],"observed_at"); _hex(p["source_sha256"],"source_sha256",HEX64)
        if not isinstance(data["models"],list) or not 1<=len(data["models"])<=64: raise ContractError("invalid_collection")
        models=[]; identities=set(); priorities=set()
        for raw in data["models"]:
            _closed(raw,{"provider_id","model_id","free_claim","quota_mode","enabled","priority"})
            provider=_opaque(raw["provider_id"],"provider_id"); model=_opaque(raw["model_id"],"model_id")
            if provider not in _PROVIDERS or raw["free_claim"] not in (False,None) or type(raw["enabled"]) is not bool: raise ContractError("unsupported_eligibility_claim")
            if raw["quota_mode"] not in {"token","request"} or (provider=="openrouter" and raw["quota_mode"]!="request"): raise ContractError("invalid_quota_mode")
            priority=integer(raw["priority"],"priority",0,1_000_000)
            if (provider,model) in identities or priority in priorities: raise ContractError("duplicate_model")
            identities.add((provider,model)); priorities.add(priority); models.append(ModelEntry(provider,model,raw["free_claim"],raw["quota_mode"],raw["enabled"],priority))
        models.sort(key=lambda m:m.priority)
        raw=data["policy"]; _closed(raw,{"max_attempts","max_cooldown_seconds","token_quota","request_quota","per_attempt_token_limit"})
        policy=RotationPolicy(integer(raw["max_attempts"],"max_attempts",1,64),integer(raw["max_cooldown_seconds"],"cooldown",1,86400),integer(raw["token_quota"],"quota",1,10_000_000),integer(raw["request_quota"],"request_quota",1,1_000_000),integer(raw["per_attempt_token_limit"],"attempt_limit",1,1_000_000))
        if policy.per_attempt_token_limit>policy.token_quota: raise ContractError("invalid_token_policy")
        return cls(1,data["registry_id"],data["registry_version"],dict(p),tuple(models),policy)
    def to_dict(self): return {"schema_version":1,"registry_id":self.registry_id,"registry_version":self.registry_version,"provenance":dict(self.provenance),"models":[m.to_dict() for m in self.models],"policy":self.policy.to_dict()}
    @property
    def registry_digest(self): return canonical_digest(self.to_dict())
@dataclass(frozen=True)
class RotationBindingV1:
    schema_version:int; tenant_id:str; repository_id:str; task_id:str; run_id:str; attempt_id:str; fence:int; budget_reservation_id:str; budget_digest:str; registry_digest:str; operation_id:str; requested_provider_id:str; requested_model_id:str; remaining_token_units:int; remaining_request_units:int
    @classmethod
    def from_dict(cls,data):
        _closed(data,set(cls.__dataclass_fields__))
        if data["schema_version"]!=1: raise ContractError("unsupported_version")
        for name in ("tenant_id","repository_id","task_id","run_id","attempt_id","budget_reservation_id","operation_id","requested_provider_id","requested_model_id"): _opaque(data[name],name)
        integer(data["fence"],"fence",1); integer(data["remaining_token_units"],"remaining",0); integer(data["remaining_request_units"],"remaining_requests",0); _hex(data["budget_digest"],"budget_digest",HEX64); _hex(data["registry_digest"],"registry_digest",HEX64)
        return cls(**data)
    def to_dict(self): return {name:getattr(self,name) for name in self.__dataclass_fields__}
    @property
    def binding_digest(self): return canonical_digest(self.to_dict())
@dataclass(frozen=True)
class RotationAuthorityGrant:
    tenant_digest:str; repository_id:str; task_id:str; run_id:str; attempt_id:str; fence:int; reservation_id:str; budget_digest:str; token_capacity:int; request_capacity:int
    @classmethod
    def from_authoritative_facts(cls,**facts):
        required={"repository_id","task_id","run_id","attempt_id","fence","reservation_id","budget_digest","token_capacity","request_capacity"}; _closed(facts,required)
        for name in ("repository_id","task_id","run_id","attempt_id","reservation_id"): _opaque(facts[name],name)
        _hex(facts["budget_digest"],"budget_digest",HEX64); integer(facts["fence"],"fence",1); integer(facts["token_capacity"],"token_capacity",0); integer(facts["request_capacity"],"request_capacity",0)
        return cls(canonical_digest(facts["repository_id"]),facts["repository_id"],facts["task_id"],facts["run_id"],facts["attempt_id"],facts["fence"],facts["reservation_id"],facts["budget_digest"],facts["token_capacity"],facts["request_capacity"])
@dataclass(frozen=True)
class TransportResult:
    ok:bool; status_code:int; category:str; response_started:bool; response_digest:str|None; input_tokens:int|None; output_tokens:int|None
    def __post_init__(self):
        if type(self.ok) is not bool or type(self.response_started) is not bool: raise ContractError("invalid_transport_result")
        integer(self.status_code,"status_code",100,599)
        if self.category not in _RETRYABLE|_TERMINAL|{"success"}: raise ContractError("unknown_failure_category")
        if self.ok!=(self.category=="success") or self.ok!=(200<=self.status_code<300): raise ContractError("transport_status_mismatch")
        if self.ok:
            if not self.response_started or self.response_digest is None: raise ContractError("success_evidence_missing")
            _hex(self.response_digest,"response_digest",HEX64)
        elif self.response_digest is not None: raise ContractError("failure_digest_forbidden")
        if (self.input_tokens is None)!=(self.output_tokens is None): raise ContractError("partial_usage")
        if self.input_tokens is not None: integer(self.input_tokens,"input_tokens",0); integer(self.output_tokens,"output_tokens",0)
    @classmethod
    def success(cls,*,response_digest,input_tokens,output_tokens): return cls(True,200,"success",True,response_digest,input_tokens,output_tokens)
    @classmethod
    def failure(cls,status_code,category,*,response_started,input_tokens=None,output_tokens=None): return cls(False,status_code,category,response_started,None,input_tokens,output_tokens)

class InMemoryRotationStore:
    """Reference durable-state semantics; production is migration 027's PostgreSQL API."""
    def __init__(self): self._lock=threading.Lock(); self._authority={}; self._state={}; self._claims={}; self._quarantine={}; self._results={}; self._operations={}
    def authorize(self,grant):
        if not isinstance(grant,RotationAuthorityGrant): raise ContractError("authoritative_grant_required")
        self._authority[(grant.task_id,grant.run_id,grant.attempt_id,grant.reservation_id)]=grant
    def _grant(self,binding):
        grant=self._authority.get((binding.task_id,binding.run_id,binding.attempt_id,binding.budget_reservation_id))
        if grant is None or (grant.tenant_digest,grant.repository_id,grant.fence,grant.budget_digest)!=(canonical_digest(binding.repository_id),binding.repository_id,binding.fence,binding.budget_digest): raise ContractError("authority_not_granted")
        if binding.tenant_id!=binding.repository_id or binding.remaining_token_units>grant.token_capacity or binding.remaining_request_units>grant.request_capacity: raise ContractError("authority_not_granted")
        return grant
    def claim(self,binding,registry_digest,requested_cursor,requested_digest,now):
        with self._lock:
            grant=self._grant(binding); digest=binding.binding_digest
            if registry_digest!=binding.registry_digest: raise ContractError("authority_not_granted")
            operation=canonical_digest(binding.operation_id); prior=self._operations.get(operation)
            if prior is not None and prior!=digest: raise ContractError("idempotency_conflict")
            self._operations[operation]=digest
            if digest in self._results: return {"replay":self._results[digest]}
            key=(grant.tenant_digest,registry_digest); state=self._state.get(key)
            if state is None: state={"cooldowns":{},"cursor":requested_cursor,"requested_digest":requested_digest,"version":0,"quarantined":False,"held_token":0,"settled_token":0,"held_request":0,"settled_request":0}; self._state[key]=state
            if state["quarantined"]: raise ContractError("reconciliation_required")
            if state["cursor"]!=requested_cursor or state["requested_digest"]!=requested_digest: raise ContractError("requested_cursor_mismatch")
            active=next((c for c in self._claims.values() if c["key"]==key),None)
            if active:
                if active["expires_at"]>now: raise ContractError("operation_already_claimed")
                state["quarantined"]=True; raise ContractError("reconciliation_required")
            token=canonical_digest({"binding":digest,"version":state["version"],"now":now}); self._claims[digest]={"token":token,"key":key,"version":state["version"],"expires_at":now+30,"reserved_token":0,"reserved_request":0,"grant":grant}
            return {"replay":None,"claim_token":token,"cooldowns":dict(state["cooldowns"]),"cursor":state["cursor"],"version":state["version"]}
    def reserve_dispatch(self,binding_digest,claim_token,quota_mode,token_units):
        with self._lock:
            claim=self._claims.get(binding_digest)
            if claim is None or claim["token"]!=claim_token: raise ContractError("stale_rotation_claim")
            grant=claim["grant"]
            state=self._state[claim["key"]]
            if quota_mode=="token":
                if state["held_token"]+state["settled_token"]+token_units>grant.token_capacity: return False
                claim["reserved_token"]+=token_units; state["held_token"]+=token_units
            else:
                if state["held_request"]+state["settled_request"]+1>grant.request_capacity: return False
                claim["reserved_request"]+=1; state["held_request"]+=1
            return True
    def quarantine(self,binding_digest,claim_token,evidence):
        with self._lock:
            claim=self._claims.get(binding_digest)
            if claim is None or claim["token"]!=claim_token: raise ContractError("stale_rotation_claim")
            self._state[claim["key"]]["quarantined"]=True; self._results[binding_digest]=evidence; self._quarantine[binding_digest]=claim; del self._claims[binding_digest]
    def reconcile(self,tenant_digest,registry_digest,*,settle=False):
        with self._lock:
            key=(tenant_digest,registry_digest); state=self._state[key]
            for digest,claim in list(self._quarantine.items()):
                if claim["key"]!=key: continue
                state["held_token"]-=claim["reserved_token"]; state["held_request"]-=claim["reserved_request"]
                if settle: state["settled_token"]+=claim["reserved_token"]; state["settled_request"]+=claim["reserved_request"]
                del self._quarantine[digest]
            state["quarantined"]=False
    def finish(self,binding_digest,claim_token,evidence,cooldowns,cursor,version):
        with self._lock:
            claim=self._claims.get(binding_digest)
            if claim is None or claim["token"]!=claim_token or claim["version"]!=version: raise ContractError("stale_rotation_claim")
            state=self._state[claim["key"]]
            if state["version"]!=version: raise ContractError("state_version_conflict")
            state["held_token"]-=claim["reserved_token"]; state["settled_token"]+=claim["reserved_token"]
            state["held_request"]-=claim["reserved_request"]; state["settled_request"]+=claim["reserved_request"]
            state.update(cooldowns=dict(cooldowns),cursor=cursor,requested_digest=evidence["next_model_digest"],version=version+1); self._results[binding_digest]=evidence; del self._claims[binding_digest]

class PostgresRotationStore:
    """Runtime adapter for migration 027's transaction/fence/budget authority API."""
    def __init__(self,database_url):
        if not isinstance(database_url,str) or not database_url: raise ContractError("database_url_required")
        self._database_url=database_url
    def claim(self,binding,registry_digest,requested_cursor,requested_digest,now):
        import json, psycopg
        with psycopg.connect(self._database_url) as connection, connection.transaction(), connection.cursor() as cursor:
            wire=canonical_json(binding.to_dict()).decode()
            cursor.execute("SELECT factory.model_rotator_claim_v1(%s::jsonb,%s,%s,%s,%s,%s,%s)",(wire,wire,binding.binding_digest,registry_digest,requested_cursor,requested_digest,now))
            value=cursor.fetchone()[0]
            if value.get("error"): raise ContractError(value["error"])
            return value
    def reserve_dispatch(self,binding_digest,claim_token,quota_mode,token_units):
        import psycopg
        with psycopg.connect(self._database_url) as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SELECT factory.model_rotator_reserve_v1(%s,%s,%s,%s)",(binding_digest,claim_token,quota_mode,token_units)); return cursor.fetchone()[0]
    def quarantine(self,binding_digest,claim_token,evidence):
        import json, psycopg
        with psycopg.connect(self._database_url) as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SELECT factory.model_rotator_quarantine_v1(%s,%s,%s::jsonb)",(binding_digest,claim_token,json.dumps(evidence)))
            if cursor.fetchone()[0] is not True: raise ContractError("stale_rotation_claim")
    def reconcile(self,binding_digest,*,settle=False):
        import psycopg
        with psycopg.connect(self._database_url) as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SELECT factory.model_rotator_reconcile_v1(%s,%s)",(binding_digest,"settle" if settle else "release"))
            if cursor.fetchone()[0] is not True: raise ContractError("reconciliation_failed")
    def finish(self,binding_digest,claim_token,evidence,cooldowns,cursor_value,version):
        import json, psycopg
        with psycopg.connect(self._database_url) as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SELECT factory.model_rotator_finish_v1(%s,%s,%s::jsonb,%s::jsonb,%s,%s)",
                (binding_digest,claim_token,json.dumps(evidence),json.dumps(cooldowns),cursor_value,version))
            if cursor.fetchone()[0] is not True: raise ContractError("stale_rotation_claim")

class ModelRotator:
    def __init__(self,registry,store,*,enabled=False):
        if not isinstance(registry,ProviderRegistryV1): raise ContractError("registry_required")
        if store is None: raise ContractError("store_required")
        if type(enabled) is not bool: raise ContractError("invalid_enabled")
        self.registry,self.store,self.enabled=registry,store,enabled
    def _ordered(self,binding,cursor=0):
        enabled=tuple(m for m in self.registry.models if m.enabled); wanted=(binding.requested_provider_id,binding.requested_model_id)
        if wanted not in [(m.provider_id,m.model_id) for m in enabled]: raise ContractError("requested_model_unregistered")
        start=cursor%len(enabled); return enabled[start:]+enabled[:start]
    def _validate(self,binding):
        if not isinstance(binding,RotationBindingV1) or binding.registry_digest!=self.registry.registry_digest: raise ContractError("registry_binding_mismatch")
    def select(self,binding,cooldowns,*,now,cursor=0):
        self._validate(binding); integer(now,"now",0)
        for m in self._ordered(binding,cursor):
            until=cooldowns.get(f"{m.provider_id}/{m.model_id}",0); integer(until,"cooldown_until",0)
            if now>=until:return m.provider_id,m.model_id
        return None
    def execute(self,binding,transport,*,now):
        if not self.enabled: raise ContractError("rotator_disabled")
        self._validate(binding)
        enabled=tuple(m for m in self.registry.models if m.enabled); requested=(binding.requested_provider_id,binding.requested_model_id)
        positions=[(m.provider_id,m.model_id) for m in enabled]
        if requested not in positions: raise ContractError("requested_model_unregistered")
        requested_cursor=positions.index(requested); requested_digest=canonical_digest({"provider_id":requested[0],"model_id":requested[1]})
        claim=self.store.claim(binding,self.registry.registry_digest,requested_cursor,requested_digest,now)
        if claim.get("replay") is not None:return claim["replay"]
        cooldowns=claim["cooldowns"]; cursor=claim["cursor"]; version=claim["version"]; attempts=[]; known=unknown=0; status="exhausted"; selected=None; next_cursor=cursor; ambiguous=False
        for m in self._ordered(binding,cursor):
            if len(attempts)>=self.registry.policy.max_attempts: break
            key=f"{m.provider_id}/{m.model_id}"
            if now<cooldowns.get(key,0): continue
            reserve_units=self.registry.policy.per_attempt_token_limit if m.quota_mode=="token" else 1
            if not self.store.reserve_dispatch(binding.binding_digest,claim["claim_token"],m.quota_mode,reserve_units): status="stopped"; break
            try:
                result=transport(m.provider_id,m.model_id,self.registry.policy.per_attempt_token_limit)
                if not isinstance(result,TransportResult): raise ContractError("invalid_transport_result")
            except Exception:
                result=TransportResult.failure(503,"transport",response_started=True)
                ambiguous=True
            used=None if result.input_tokens is None else result.input_tokens+result.output_tokens
            overrun=m.quota_mode=="token" and used is not None and used>self.registry.policy.per_attempt_token_limit
            if used is None: unknown+=1
            else: known+=used
            if not result.ok and result.category in _RETRYABLE and not result.response_started: cooldowns[key]=now+self.registry.policy.max_cooldown_seconds
            attempts.append({"ordinal":len(attempts)+1,"provider_id":m.provider_id,"model_id":m.model_id,"binding_digest":binding.binding_digest,"status_code":result.status_code,"category":result.category,"response_started":result.response_started,"response_digest":result.response_digest,"usage_input_units":result.input_tokens,"usage_output_units":result.output_tokens,"budget_overrun":overrun,"cooldown_until":cooldowns.get(key)})
            if overrun or used is None or (result.response_started and not result.ok): status="needs_human"; ambiguous=True; break
            if result.ok: status="selected"; selected={"provider_id":m.provider_id,"model_id":m.model_id}; next_cursor=(self.registry.models.index(m)+1)%len(self.registry.models); break
            if result.status_code in {401,402} or result.category in _TERMINAL: status="stopped"; break
        public={"tenant_digest":canonical_digest(binding.tenant_id),"repository_digest":canonical_digest(binding.repository_id),"task_digest":canonical_digest(binding.task_id),"run_digest":canonical_digest(binding.run_id),"attempt_digest":canonical_digest(binding.attempt_id),"fence":binding.fence,"budget_reservation_digest":canonical_digest(binding.budget_reservation_id),"budget_digest":binding.budget_digest,"operation_digest":canonical_digest(binding.operation_id)}
        next_model=enabled[next_cursor%len(enabled)]
        evidence={"schema_version":1,"registry_digest":self.registry.registry_digest,"binding":public,"status":status,"selected":selected,"attempts":attempts,"usage":{"known_tokens":known,"unknown_attempts":unknown,"complete":unknown==0 and status!="needs_human"},"cost_usd":None,"authority_effect":"none","credentials_persisted":False,"live_qualification":"NOT_RUN","state_version":version,"next_model_digest":canonical_digest({"provider_id":next_model.provider_id,"model_id":next_model.model_id})}
        evidence["evidence_digest"]=canonical_digest(evidence)
        if ambiguous:self.store.quarantine(binding.binding_digest,claim["claim_token"],evidence)
        else:self.store.finish(binding.binding_digest,claim["claim_token"],evidence,cooldowns,next_cursor,version)
        return evidence
