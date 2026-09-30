"""Bounded model-rotation observations; no credential or host-settings access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .contracts import ContractError, HEX40, HEX64, _hex, _id, _text, _time, canonical_digest
from .v15_contracts import integer


_PROVIDERS = frozenset({"openrouter", "qwen"})
_RETRYABLE = frozenset({"rate_limit", "transport", "deadline", "unavailable"})
_TERMINAL = frozenset({"authentication", "payment", "daily_limit", "permission", "policy",
                       "protocol", "accounting", "input", "configuration"})


def _closed(value: Mapping, fields: set[str]) -> None:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ContractError("closed_object_required")


@dataclass(frozen=True)
class ModelEntry:
    provider_id: str
    model_id: str
    free_claim: bool
    enabled: bool
    priority: int

    def to_dict(self) -> dict:
        return dict(provider_id=self.provider_id, model_id=self.model_id,
                    free_claim=self.free_claim, enabled=self.enabled, priority=self.priority)


@dataclass(frozen=True)
class RotationPolicy:
    max_attempts: int
    max_cooldown_seconds: int
    token_quota: int
    per_attempt_token_limit: int

    def to_dict(self) -> dict:
        return dict(max_attempts=self.max_attempts, max_cooldown_seconds=self.max_cooldown_seconds,
                    token_quota=self.token_quota, per_attempt_token_limit=self.per_attempt_token_limit)


@dataclass(frozen=True)
class ProviderRegistryV1:
    schema_version: int
    registry_id: str
    registry_version: str
    provenance: dict
    models: tuple[ModelEntry, ...]
    policy: RotationPolicy

    @classmethod
    def from_dict(cls, data: Mapping) -> "ProviderRegistryV1":
        _closed(data, {"schema_version", "registry_id", "registry_version", "provenance", "models", "policy"})
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version")
        _id(data["registry_id"], "registry_id")
        _text(data["registry_version"], "registry_version", 32)
        provenance = data["provenance"]
        _closed(provenance, {"repository", "commit", "observed_at"})
        _id(provenance["repository"], "repository")
        _hex(provenance["commit"], "provenance.commit", HEX40)
        _time(provenance["observed_at"], "provenance.observed_at")
        raw_models = data["models"]
        if not isinstance(raw_models, list) or not 1 <= len(raw_models) <= 64:
            raise ContractError("invalid_collection", "models")
        models = []
        identities = set()
        priorities = set()
        for raw in raw_models:
            _closed(raw, {"provider_id", "model_id", "free_claim", "enabled", "priority"})
            provider = _id(raw["provider_id"], "provider_id")
            model = _id(raw["model_id"], "model_id")
            if provider not in _PROVIDERS or raw["free_claim"] is not True or type(raw["enabled"]) is not bool:
                raise ContractError("ineligible_model")
            priority = integer(raw["priority"], "priority", 0, 1_000_000)
            if (provider, model) in identities or priority in priorities:
                raise ContractError("duplicate_model")
            identities.add((provider, model)); priorities.add(priority)
            models.append(ModelEntry(provider, model, True, raw["enabled"], priority))
        models.sort(key=lambda item: item.priority)
        raw_policy = data["policy"]
        _closed(raw_policy, {"max_attempts", "max_cooldown_seconds", "token_quota", "per_attempt_token_limit"})
        policy = RotationPolicy(
            integer(raw_policy["max_attempts"], "max_attempts", 1, 64),
            integer(raw_policy["max_cooldown_seconds"], "max_cooldown_seconds", 1, 86400),
            integer(raw_policy["token_quota"], "token_quota", 1, 10_000_000),
            integer(raw_policy["per_attempt_token_limit"], "per_attempt_token_limit", 1, 1_000_000),
        )
        if policy.per_attempt_token_limit > policy.token_quota:
            raise ContractError("invalid_token_policy")
        return cls(1, data["registry_id"], data["registry_version"], dict(provenance), tuple(models), policy)

    def to_dict(self) -> dict:
        return {"schema_version": 1, "registry_id": self.registry_id,
                "registry_version": self.registry_version, "provenance": dict(self.provenance),
                "models": [item.to_dict() for item in self.models], "policy": self.policy.to_dict()}

    @property
    def registry_digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class RotationBindingV1:
    schema_version: int
    tenant_id: str
    repository_id: str
    task_id: str
    run_id: str
    attempt_id: str
    fence: int
    budget_reservation_id: str
    budget_digest: str
    registry_digest: str
    operation_id: str
    requested_provider_id: str
    requested_model_id: str
    remaining_token_units: int

    @classmethod
    def from_dict(cls, data: Mapping) -> "RotationBindingV1":
        fields = set(cls.__dataclass_fields__)
        _closed(data, fields)
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version")
        for name in ("tenant_id", "repository_id", "task_id", "run_id", "attempt_id",
                     "budget_reservation_id", "operation_id", "requested_provider_id", "requested_model_id"):
            _id(data[name], name)
        integer(data["fence"], "fence", 1)
        integer(data["remaining_token_units"], "remaining_token_units", 0)
        _hex(data["budget_digest"], "budget_digest", HEX64)
        _hex(data["registry_digest"], "registry_digest", HEX64)
        return cls(**data)

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @property
    def binding_digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class TransportResult:
    ok: bool
    status_code: int
    category: str
    response_started: bool
    response_digest: str | None
    input_tokens: int | None
    output_tokens: int | None

    @classmethod
    def success(cls, *, response_digest: str, input_tokens: int | None,
                output_tokens: int | None) -> "TransportResult":
        _hex(response_digest, "response_digest", HEX64)
        return cls(True, 200, "success", True, response_digest, input_tokens, output_tokens)

    @classmethod
    def failure(cls, status_code: int, category: str, *, response_started: bool,
                input_tokens: int | None = None, output_tokens: int | None = None) -> "TransportResult":
        if category not in _RETRYABLE | _TERMINAL:
            raise ContractError("unknown_failure_category")
        return cls(False, integer(status_code, "status_code", 0, 599), category,
                   bool(response_started), None, input_tokens, output_tokens)

    def validate(self) -> None:
        if self.input_tokens is None or self.output_tokens is None:
            if self.input_tokens is not None or self.output_tokens is not None:
                raise ContractError("partial_usage")
        else:
            integer(self.input_tokens, "input_tokens", 0)
            integer(self.output_tokens, "output_tokens", 0)


class ModelRotator:
    """Caller-bound coordinator. The supplied transport remains the caller's network boundary."""

    def __init__(self, registry: ProviderRegistryV1, *, enabled: bool = False) -> None:
        if not isinstance(registry, ProviderRegistryV1):
            raise ContractError("registry_required")
        if type(enabled) is not bool:
            raise ContractError("invalid_enabled")
        self.registry = registry
        self.enabled = enabled

    def _ordered(self, binding: RotationBindingV1) -> tuple[ModelEntry, ...]:
        enabled = tuple(item for item in self.registry.models if item.enabled)
        requested = (binding.requested_provider_id, binding.requested_model_id)
        positions = [(item.provider_id, item.model_id) for item in enabled]
        if requested not in positions:
            raise ContractError("requested_model_unregistered")
        index = positions.index(requested)
        return enabled[index:] + enabled[:index]

    def _validate_binding(self, binding: RotationBindingV1) -> None:
        if not isinstance(binding, RotationBindingV1) or binding.registry_digest != self.registry.registry_digest:
            raise ContractError("registry_binding_mismatch")
        if binding.remaining_token_units < self.registry.policy.per_attempt_token_limit:
            raise ContractError("reserved_budget_insufficient")

    def select(self, binding: RotationBindingV1, cooldowns: Mapping[tuple[str, str], int], *, now: int):
        self._validate_binding(binding)
        integer(now, "now", 0)
        for item in self._ordered(binding):
            until = cooldowns.get((item.provider_id, item.model_id), 0)
            integer(until, "cooldown_until", 0)
            if now >= until:
                return item.provider_id, item.model_id
        return None

    def execute(self, binding: RotationBindingV1,
                transport: Callable[[str, str, int], TransportResult], *, now: int) -> dict:
        if not self.enabled:
            raise ContractError("rotator_disabled")
        self._validate_binding(binding)
        candidates = self._ordered(binding)
        attempts = []
        known_tokens = 0
        unknown = 0
        status = "exhausted"
        selected = None
        for item in candidates[:self.registry.policy.max_attempts]:
            if known_tokens + self.registry.policy.per_attempt_token_limit > min(
                    binding.remaining_token_units, self.registry.policy.token_quota):
                status = "stopped"
                break
            result = transport(item.provider_id, item.model_id, self.registry.policy.per_attempt_token_limit)
            if not isinstance(result, TransportResult):
                raise ContractError("invalid_transport_result")
            result.validate()
            complete = result.input_tokens is not None
            if complete:
                used = result.input_tokens + result.output_tokens
                known_tokens += used
            else:
                unknown += 1
            attempt = {
                "ordinal": len(attempts) + 1, "provider_id": item.provider_id,
                "model_id": item.model_id, "status_code": result.status_code,
                "binding_digest": binding.binding_digest,
                "category": result.category, "response_started": result.response_started,
                "response_digest": result.response_digest,
                "usage_input_units": result.input_tokens, "usage_output_units": result.output_tokens,
                "cooldown_until": now + self.registry.policy.max_cooldown_seconds
                    if not result.ok and result.category in _RETRYABLE and not result.response_started else None,
            }
            attempts.append(attempt)
            if unknown:
                status = "needs_human"
                break
            if result.ok:
                status = "selected"
                selected = {"provider_id": item.provider_id, "model_id": item.model_id}
                break
            if result.response_started:
                status = "needs_human"
                break
            if result.status_code in {401, 402} or result.category in _TERMINAL:
                status = "stopped"
                break
            if result.category not in _RETRYABLE:
                status = "stopped"
                break
        evidence = {
            "schema_version": 1, "registry_digest": self.registry.registry_digest,
            "binding": binding.to_dict(), "status": status, "selected": selected,
            "attempts": attempts,
            "usage": {"known_tokens": known_tokens, "unknown_attempts": unknown,
                      "complete": unknown == 0},
            "cost_usd": None, "authority_effect": "none", "credentials_persisted": False,
            "live_qualification": "NOT_RUN",
        }
        evidence["evidence_digest"] = canonical_digest(evidence)
        return evidence
