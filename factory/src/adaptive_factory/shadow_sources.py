"""Trusted adapter seams only; no live acquisition, keys, URLs or default positive source."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .shadow_lookup import (
    M7LookupRequestV1, M7OutcomeObservationV1, M7CheckObservationV1,
    M7GitHubContextV1, M7EpochContextV1, SourceUnavailable,
)


@dataclass(frozen=True)
class CurrentPrSubject:
    repository_id: str
    pr_number: int


class HumanOutcomeSource(Protocol):
    def resolve(self, request: M7LookupRequestV1) -> M7OutcomeObservationV1 | SourceUnavailable: ...


class SignedCiSource(Protocol):
    def resolve(self, request: M7LookupRequestV1) -> M7CheckObservationV1 | SourceUnavailable: ...


class GitHubCurrentSource(Protocol):
    # The selector intentionally contains no caller-desired head or policy.
    def resolve(self, subject: CurrentPrSubject) -> M7GitHubContextV1 | SourceUnavailable: ...


class DeployedEpochSource(Protocol):
    def resolve(self, repository_id: str) -> M7EpochContextV1 | SourceUnavailable: ...


class UnavailableHumanOutcomeSource:
    def resolve(self, request: M7LookupRequestV1) -> SourceUnavailable:
        return SourceUnavailable()


class UnavailableSignedCiSource:
    def resolve(self, request: M7LookupRequestV1) -> SourceUnavailable:
        return SourceUnavailable()


class UnavailableGitHubCurrentSource:
    def resolve(self, subject: CurrentPrSubject) -> SourceUnavailable:
        return SourceUnavailable()


class UnavailableDeployedEpochSource:
    def resolve(self, repository_id: str) -> SourceUnavailable:
        return SourceUnavailable()
