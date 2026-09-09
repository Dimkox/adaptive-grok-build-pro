"""Bounded in-memory dry-run sink with deliberately no external capability."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import ContractError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED_EFFECTS = frozenset(
    {"entered_stage", "changed_exposure", "halted", "restored"}
)


class AdapterBoundaryError(ContractError):
    """A requested in-memory effect crossed the source-only boundary."""


@dataclass(frozen=True, slots=True)
class AppliedDryRunEffect:
    effect: str
    promotion_digest: str
    artifact_digest: str
    environment: str
    exposure_basis_points: int


class FakeEnvironmentAdapter:
    """Record at most 128 nonproduction effects and do nothing else."""

    __slots__ = ("__effects",)

    supported_effects = _SUPPORTED_EFFECTS

    def __init__(self) -> None:
        object.__setattr__(self, "_FakeEnvironmentAdapter__effects", ())

    def __setattr__(self, name: str, value: object) -> None:
        if type(self) is not FakeEnvironmentAdapter:
            object.__setattr__(self, name, value)
            return
        raise AttributeError("FakeEnvironmentAdapter instances are immutable")

    @property
    def effects(self) -> tuple[AppliedDryRunEffect, ...]:
        return self.__effects

    def apply(
        self,
        *,
        effect: str,
        promotion_digest: str,
        artifact_digest: str,
        environment: str,
        exposure_basis_points: int,
    ) -> AppliedDryRunEffect:
        effects = self.__effects
        if len(effects) >= 128:
            raise AdapterBoundaryError("effects", "cannot exceed 128 dry-run records")
        if effect not in _SUPPORTED_EFFECTS:
            raise AdapterBoundaryError("effect", "is not a supported dry-run effect")
        if not isinstance(promotion_digest, str) or not _HEX64.fullmatch(
            promotion_digest
        ):
            raise AdapterBoundaryError("promotion_digest", "must be lowercase 64-hex")
        if not isinstance(artifact_digest, str) or not _HEX64.fullmatch(artifact_digest):
            raise AdapterBoundaryError("artifact_digest", "must be lowercase 64-hex")
        if environment not in {"preview", "staging", "bounded_canary"}:
            raise AdapterBoundaryError(
                "environment", "only the three nonproduction stages are representable"
            )
        if type(exposure_basis_points) is not int or not 0 <= exposure_basis_points <= 10000:
            raise AdapterBoundaryError(
                "exposure_basis_points", "must be an integer from 0 through 10000"
            )
        applied = AppliedDryRunEffect(
            effect=effect,
            promotion_digest=promotion_digest,
            artifact_digest=artifact_digest,
            environment=environment,
            exposure_basis_points=exposure_basis_points,
        )
        object.__setattr__(
            self,
            "_FakeEnvironmentAdapter__effects",
            effects + (applied,),
        )
        return applied
