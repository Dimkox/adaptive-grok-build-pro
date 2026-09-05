from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .landing_artifact import LandingArtifactPackager, LandingArtifactResult
from .landing_contracts import (
    LandingInputV1,
    LandingProviderEvidenceV1,
    SiteArtifactV1,
    StaticLandingSpecV1,
)
from .landing_coordinator import LandingCoordinator, LandingRunResult
from .landing_renderer import TARGET_REPOSITORY_ID


class LandingRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class CoordinatedLandingArtifactResult:
    run: LandingRunResult
    sealed: LandingArtifactResult

    @property
    def artifact(self) -> SiteArtifactV1:
        return self.sealed.artifact


class CoordinatedLandingArtifactBuilder:
    """Compose the bounded local render/evaluate/seal path without publishing."""

    def __init__(
        self,
        coordinator: LandingCoordinator,
        packager: LandingArtifactPackager,
        output_directory: Path,
    ) -> None:
        if not isinstance(coordinator, LandingCoordinator):
            raise LandingRuntimeError("coordinator_type")
        if not isinstance(packager, LandingArtifactPackager):
            raise LandingRuntimeError("packager_type")
        output = Path(output_directory)
        if not output.is_absolute():
            raise LandingRuntimeError("output_path")
        self._coordinator = coordinator
        self._packager = packager
        self._output_directory = output

    def build(
        self,
        source: LandingInputV1,
        spec: StaticLandingSpecV1,
        evidence: LandingProviderEvidenceV1,
    ) -> CoordinatedLandingArtifactResult:
        if (
            not isinstance(source, LandingInputV1)
            or not isinstance(spec, StaticLandingSpecV1)
            or not isinstance(evidence, LandingProviderEvidenceV1)
            or source.repository_id != TARGET_REPOSITORY_ID
            or source.input_digest != spec.input_digest
            or source.input_digest != evidence.input_digest
        ):
            raise LandingRuntimeError("input_binding")
        run = self._coordinator.run(spec, profile_digest=evidence.profile_digest)
        if (
            run.disposition != "candidate_ready"
            or run.candidate is None
            or not run.attempts
            or not run.evaluations
        ):
            raise LandingRuntimeError(run.terminal_reason or "candidate_unavailable")
        sealed = self._packager.seal(
            run.candidate,
            run.attempts[-1],
            run.evaluations[-1],
            self._output_directory,
        )
        artifact = sealed.artifact
        if (
            artifact.source_sha != source.exact_base_sha
            or artifact.source_tree != source.exact_base_tree
            or artifact.input_digest != source.input_digest
            or artifact.spec_digest != spec.spec_digest
            or artifact.profile_digest != evidence.profile_digest
        ):
            raise LandingRuntimeError("artifact_binding")
        return CoordinatedLandingArtifactResult(run, sealed)
