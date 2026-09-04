from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import html
import re
from typing import Protocol

from .landing_contracts import (
    LandingAttemptV1,
    LandingContractError,
    LandingEvaluationV1,
    StaticLandingSpecV1,
    landing_digest,
    same_origin_root_path,
)
from .landing_renderer import (
    LANDING_WRITE_PATHS,
    LandingCandidateSnapshot,
    LandingRenderError,
    source_surface_facts,
)


EVALUATOR_ID = "independent-landing-evaluator"
EVALUATOR_VERSION = "1.0.0"
EVALUATOR_IDENTITY_DIGEST = landing_digest(
    "evaluator-identity",
    {"evaluator_id": EVALUATOR_ID, "version": EVALUATOR_VERSION},
)
POLICY_DIGEST = landing_digest(
    "evaluation-policy",
    {
        "policy": "preserve-source-static-no-active-content",
        "version": EVALUATOR_VERSION,
    },
)
RUBRIC_DIGEST = landing_digest(
    "evaluation-rubric",
    {
        "checks": [
            "closed-spec",
            "exact-subject",
            "full-tree",
            "source-facts",
            "static-surface",
        ],
        "version": EVALUATOR_VERSION,
    },
)
REPAIR_REASON_CODES = frozenset({"copy_density", "missing_required_section"})
_TERMINAL_REASON_CODES = frozenset(
    {"active_content", "identity_mismatch", "source_fact_drift", "tree_scope_violation"}
)


class LandingEvaluationError(RuntimeError):
    pass


class LandingEvaluator(Protocol):
    evaluator_id: str
    identity_digest: str

    def evaluate(
        self,
        attempt: LandingAttemptV1,
        spec: StaticLandingSpecV1,
        candidate: LandingCandidateSnapshot,
    ) -> LandingEvaluationV1: ...


class DeterministicLandingEvaluator:
    evaluator_id = EVALUATOR_ID
    identity_digest = EVALUATOR_IDENTITY_DIGEST
    policy_digest = POLICY_DIGEST
    rubric_digest = RUBRIC_DIGEST

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate(
        self,
        attempt: LandingAttemptV1,
        spec: StaticLandingSpecV1,
        candidate: LandingCandidateSnapshot,
    ) -> LandingEvaluationV1:
        reasons = self._inspect(attempt, spec, candidate)
        if reasons & _TERMINAL_REASON_CODES:
            decision = "needs_human"
        elif reasons:
            decision = "repair"
        else:
            decision = "pass"
        findings = sorted(
            landing_digest(
                "evaluation-finding",
                {
                    "candidate_sha": candidate.candidate_sha,
                    "reason_code": reason,
                },
            )
            for reason in reasons
        )
        requirements = sorted(
            landing_digest("evaluation-requirement", {"requirement": name})
            for name in (
                "exact-subject",
                "preserve-source-facts",
                "static-surface",
                "two-file-scope",
            )
        )
        created = self._clock()
        if not isinstance(created, datetime) or created.tzinfo is None:
            raise LandingEvaluationError("evaluator_clock")
        return LandingEvaluationV1.from_facts(
            {
                "schema_version": 1,
                "attempt_digest": attempt.attempt_digest,
                "candidate_head_sha": candidate.candidate_sha,
                "evaluator_id": self.evaluator_id,
                "context_digest": landing_digest(
                    "evaluator-context",
                    {
                        "attempt_digest": attempt.attempt_digest,
                        "candidate_tree": candidate.candidate_tree,
                        "policy_digest": self.policy_digest,
                        "rubric_digest": self.rubric_digest,
                    },
                ),
                "policy_digest": self.policy_digest,
                "rubric_digest": self.rubric_digest,
                "decision": decision,
                "reason_codes": sorted(reasons),
                "requirement_digests": requirements,
                "finding_digests": findings,
                "created_at": created.astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )

    @staticmethod
    def _inspect(
        attempt: LandingAttemptV1,
        spec: StaticLandingSpecV1,
        candidate: LandingCandidateSnapshot,
    ) -> set[str]:
        reasons: set[str] = set()
        if (
            attempt.exact_head_sha != candidate.candidate_sha
            or attempt.exact_base_sha != candidate.source_sha
            or attempt.renderer_digest != candidate.renderer_digest
            or attempt.workspace_result_digest != candidate.workspace_result_digest
            or spec.spec_digest != attempt.spec_digest
        ):
            reasons.add("identity_mismatch")
        source_inventory = {
            item.path: (item.mode, item.object_id) for item in candidate.source_members
        }
        candidate_inventory = {
            item.path: (item.mode, item.object_id) for item in candidate.candidate_members
        }
        if (
            set(source_inventory) != set(candidate_inventory)
            or set(candidate.changed_paths) != LANDING_WRITE_PATHS
            or any(
                source_inventory[path] != candidate_inventory[path]
                for path in source_inventory
                if path not in LANDING_WRITE_PATHS
            )
        ):
            reasons.add("tree_scope_violation")
        try:
            source_html = candidate.source_index_html.decode("utf-8")
            rendered_html = candidate.index_html.decode("utf-8")
            rendered_css = candidate.content_css.decode("utf-8")
            if source_surface_facts(source_html) != source_surface_facts(rendered_html):
                reasons.add("source_fact_drift")
        except (UnicodeDecodeError, LandingRenderError):
            reasons.add("source_fact_drift")
            rendered_html = ""
            rendered_css = ""
        lowered = rendered_html.lower()
        scripts = re.findall(r"<script(?:\s[^>]*)?>.*?</script>", rendered_html, re.DOTALL)
        if (
            len(scripts) != 1
            or not scripts[0].startswith('<script type="application/ld+json">')
            or any(
                forbidden in lowered
                for forbidden in ("<form", "google-analytics", "gtag(", "javascript:")
            )
            or "@import" in rendered_css.lower()
            or "url(http" in rendered_css.lower()
        ):
            reasons.add("active_content")
        generated_hrefs = tuple(
            html.unescape(value)
            for value in re.findall(
                r'<a class="l5-action" href="([^"]*)">', rendered_html
            )
        )
        try:
            expected_hrefs = tuple(
                same_origin_root_path(section.cta_path)
                for section in spec.sections
                if section.cta_label
            )
            if (
                generated_hrefs != expected_hrefs
                or any(same_origin_root_path(value) != value for value in generated_hrefs)
            ):
                reasons.add("active_content")
        except LandingContractError:
            reasons.add("active_content")
        required_text = [html.escape(spec.title), html.escape(spec.description)]
        required_text.extend(html.escape(section.heading) for section in spec.sections)
        if any(value not in rendered_html for value in required_text):
            reasons.add("missing_required_section")
        if len(candidate.index_html) + len(candidate.content_css) > 1_500_000:
            reasons.add("copy_density")
        return reasons
