"""Durable, authority-bound model rotation; no credential or host-settings access."""
from __future__ import annotations
from dataclasses import dataclass
import re, threading
from typing import Mapping
from .contracts import ContractError, HEX40, HEX64, _hex, _id, _text, _time, canonical_digest
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
    max_attempts:int; max_cooldown_seconds:int; token_quota:int; per_attempt_token_limit:int
    def to_dict(self): return dict(max_attempts=self.max_attempts,max_cooldown_seconds=self.max_cooldown_seconds,token_quota=self.token_quota,per_attempt_token_limit=self.per_attempt_token_limit)
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
        raw=data["policy"]; _closed(raw,{"max_attempts","max_cooldown_seconds","token_quota","per_attempt_token_limit"})
        policy=RotationPolicy(integer(raw["max_attempts"],"max_attempts",1,64),integer(raw["max_cooldown_seconds"],"cooldown",1,86400),integer(raw["token_quota"],"quota",1,10_000_000),integer(raw["per_attempt_token_limit"],"attempt_limit",1,1_000_000))
        if policy.per_attempt_token_limit>policy.token_quota: raise ContractError("invalid_token_policy")
        return cls(1,data["registry_id"],data["registry_version"],dict(p),tuple(models),policy)
    def to_dict(self): return {"schema_version":1,"registry_id":self.registry_id,"registry_version":self.registry_version,"provenance":dict(self.provenance),"models":[m.to_dict() for m in self.models],"policy":self.policy.to_dict()}
    @property
    def registry_digest(self): return canonical_digest(self.to_dict())
@dataclass(frozen=True)
class RotationBindingV1:
    schema_version:int; tenant_id:str; repository_id:str; task_id:str; run_id:str; attempt_id:str; fence:int; budget_reservation_id:str; budget_digest:str; registry_digest:str; operation_id:str; requested_provider_id:str; requested_model_id:str; remaining_token_units:int
    @classmethod
    def from_dict(cls,data):
        _closed(data,set(cls.__dataclass_fields__))
        if data["schema_version"]!=1: raise ContractError("unsupported_version")
        for name in ("tenant_id","repository_id","task_id","run_id","attempt_id","budget_reservation_id","operation_id","requested_provider_id","requested_model_id"): _opaque(data[name],name)
        integer(data["fence"],"fence",1); integer(data["remaining_token_units"],"remaining",0); _hex(data["budget_digest"],"budget_digest",HEX64); _hex(data["registry_digest"],"registry_digest",HEX64)
        return cls(**data)
    def to_dict(self): return {name:getattr(self,name) for name in self.__dataclass_fields__}
    @property
    def binding_digest(self): return canonical_digest(self.to_dict())
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
    def __init__(self): self._lock=threading.Lock(); self._authority={}; self._state={}; self._claims={}; self._results={}; self._operations={}
    def authorize(self,binding): self._authority[binding.binding_digest]=binding.remaining_token_units
    def claim(self,binding,registry_digest,now):
        with self._lock:
            digest=binding.binding_digest
            if self._authority.get(digest)!=binding.remaining_token_units or registry_digest!=binding.registry_digest: raise ContractError("authority_not_granted")
            operation=canonical_digest(binding.operation_id); prior=self._operations.get(operation)
            if prior is not None and prior!=digest: raise ContractError("idempotency_conflict")
            self._operations[operation]=digest
            if digest in self._results: return {"replay":self._results[digest]}
            if digest in self._claims: raise ContractError("operation_already_claimed")
            token=canonical_digest({"binding":digest,"now":now}); self._claims[digest]=token
            key=(canonical_digest(binding.tenant_id),registry_digest); state=self._state.get(key,{"cooldowns":{},"cursor":0})
            return {"replay":None,"claim_token":token,"cooldowns":dict(state["cooldowns"]),"cursor":state["cursor"]}
    def finish(self,binding_digest,claim_token,evidence,cooldowns,cursor):
        with self._lock:
            if self._claims.get(binding_digest)!=claim_token: raise ContractError("stale_rotation_claim")
            key=(evidence["binding"]["tenant_digest"],evidence["registry_digest"]); self._state[key]={"cooldowns":dict(cooldowns),"cursor":cursor}; self._results[binding_digest]=evidence; del self._claims[binding_digest]

class PostgresRotationStore:
    """Runtime adapter for migration 027's transaction/fence/budget authority API."""
    def __init__(self,database_url):
        if not isinstance(database_url,str) or not database_url: raise ContractError("database_url_required")
        self._database_url=database_url
    def claim(self,binding,registry_digest,now):
        import json, psycopg
        with psycopg.connect(self._database_url) as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SELECT factory.model_rotator_claim_v1(%s::jsonb,%s,%s,%s)",(json.dumps(binding.to_dict()),binding.binding_digest,registry_digest,now))
            value=cursor.fetchone()[0]
            if value.get("error"): raise ContractError(value["error"])
            return value
    def finish(self,binding_digest,claim_token,evidence,cooldowns,cursor_value):
        import json, psycopg
        with psycopg.connect(self._database_url) as connection, connection.transaction(), connection.cursor() as cursor:
            cursor.execute("SELECT factory.model_rotator_finish_v1(%s,%s,%s::jsonb,%s::jsonb,%s)",
                (binding_digest,claim_token,json.dumps(evidence),json.dumps(cooldowns),cursor_value))
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
        if binding.remaining_token_units<self.registry.policy.per_attempt_token_limit: raise ContractError("reserved_budget_insufficient")
    def select(self,binding,cooldowns,*,now,cursor=0):
        self._validate(binding); integer(now,"now",0)
        for m in self._ordered(binding,cursor):
            until=cooldowns.get(f"{m.provider_id}/{m.model_id}",0); integer(until,"cooldown_until",0)
            if now>=until:return m.provider_id,m.model_id
        return None
    def execute(self,binding,transport,*,now):
        if not self.enabled: raise ContractError("rotator_disabled")
        self._validate(binding); claim=self.store.claim(binding,self.registry.registry_digest,now)
        if claim.get("replay") is not None:return claim["replay"]
        cooldowns=claim["cooldowns"]; cursor=claim["cursor"]; attempts=[]; known=unknown=0; status="exhausted"; selected=None; next_cursor=cursor
        for m in self._ordered(binding,cursor):
            if len(attempts)>=self.registry.policy.max_attempts: break
            key=f"{m.provider_id}/{m.model_id}"
            if now<cooldowns.get(key,0): continue
            ceiling=min(binding.remaining_token_units,self.registry.policy.token_quota)
            if known+self.registry.policy.per_attempt_token_limit>ceiling: status="stopped"; break
            result=transport(m.provider_id,m.model_id,self.registry.policy.per_attempt_token_limit)
            if not isinstance(result,TransportResult): raise ContractError("invalid_transport_result")
            used=None if result.input_tokens is None else result.input_tokens+result.output_tokens
            overrun=used is not None and (used>self.registry.policy.per_attempt_token_limit or known+used>ceiling)
            if used is None: unknown+=1
            else: known+=used
            if not result.ok and result.category in _RETRYABLE and not result.response_started: cooldowns[key]=now+self.registry.policy.max_cooldown_seconds
            attempts.append({"ordinal":len(attempts)+1,"provider_id":m.provider_id,"model_id":m.model_id,"binding_digest":binding.binding_digest,"status_code":result.status_code,"category":result.category,"response_started":result.response_started,"response_digest":result.response_digest,"usage_input_units":result.input_tokens,"usage_output_units":result.output_tokens,"budget_overrun":overrun,"cooldown_until":cooldowns.get(key)})
            if overrun or used is None or (result.response_started and not result.ok): status="needs_human"; break
            if result.ok: status="selected"; selected={"provider_id":m.provider_id,"model_id":m.model_id}; next_cursor=(self.registry.models.index(m)+1)%len(self.registry.models); break
            if result.status_code in {401,402} or result.category in _TERMINAL: status="stopped"; break
        public={"tenant_digest":canonical_digest(binding.tenant_id),"repository_digest":canonical_digest(binding.repository_id),"task_digest":canonical_digest(binding.task_id),"run_digest":canonical_digest(binding.run_id),"attempt_digest":canonical_digest(binding.attempt_id),"fence":binding.fence,"budget_reservation_digest":canonical_digest(binding.budget_reservation_id),"budget_digest":binding.budget_digest,"operation_digest":canonical_digest(binding.operation_id)}
        evidence={"schema_version":1,"registry_digest":self.registry.registry_digest,"binding":public,"status":status,"selected":selected,"attempts":attempts,"usage":{"known_tokens":known,"unknown_attempts":unknown,"complete":unknown==0 and status!="needs_human"},"cost_usd":None,"authority_effect":"none","credentials_persisted":False,"live_qualification":"NOT_RUN"}
        evidence["evidence_digest"]=canonical_digest(evidence); self.store.finish(binding.binding_digest,claim["claim_token"],evidence,cooldowns,next_cursor); return evidence
