from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import landing_renderer as landing_pins
from .landing_artifact import (
    DEPLOY_MEMBERS,
    ExactGitLandingArtifactSource,
    LandingArtifactPackager,
    LandingArtifactResult,
)
from .landing_artifact_retention import RetainedLandingArtifact
from .landing_contracts import (
    LandingInputV1,
    LandingProviderEvidenceV1,
    SiteArtifactV1,
    StaticLandingSpecV1,
    landing_digest,
)
from .landing_coordinator import LandingCoordinator, LandingRunResult
from .landing_evaluation import DeterministicLandingEvaluator
from .landing_intake import PrivateLandingBlobStore
from .landing_normalizer import (
    CodexLandingExecutor,
    CodexLandingNormalizer,
    CodexLandingProfile,
)
from .landing_provider import UnavailableLandingProvider, unavailable_landing_profile
from .landing_renderer import (
    DeterministicLandingRenderer,
    ExactGitLandingWorkspace,
    LANDING_WRITE_PATHS,
    RENDERER_VERSION,
    TARGET_REPOSITORY_ID,
)
from .landing_service import (
    InMemoryLandingJobStore,
    LandingApplicationService,
    LandingJobStore,
)


class LandingRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class CoordinatedLandingArtifactResult:
    run: LandingRunResult
    sealed: LandingArtifactResult
    retained: RetainedLandingArtifact

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
        retained = RetainedLandingArtifact.capture(
            sealed, evidence, run.attempts[-1], run.evaluations[-1], source
        )
        return CoordinatedLandingArtifactResult(run, sealed, retained)


@dataclass(frozen=True)
class LandingLiveBindingV1:
    schema_version: int
    repository_id: str
    exact_base_sha: str
    exact_base_tree: str
    renderer_version: str
    deploy_members: tuple[str, ...]
    write_paths: frozenset[str]
    enabled: bool

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise LandingRuntimeError("binding_version")
        if self.repository_id != TARGET_REPOSITORY_ID:
            raise LandingRuntimeError("source_binding_unimplemented")
        if self.renderer_version != RENDERER_VERSION:
            raise LandingRuntimeError("source_binding_unimplemented")
        if tuple(self.deploy_members) != DEPLOY_MEMBERS:
            raise LandingRuntimeError("source_binding_unimplemented")
        if frozenset(self.write_paths) != LANDING_WRITE_PATHS:
            raise LandingRuntimeError("source_binding_unimplemented")

    @property
    def binding_digest(self) -> str:
        return landing_digest(
            "live-binding",
            {
                "schema_version": self.schema_version,
                "repository_id": self.repository_id,
                "exact_base_sha": self.exact_base_sha,
                "exact_base_tree": self.exact_base_tree,
                "renderer_version": self.renderer_version,
                "deploy_members": list(self.deploy_members),
                "write_paths": sorted(self.write_paths),
                "enabled": self.enabled,
            },
        )


def implemented_live_binding(*, enabled: bool = False) -> LandingLiveBindingV1:
    return LandingLiveBindingV1(
        schema_version=1,
        repository_id=landing_pins.TARGET_REPOSITORY_ID,
        exact_base_sha=landing_pins.TARGET_BASE_SHA,
        exact_base_tree=landing_pins.TARGET_BASE_TREE,
        renderer_version=landing_pins.RENDERER_VERSION,
        deploy_members=DEPLOY_MEMBERS,
        write_paths=landing_pins.LANDING_WRITE_PATHS,
        enabled=enabled,
    )


def compose_unavailable_landing(
    blobs: PrivateLandingBlobStore,
    *,
    store: LandingJobStore | None = None,
    clock: Callable[[], datetime] | None = None,
) -> LandingApplicationService:
    profile = unavailable_landing_profile()
    return LandingApplicationService(
        store or InMemoryLandingJobStore(),
        blobs,
        UnavailableLandingProvider(profile, clock=clock),
        profile_digest=profile.profile_digest,
        clock=clock,
    )


def compose_landing_live(
    *,
    binding: LandingLiveBindingV1,
    profile: CodexLandingProfile,
    executor: CodexLandingExecutor,
    source_repository: Path,
    scratch_root: Path,
    output_directory: Path,
    blobs: PrivateLandingBlobStore,
    store: LandingJobStore | None = None,
    clock: Callable[[], datetime] | None = None,
) -> LandingApplicationService:
    if not binding.enabled:
        raise LandingRuntimeError("live_disabled")
    if (
        binding.exact_base_sha != landing_pins.TARGET_BASE_SHA
        or binding.exact_base_tree != landing_pins.TARGET_BASE_TREE
    ):
        raise LandingRuntimeError("source_binding_unimplemented")
    if not isinstance(profile, CodexLandingProfile) or not profile.available:
        raise LandingRuntimeError("profile_unavailable")
    if executor is None:
        raise LandingRuntimeError("executor_required")
    tick = clock or (lambda: datetime.now(timezone.utc))
    builder = create_landing_artifact_builder(
        binding=binding,
        source_repository=source_repository,
        scratch_root=scratch_root,
        output_directory=output_directory,
        clock=tick,
    )
    return LandingApplicationService(
        store or InMemoryLandingJobStore(),
        blobs,
        CodexLandingNormalizer(profile, executor, clock=tick),
        profile_digest=profile.profile_digest,
        artifact_builder=builder,
        clock=tick,
    )


def create_landing_artifact_builder(
    *,
    binding: LandingLiveBindingV1,
    source_repository: Path,
    scratch_root: Path,
    output_directory: Path,
    clock: Callable[[], datetime] | None = None,
) -> CoordinatedLandingArtifactBuilder:
    """Share the exact-source artifact pipeline across separately identified providers."""
    if not isinstance(binding, LandingLiveBindingV1) or not binding.enabled:
        raise LandingRuntimeError("live_disabled")
    if (
        binding.exact_base_sha != landing_pins.TARGET_BASE_SHA
        or binding.exact_base_tree != landing_pins.TARGET_BASE_TREE
    ):
        raise LandingRuntimeError("source_binding_unimplemented")
    source = Path(source_repository)
    scratch = Path(scratch_root)
    output = Path(output_directory)
    if not source.is_absolute() or not scratch.is_absolute() or not output.is_absolute():
        raise LandingRuntimeError("output_path")
    tick = clock or (lambda: datetime.now(timezone.utc))
    return CoordinatedLandingArtifactBuilder(
        LandingCoordinator(
            ExactGitLandingWorkspace(source, scratch_root=scratch),
            DeterministicLandingRenderer(),
            DeterministicLandingEvaluator(clock=tick),
            clock=tick,
        ),
        LandingArtifactPackager(ExactGitLandingArtifactSource(source)),
        output,
    )
