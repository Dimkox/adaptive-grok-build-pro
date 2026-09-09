"""Thin M8 bridge over the canonical M7 producer contracts.

The envelope owns only the provider mapping. M7 bundles, cohort data, aggregate,
and evaluation remain producer-owned and are parsed or recomputed locally.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
from typing import Any, ClassVar, Mapping

from .contracts import ContractError, HEX64, _closed, _hex, canonical_json
from .shadow_contracts import ReadyForPrBundleV1, ShadowCohortV1
from .shadow_evaluation import (
    ShadowCohortAggregateV1,
    ShadowEvaluationV1,
    aggregate_shadow_cohort,
    evaluate_shadow_cohort,
)


MAX_ITEMS = 10_000


def _object(data: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(data, Mapping) or any(not isinstance(key, str) for key in data):
        raise ContractError("invalid_contract", name)
    return data


def _field_names(contract: type[Any]) -> set[str]:
    return {field.name for field in fields(contract)}


def _version(value: Any, name: str) -> int:
    if type(value) is not int or value != 1:
        raise ContractError("unsupported_version", name)
    return 1


def _domain_digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class M7ProviderMappingV1:
    schema_version: int
    cohort_key_digest: str
    validator_digest: str
    provider_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-m7-provider-mapping/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "provider_mapping")
        for name in ("cohort_key_digest", "validator_digest", "provider_digest"):
            _hex(getattr(self, name), name, HEX64)
        if self.provider_digest == self.validator_digest:
            raise ContractError("provider_mapping_mismatch", "provider_validator_separation")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M7ProviderMappingV1":
        data = _object(data, "provider_mapping")
        _closed(data, _field_names(cls))
        return cls(
            _version(data["schema_version"], "provider_mapping"),
            _hex(data["cohort_key_digest"], "cohort_key_digest", HEX64),
            _hex(data["validator_digest"], "validator_digest", HEX64),
            _hex(data["provider_digest"], "provider_digest", HEX64),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "cohort_key_digest": self.cohort_key_digest,
            "validator_digest": self.validator_digest,
            "provider_digest": self.provider_digest,
        }

    @property
    def digest(self) -> str:
        return _domain_digest(self.DOMAIN, self.to_dict())


@dataclass(frozen=True)
class M7AutonomyBridgeV1:
    schema_version: int
    provider_mapping: M7ProviderMappingV1
    bundles: tuple[ReadyForPrBundleV1, ...]
    cohort: ShadowCohortV1

    DOMAIN: ClassVar[str] = "adaptive-factory.m8-m7-autonomy-bridge/v1"

    def __post_init__(self) -> None:
        _version(self.schema_version, "m7_autonomy_bridge")
        if not isinstance(self.provider_mapping, M7ProviderMappingV1):
            raise ContractError("invalid_contract", "provider_mapping")
        if not isinstance(self.bundles, tuple) or not 1 <= len(self.bundles) <= MAX_ITEMS:
            raise ContractError("invalid_contract", "bundles")
        if any(not isinstance(bundle, ReadyForPrBundleV1) for bundle in self.bundles):
            raise ContractError("invalid_contract", "bundles")
        if not isinstance(self.cohort, ShadowCohortV1):
            raise ContractError("invalid_contract", "cohort")

        # Reparse producer bodies even on direct construction so callers cannot
        # smuggle a modified frozen object into the M8 envelope.
        reparsed_bundles = tuple(
            ReadyForPrBundleV1.from_dict(bundle.to_dict()) for bundle in self.bundles
        )
        reparsed_cohort = ShadowCohortV1.from_dict(self.cohort.to_dict())
        reparsed_mapping = M7ProviderMappingV1.from_dict(self.provider_mapping.to_dict())
        if reparsed_bundles != self.bundles or reparsed_cohort != self.cohort:
            raise ContractError("invalid_contract", "producer_snapshot")
        if reparsed_mapping != self.provider_mapping:
            raise ContractError("invalid_contract", "provider_mapping")

        bundle_digests = tuple(bundle.bundle_digest for bundle in self.bundles)
        if bundle_digests != tuple(sorted(bundle_digests)):
            raise ContractError("invalid_order", "bundles")
        if len(set(bundle_digests)) != len(bundle_digests):
            raise ContractError("replay", "bundle_digest")
        outcome_bundle_digests = tuple(
            sorted(outcome.bundle_digest for outcome in self.cohort.outcomes)
        )
        if bundle_digests != outcome_bundle_digests:
            raise ContractError("m7_outcome_mismatch", "bundle_digest")

        key = self.cohort.key
        if (
            self.provider_mapping.cohort_key_digest != key.digest
            or self.provider_mapping.validator_digest != key.validator_digest
            or self.provider_mapping.provider_digest == key.validator_digest
        ):
            raise ContractError("provider_mapping_mismatch")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "M7AutonomyBridgeV1":
        data = _object(data, "m7_autonomy_bridge")
        _closed(data, _field_names(cls))
        bundles = data["bundles"]
        if not isinstance(bundles, list) or not 1 <= len(bundles) <= MAX_ITEMS:
            raise ContractError("invalid_contract", "bundles")
        return cls(
            _version(data["schema_version"], "m7_autonomy_bridge"),
            M7ProviderMappingV1.from_dict(data["provider_mapping"]),
            tuple(ReadyForPrBundleV1.from_dict(bundle) for bundle in bundles),
            ShadowCohortV1.from_dict(data["cohort"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_mapping": self.provider_mapping.to_dict(),
            "bundles": [bundle.to_dict() for bundle in self.bundles],
            "cohort": self.cohort.to_dict(),
        }

    @property
    def aggregate(self) -> ShadowCohortAggregateV1:
        return aggregate_shadow_cohort(self.cohort)

    @property
    def evaluation(self) -> ShadowEvaluationV1:
        return evaluate_shadow_cohort(self.cohort)

    @property
    def external_acceptance_available(self) -> bool:
        return False

    @property
    def currentness_available(self) -> bool:
        return False

    @property
    def digest(self) -> str:
        return _domain_digest(self.DOMAIN, self.to_dict())
