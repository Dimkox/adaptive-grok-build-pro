"""Versioned, bounded facts about one completed local provider operation."""

from dataclasses import dataclass

from .landing_contracts import (
    LandingContractError, LandingProviderEvidence, decode_provider_evidence, landing_digest,
)


CATEGORIES = frozenset({
    "normalized", "authentication", "rate_limit", "unavailable", "transport", "deadline",
    "policy", "permission", "accounting", "protocol", "draft", "input", "configuration", "unknown",
})
FALLBACK_CATEGORIES = frozenset({"authentication", "rate_limit", "unavailable", "transport", "deadline"})


@dataclass(frozen=True)
class LandingProviderObservation:
    evidence: LandingProviderEvidence
    category: str
    dispatched: bool
    usage_status: str
    usage_input_units: int | None
    usage_output_units: int | None
    http_status: int | None = None

    def __post_init__(self):
        if not isinstance(self.category, str) or self.category not in CATEGORIES or type(self.dispatched) is not bool:
            raise LandingContractError("provider_observation")
        if self.http_status is not None and (type(self.http_status) is not int or not 100 <= self.http_status <= 599):
            raise LandingContractError("provider_observation")
        counts = (self.usage_input_units, self.usage_output_units)
        if self.usage_status == "reported":
            if not self.dispatched or any(type(value) is not int or not 0 <= value <= 10_000_000 for value in counts):
                raise LandingContractError("provider_observation_usage")
        elif self.usage_status == "not_dispatched":
            if self.dispatched or counts != (0, 0):
                raise LandingContractError("provider_observation_usage")
        elif self.usage_status != "unavailable" or not self.dispatched or counts != (None, None):
            raise LandingContractError("provider_observation_usage")
        if self.category == "normalized" and self.usage_status != "reported":
            raise LandingContractError("provider_observation_usage")
        # Keep the original evidence contract and validate its independent digest.
        decode_provider_evidence(self.evidence.to_dict())

    def to_dict(self):
        facts = {
            "schema_version": 1, "evidence": self.evidence.to_dict(),
            "category": self.category, "dispatched": self.dispatched,
            "usage_status": self.usage_status, "usage_input_units": self.usage_input_units,
            "usage_output_units": self.usage_output_units, "http_status": self.http_status,
        }
        return {**facts, "observation_digest": landing_digest("provider-observation-v1", facts)}

    @classmethod
    def from_dict(cls, value):
        keys = {"schema_version", "evidence", "category", "dispatched", "usage_status",
                "usage_input_units", "usage_output_units", "http_status", "observation_digest"}
        if not isinstance(value, dict) or set(value) != keys or type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise LandingContractError("provider_observation")
        observation = cls(
            decode_provider_evidence(value["evidence"]), value["category"], value["dispatched"],
            value["usage_status"], value["usage_input_units"], value["usage_output_units"], value["http_status"],
        )
        if observation.to_dict() != value:
            raise LandingContractError("provider_observation_digest")
        return observation
