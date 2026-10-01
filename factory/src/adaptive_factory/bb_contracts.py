"""BB-01 admission boundary; no external backend is qualified or enabled here."""

from .contracts import ContractError, canonical_digest
from .v15_contracts import FrozenWire, closed, digest, identity, integer, sequence, sha, version


_CAPABILITIES = frozenset(
    {"observe", "pause", "resume", "cancel", "pre_model_interception"}
)
_OUTCOMES = frozenset({"unknown", "observed", "rejected", "unavailable"})


class BBBackendProfileV1(FrozenWire):
    """A bounded, explicitly disabled profile pending a separate live qualification."""

    @classmethod
    def from_dict(cls, data):
        closed(
            data,
            (
                "schema_version",
                "profile_id",
                "enabled",
                "source_commit",
                "binary_digest",
                "workflows_digest",
                "orchestra_digest",
                "capabilities",
                "max_agents",
                "max_depth",
                "max_cost_usd_micros",
                "wall_seconds",
                "lease_seconds",
                "stop_seconds",
            ),
        )
        version(data)
        identity(data["profile_id"])
        if data["enabled"] is not False:
            raise ContractError("bb_live_profile_unqualified")
        if data["source_commit"] is not None:
            sha(data["source_commit"])
        for key in ("binary_digest", "workflows_digest", "orchestra_digest"):
            if data[key] is not None:
                digest(data[key])
        capabilities = sequence(data["capabilities"], 16)
        if any(type(capability) is not str for capability in capabilities):
            raise ContractError("invalid_capability")
        if len(set(capabilities)) != len(capabilities):
            raise ContractError("duplicate_capability")
        if any(capability not in _CAPABILITIES for capability in capabilities):
            raise ContractError("unknown_capability")
        for key in (
            "max_agents",
            "max_depth",
            "max_cost_usd_micros",
            "wall_seconds",
            "lease_seconds",
            "stop_seconds",
        ):
            integer(data[key], key, 1, 1_000_000_000)
        if (
            data["lease_seconds"] > data["wall_seconds"]
            or data["stop_seconds"] > data["lease_seconds"]
        ):
            raise ContractError("invalid_deadlines")
        return cls.freeze(data)


def select_backend(profile):
    """Preserve the qualified native route; this contract grants no BB authority."""

    BBBackendProfileV1.from_dict(profile.to_dict())
    return {
        "backend": "native",
        "bb_qualification": "not_run",
        "authority_effect": "none",
    }


class BBLifecycleObservationV1(FrozenWire):
    """Immutable observation of command acknowledgement and separately proven effects."""

    _BINDING_FIELDS = (
        "repository_id",
        "task_id",
        "run_id",
        "attempt_id",
        "fence",
        "context_digest",
        "policy_digest",
        "operation_id",
        "command_digest",
    )
    _OPERATION_FIELDS = _BINDING_FIELDS[:-1]

    @classmethod
    def from_dict(cls, data):
        closed(
            data,
            (
                "schema_version",
                "repository_id",
                "task_id",
                "run_id",
                "attempt_id",
                "fence",
                "context_digest",
                "policy_digest",
                "operation_id",
                "command_digest",
                "acknowledged",
                "effect_outcome",
                "stop_outcome",
                "evidence_digest",
            ),
        )
        version(data)
        for key in ("repository_id", "task_id", "run_id", "attempt_id", "operation_id"):
            identity(data[key])
        integer(data["fence"], "fence", 1)
        for key in ("context_digest", "policy_digest", "command_digest"):
            digest(data[key])
        if type(data["acknowledged"]) is not bool:
            raise ContractError("invalid_acknowledgement")
        for key in ("effect_outcome", "stop_outcome"):
            if type(data[key]) is not str or data[key] not in _OUTCOMES:
                raise ContractError("invalid_observation")
        if data["evidence_digest"] is not None:
            digest(data["evidence_digest"])
        if (
            "observed" in (data["effect_outcome"], data["stop_outcome"])
            and data["evidence_digest"] is None
        ):
            raise ContractError("effect_evidence_missing")
        return cls.freeze(data)

    @property
    def operation_key(self):
        data = self.to_dict()
        return canonical_digest({key: data[key] for key in self._OPERATION_FIELDS})

    @property
    def request_digest(self):
        data = self.to_dict()
        return canonical_digest(
            {
                "operation_key": self.operation_key,
                "command_digest": data["command_digest"],
            }
        )

    def validate_binding(
        self,
        *,
        repository_id,
        task_id,
        run_id,
        attempt_id,
        fence,
        context_digest,
        policy_digest,
        operation_id,
        command_digest,
    ):
        expected = {
            "repository_id": repository_id,
            "task_id": task_id,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "fence": fence,
            "context_digest": context_digest,
            "policy_digest": policy_digest,
            "operation_id": operation_id,
            "command_digest": command_digest,
        }
        data = self.to_dict()
        if any(data[key] != expected[key] for key in self._BINDING_FIELDS):
            raise ContractError("bb_identity_mismatch")

    def validate_replay(self, other):
        try:
            other = BBLifecycleObservationV1.from_dict(other.to_dict())
        except (AttributeError, ContractError, TypeError, ValueError) as exc:
            raise ContractError("bb_idempotency_conflict") from exc
        if self.operation_key != other.operation_key or self.request_digest != other.request_digest:
            raise ContractError("bb_idempotency_conflict")
        if self.record_digest != other.record_digest:
            raise ContractError("bb_replay_body_conflict")
