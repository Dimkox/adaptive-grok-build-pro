"""Admission quality gate for repository verification reports.

The verifier may report ``skip`` for a check that is intentionally outside the current
scope. QG-01 keeps that value from becoming a silent pass: mandatory checks may be
absent or skipped only when an explicit local policy explains why.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

MANDATORY_PR_CHECKS = frozenset(
    {
        "git-diff-check",
        "docs-state-scope",
        "change-spec",
        "architecture-inputs",
        "architecture",
        "governance",
        "workflow-artifacts",
        "secret-scan",
        "contract-structure",
        "sql-safety",
        "source-stability",
    }
)

MANDATORY_PYTHON_PR_CHECKS = frozenset({"ruff", "bandit"})
FULL_DISCOVERY_RUNNERS = frozenset({"python-unittest", "pytest"})
FOCUSED_DISCOVERY_RUNNERS = frozenset({"python-focused-unittest"})


@dataclass(frozen=True)
class QualityGateDecision:
    status: str
    summary: str
    details: list[dict[str, str]] = field(default_factory=list)


def _value(check: object, field_name: str) -> str:
    if isinstance(check, dict):
        value = check.get(field_name)
    else:
        value = getattr(check, field_name, None)
    return value if isinstance(value, str) else ""


def _by_name(checks: Iterable[object]) -> dict[str, object]:
    named: dict[str, object] = {}
    for check in checks:
        name = _value(check, "name")
        if name:
            named[name] = check
    return named


def _docs_declares_skip(docs_scope: dict[str, object] | None, name: str) -> bool:
    if not docs_scope or docs_scope.get("eligible") is not True:
        return False
    skipped = docs_scope.get("skipped_checks", ())
    return isinstance(skipped, (list, tuple)) and name in skipped


def _allowed_skip(name: str, summary: str, docs_scope: dict[str, object] | None) -> bool:
    if _docs_declares_skip(docs_scope, name):
        return True
    if "architecture input preflight failed" in summary:
        return True
    if name == "ruff":
        return summary == "no python quality paths"
    if name == "bandit":
        return summary in {"no non-test python paths", "bandit not available"}
    if name == "architecture-inputs":
        return summary == "architecture authority inputs are absent; not executed"
    if name == "change-spec":
        return summary == "0 specs checked; exempt=True"
    if name == "coverage":
        return summary == "pytest runner owns tests; measure unittest trees only"
    if name == "factory-postgres-exit":
        return summary == "repository-sandbox has no nested-container/database capability"
    if name in {"architecture", "governance", "workflow-artifacts"}:
        return summary in {
            "architecture is not configured",
            "governance is not configured",
            "no active change",
            "workflow artifacts are not configured",
        }
    return False


def _detail(code: str, name: str, message: str) -> dict[str, str]:
    return {"severity": "error", "code": code, "path": name, "message": message}


def _status_findings(check: object, mode: str, docs_scope: dict[str, object] | None) -> list[dict[str, str]]:
    name, status, summary = (_value(check, key) for key in ('name', 'status', 'summary'))
    if status == 'skip' and mode in {'pr', 'release'} and not _allowed_skip(name, summary, docs_scope):
        return [_detail('mandatory-check-skipped', name,
                        f'{name} was skipped without an explicit QG-01 allowance: {summary}')]
    if status not in {'pass', 'fail', 'skip', 'cancelled'}:
        return [_detail('unknown-check-status', name, f'{name} returned {status!r}')]
    return []


def required_check_refused(check: object, *, mode: str, docs_scope: dict[str, object] | None = None) -> bool:
    """Inspect one completed result without claiming future admission completeness."""
    return mode in {'pr', 'release'} and (
        _value(check, 'status') in {'fail', 'cancelled'} or bool(_status_findings(check, mode, docs_scope))
    )


def evaluate_quality_gate(
    *,
    mode: str,
    checks: Iterable[object],
    docs_scope: dict[str, object] | None = None,
) -> QualityGateDecision:
    """Return the QG-01 admission decision for already executed checks."""
    check_map = _by_name(checks)
    details: list[dict[str, str]] = []

    if mode in {"pr", "release"}:
        required = set(MANDATORY_PR_CHECKS)
        required.update(MANDATORY_PYTHON_PR_CHECKS)
        for name in sorted(required - set(check_map)):
            details.append(_detail("mandatory-check-missing", name, f"{name} did not run"))

        full_runners = set(check_map) & FULL_DISCOVERY_RUNNERS
        full_discovery_reported = any(_value(check_map[name], 'status') in {'pass', 'fail'} for name in full_runners)
        focused_reported = any(_value(check_map[name], 'status') in {'pass', 'fail'} for name in set(check_map) & FOCUSED_DISCOVERY_RUNNERS)
        focused_admitted = (
            focused_reported
            and _value(check_map.get('docs-state-scope'), 'status') == 'pass'
            and _docs_declares_skip(docs_scope, 'coverage')
            and _value(check_map.get('coverage'), 'status') == 'skip'
            and any(
                _docs_declares_skip(docs_scope, name)
                and _value(check_map[name], 'status') == 'skip'
                for name in full_runners
            )
        )
        if focused_reported and not full_discovery_reported and not focused_admitted:
            details.append(_detail(
                'focused-discovery-unscoped', 'python-focused-unittest',
                'focused discovery requires an eligible documentation/state scope and explicit replaced-runner and coverage skip records',
            ))
        if not (full_discovery_reported or focused_admitted):
            details.append(
                _detail(
                    "mandatory-check-missing",
                    "python-discovery",
                    "no Python discovery runner reported an executed pass/fail result",
                )
            )
        if full_runners and "coverage" not in check_map:
            details.append(_detail("mandatory-check-missing", "coverage", "coverage did not run"))

    for name, check in sorted(check_map.items()):
        details.extend(_status_findings(check, mode, docs_scope))

    if details:
        return QualityGateDecision("fail", f"QG-01 blocked admission: {len(details)} finding(s)", details)
    return QualityGateDecision("pass", "QG-01 admission checks passed", [])
