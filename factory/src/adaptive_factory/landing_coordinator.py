from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import re

from .landing_contracts import (
    LandingAttemptV1,
    LandingEvaluationV1,
    StaticLandingSpecV1,
    landing_digest,
)
from .landing_evaluation import LandingEvaluator, REPAIR_REASON_CODES
from .landing_renderer import (
    LandingCandidateSnapshot,
    LandingRenderer,
    ExactGitLandingWorkspace,
)


MAX_LANDING_ATTEMPTS = 3
LANDING_WRITER_ID = "landing-writer"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LandingCoordinatorError(RuntimeError):
    pass


@dataclass(frozen=True)
class LandingRunResult:
    disposition: str
    candidate: LandingCandidateSnapshot | None
    attempts: tuple[LandingAttemptV1, ...]
    evaluations: tuple[LandingEvaluationV1, ...]
    terminal_reason: str | None
    run_digest: str


class LandingCoordinator:
    def __init__(
        self,
        workspace: ExactGitLandingWorkspace,
        renderer: LandingRenderer,
        evaluator: LandingEvaluator,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._workspace = workspace
        self._renderer = renderer
        self._evaluator = evaluator
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(
        self, spec: StaticLandingSpecV1, *, profile_digest: str
    ) -> LandingRunResult:
        if not isinstance(spec, StaticLandingSpecV1):
            raise LandingCoordinatorError("spec_type")
        if not isinstance(profile_digest, str) or not _HEX64.fullmatch(profile_digest):
            raise LandingCoordinatorError("profile_digest")
        evaluator_digest = getattr(self._evaluator, "identity_digest", None)
        evaluator_id = getattr(self._evaluator, "evaluator_id", None)
        if not isinstance(evaluator_digest, str) or not _HEX64.fullmatch(evaluator_digest):
            raise LandingCoordinatorError("evaluator_identity")
        if not isinstance(evaluator_id, str) or not evaluator_id:
            raise LandingCoordinatorError("evaluator_identity")

        attempts: list[LandingAttemptV1] = []
        evaluations: list[LandingEvaluationV1] = []
        prior_attempt: LandingAttemptV1 | None = None
        repair_codes: tuple[str, ...] = ()
        seen_repairs: set[str] = set()
        for ordinal in range(1, MAX_LANDING_ATTEMPTS + 1):
            candidate = self._workspace.build_candidate(
                spec,
                self._renderer,
                ordinal=ordinal,
                repair_codes=repair_codes,
            )
            started = self._timestamp()
            completed = self._timestamp()
            attempt = LandingAttemptV1.from_facts(
                {
                    "schema_version": 1,
                    "input_digest": spec.input_digest,
                    "spec_digest": spec.spec_digest,
                    "profile_digest": profile_digest,
                    "ordinal": ordinal,
                    "exact_base_sha": candidate.source_sha,
                    "exact_head_sha": candidate.candidate_sha,
                    "workspace_result_digest": candidate.workspace_result_digest,
                    "renderer_digest": candidate.renderer_digest,
                    "writer_id": LANDING_WRITER_ID,
                    "context_digest": landing_digest(
                        "renderer-context",
                        {
                            "ordinal": ordinal,
                            "prior_attempt_digest": (
                                prior_attempt.attempt_digest if prior_attempt else None
                            ),
                            "repair_codes": list(repair_codes),
                            "spec_digest": spec.spec_digest,
                        },
                    ),
                    "evaluator_digest": evaluator_digest,
                    "prior_attempt_digest": (
                        prior_attempt.attempt_digest if prior_attempt else None
                    ),
                    "outcome": "candidate" if ordinal == 1 else "repair",
                    "started_at": started,
                    "completed_at": completed,
                }
            )
            attempts.append(attempt)
            if evaluator_id == LANDING_WRITER_ID:
                return self._result(
                    "needs_human",
                    None,
                    attempts,
                    evaluations,
                    "evaluator_not_independent",
                )
            evaluation = self._evaluator.evaluate(attempt, spec, candidate)
            if not self._evaluation_is_bound(
                evaluation, attempt, candidate, evaluator_id
            ):
                return self._result(
                    "needs_human",
                    None,
                    attempts,
                    evaluations,
                    "evaluation_binding",
                )
            evaluations.append(evaluation)
            if evaluation.decision == "pass":
                if evaluation.reason_codes or evaluation.finding_digests:
                    return self._result(
                        "needs_human",
                        None,
                        attempts,
                        evaluations,
                        "contradictory_pass",
                    )
                return self._result(
                    "candidate_ready", candidate, attempts, evaluations, None
                )
            if evaluation.decision == "needs_human":
                return self._result(
                    "needs_human",
                    None,
                    attempts,
                    evaluations,
                    "evaluator_needs_human",
                )
            reasons = set(evaluation.reason_codes)
            if (
                not reasons
                or not reasons <= REPAIR_REASON_CODES
                or reasons & seen_repairs
                or ordinal == MAX_LANDING_ATTEMPTS
            ):
                return self._result(
                    "needs_human",
                    None,
                    attempts,
                    evaluations,
                    "repair_boundary",
                )
            seen_repairs.update(reasons)
            repair_codes = tuple(sorted(reasons))
            prior_attempt = attempt
        raise LandingCoordinatorError("attempt_ceiling")

    @staticmethod
    def _evaluation_is_bound(
        evaluation: LandingEvaluationV1,
        attempt: LandingAttemptV1,
        candidate: LandingCandidateSnapshot,
        evaluator_id: str,
    ) -> bool:
        return (
            isinstance(evaluation, LandingEvaluationV1)
            and evaluation.attempt_digest == attempt.attempt_digest
            and evaluation.candidate_head_sha == candidate.candidate_sha
            and evaluation.evaluator_id == evaluator_id
        )

    def _timestamp(self) -> str:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise LandingCoordinatorError("clock")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _result(
        disposition: str,
        candidate: LandingCandidateSnapshot | None,
        attempts: list[LandingAttemptV1],
        evaluations: list[LandingEvaluationV1],
        terminal_reason: str | None,
    ) -> LandingRunResult:
        if disposition not in {"candidate_ready", "needs_human"}:
            raise LandingCoordinatorError("disposition")
        values = {
            "disposition": disposition,
            "candidate_sha": candidate.candidate_sha if candidate else None,
            "candidate_tree": candidate.candidate_tree if candidate else None,
            "attempt_digests": [item.attempt_digest for item in attempts],
            "evaluation_digests": [item.evaluation_digest for item in evaluations],
            "terminal_reason": terminal_reason,
        }
        return LandingRunResult(
            disposition,
            candidate,
            tuple(attempts),
            tuple(evaluations),
            terminal_reason,
            landing_digest("run-result", values),
        )
