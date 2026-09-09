from __future__ import annotations

import json
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .architecture import architecture_digests, contract_inventory, load_architecture, validate_architecture
from .governance import governance_summary, load_governance
from .router import build_route
from .spec import canonical_spec_digest, criterion_coverage, generate_spec, load_spec, summarize_spec, validate_spec
from .verification import summarize_verification_report


SCHEMA_VERSION = 1
MAX_FIXTURE_BYTES = 256 * 1024
SAMPLE_DIR = Path(".grok-stack/demo/sample")
DEMO_ROUTE_METADATA: dict[str, str | None] = {
    "base_commit": None,
    "base_fingerprint": "66678596e6959af8a87ac7bb051f8372c93b79d112fa92fe949966d3b699af9b",
}


def _duplicate_reject(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if not data or len(data) > MAX_FIXTURE_BYTES:
        raise ValueError(f"fixture size is invalid: {path.name}")
    try:
        value = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=_duplicate_reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"fixture JSON is invalid: {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"fixture root must be an object: {path.name}")
    return value


def _valid_prompt(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 4000
        and not any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value)
    )


def load_demo_fixtures(root: Path) -> dict[str, dict[str, Any]]:
    sample = root / SAMPLE_DIR
    task = _read_json(sample / "task.json")
    if set(task) != {"schema_version", "primary_prompt", "alternate_prompt"} or task["schema_version"] != 1:
        raise ValueError("task fixture fields or version are invalid")
    if not _valid_prompt(task["primary_prompt"]) or not _valid_prompt(task["alternate_prompt"]):
        raise ValueError("task fixture prompt is invalid")
    spec = load_spec(sample / "change-spec.json", allow_legacy=False)
    validate_spec(spec)
    report = _read_json(sample / "verification-report.json")
    summarize_verification_report(report)
    return {"task": task, "spec": spec, "verification": report}


def _timestamp(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("demo time must be timezone-aware")
    return now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _route_projection(route: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "intent", "risk", "complexity", "domains", "workflow_skills", "analysis_agents",
        "write_agent", "review_agents", "quality_profiles", "human_gates",
    )
    return {"source": "computed_preview", **{field: route.get(field) for field in fields}}


def _alternate_action_label(route: dict[str, Any]) -> str:
    intent = str(route.get("intent") or "alternate").replace("_", " ")
    risk = str(route.get("risk") or "computed").replace("_", " ")
    owner = str(route.get("write_agent") or "no write owner").replace("_", " ")
    return f"Use contrasting {intent} route · {risk} risk · {owner}"


def _sample_spec_projection(spec: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_spec(spec)
    coverage = criterion_coverage(spec)
    return {
        "source": "bundled_sample",
        "status": "complete",
        "digest": summary["digest"],
        "objective": summary["objective"],
        "criterion_total": coverage["criterion_total"],
        "criterion_mapped": coverage["criterion_mapped"],
        "invariant_total": summary["invariants"],
        "forbidden_total": summary["forbidden_outcomes"],
    }


def _draft_spec_projection(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "computed_preview",
        "status": "draft",
        "design_required": True,
        "digest": canonical_spec_digest(spec),
        "objective": spec["objective"],
        "criterion_total": 0,
        "criterion_mapped": 0,
        "invariant_total": 0,
        "forbidden_total": 0,
    }


def _architecture_projection(root: Path) -> dict[str, Any]:
    try:
        snapshot = load_architecture(root)
        findings = validate_architecture(snapshot, root)
        digests = architecture_digests(snapshot)
        return {
            "source": "live_repository",
            "status": "fail" if findings else "pass",
            "architecture_id": snapshot.system["architecture_id"],
            "digest": digests["architecture_digest"],
            "node_count": len(snapshot.system["nodes"]),
            "edge_count": len(snapshot.system["edges"]),
            "contract_count": len(contract_inventory(root, snapshot)),
            "trust_domain_count": len(snapshot.system["trust_domains"]),
            "rule_count": sum(
                len(snapshot.rules.get(name) or [])
                for name in snapshot.rules
                if isinstance(snapshot.rules.get(name), list)
            ),
            "finding_count": len(findings),
            "findings": [{"code": item.code, "message": item.message} for item in findings[:8]],
        }
    except (OSError, RuntimeError, TypeError, ValueError):
        return {
            "source": "live_repository",
            "status": "unavailable",
            "error": {"code": "resource_unavailable", "message": "Repository model is unavailable."},
        }


def _governance_projection(root: Path, now: datetime) -> dict[str, Any]:
    try:
        summary = governance_summary(load_governance(root), now=now)
        return {
            "source": "live_repository",
            "status": summary["overall_status"],
            "digest": summary["governance_digest"],
            "active_rule_count": len(summary["active_rule_ids"]),
            "candidate_rule_count": len(summary["candidate_rule_ids"]),
            "open_debt_count": len(summary["open_debt_ids"]),
            "example_count": summary["example_count"],
            "finding_count": len(summary["findings"]),
            "findings": summary["findings"][:8],
        }
    except (OSError, RuntimeError, TypeError, ValueError):
        return {
            "source": "live_repository",
            "status": "unavailable",
            "error": {"code": "resource_unavailable", "message": "Governance evidence is unavailable."},
        }


def _verification_projection(report: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_verification_report(report)
    return {"source": "bundled_sample", **summary}


def _base(now: datetime, request_id: str | None, mode: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id or uuid.uuid4().hex,
        "generated_at": _timestamp(now),
        "mode": mode,
        "external_writes": False,
    }


def build_sample_snapshot(
    root: Path,
    *,
    now: datetime | None = None,
    request_id: str | None = None,
    route_metadata: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    evaluated_at = now or datetime.now(timezone.utc)
    fixtures = load_demo_fixtures(root)
    metadata = route_metadata or DEMO_ROUTE_METADATA
    route_args = {
        "base_commit_override": metadata.get("base_commit"),
        "base_fingerprint_override": metadata["base_fingerprint"],
    }
    route = build_route(root, fixtures["task"]["primary_prompt"], "demo-sample", **route_args).to_dict()
    alternate_route = build_route(
        root,
        fixtures["task"]["alternate_prompt"],
        "demo-alternate",
        **route_args,
    ).to_dict()
    alternate_projection = _route_projection(alternate_route)
    return {
        **_base(evaluated_at, request_id, "bundled_sample"),
        "scenario": {
            "source": "bundled_sample",
            "sample_id": fixtures["verification"]["sample_id"],
            "primary_prompt": fixtures["task"]["primary_prompt"],
            "alternate_prompt": fixtures["task"]["alternate_prompt"],
            "alternate_route": alternate_projection,
            "alternate_action_label": _alternate_action_label(alternate_projection),
        },
        "route": _route_projection(route),
        "spec": _sample_spec_projection(fixtures["spec"]),
        "architecture": _architecture_projection(root),
        "governance": _governance_projection(root, evaluated_at),
        "verification": _verification_projection(fixtures["verification"]),
    }


def build_prompt_preview(
    root: Path,
    prompt: str,
    *,
    now: datetime | None = None,
    request_id: str | None = None,
    route_metadata: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    if not _valid_prompt(prompt):
        raise ValueError("Prompt must contain 1 to 4000 characters without control characters.")
    evaluated_at = now or datetime.now(timezone.utc)
    metadata = route_metadata or DEMO_ROUTE_METADATA
    route_args = {
        "base_commit_override": metadata.get("base_commit"),
        "base_fingerprint_override": metadata["base_fingerprint"],
    }
    route = build_route(root, prompt, "demo-preview", **route_args).to_dict()
    spec = generate_spec(route)
    not_run = {
        "source": "computed_preview",
        "status": "not_run",
        "digest": None,
        "checks": [],
    }
    not_run.update({status: 0 for status in ("pass", "fail", "skip")})
    return {
        **_base(evaluated_at, request_id, "computed_preview"),
        "route": _route_projection(route),
        "spec": _draft_spec_projection(spec),
        "architecture": _architecture_projection(root),
        "governance": _governance_projection(root, evaluated_at),
        "verification": not_run,
    }


def health_snapshot(root: Path, *, now: datetime | None = None) -> dict[str, Any]:
    snapshot = build_sample_snapshot(root, now=now)
    degraded = any(snapshot[name]["status"] == "unavailable" for name in ("architecture", "governance"))
    return {
        "schema_version": 1,
        "request_id": snapshot["request_id"],
        "generated_at": snapshot["generated_at"],
        "external_writes": False,
        "status": "degraded" if degraded else "ready",
        "sections": {
            name: snapshot[name]["status"]
            for name in ("spec", "architecture", "governance", "verification")
        },
    }


class DemoApplication:
    """Prepared read-only application state shared by all HTTP requests."""

    def __init__(self, root: Path, *, now_provider=None) -> None:
        self.root = root.resolve(strict=True)
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self.route_metadata = dict(DEMO_ROUTE_METADATA)
        self.sample = build_sample_snapshot(
            self.root,
            now=self.now_provider(),
            route_metadata=self.route_metadata,
        )

    def snapshot(self) -> dict[str, Any]:
        return self.sample

    def health(self) -> dict[str, Any]:
        degraded = any(
            self.sample[name]["status"] == "unavailable"
            for name in ("architecture", "governance")
        )
        return {
            "schema_version": 1,
            "request_id": uuid.uuid4().hex,
            "generated_at": _timestamp(self.now_provider()),
            "external_writes": False,
            "status": "degraded" if degraded else "ready",
            "sections": {
                name: self.sample[name]["status"]
                for name in ("spec", "architecture", "governance", "verification")
            },
        }

    def preview(self, prompt: str) -> dict[str, Any]:
        return build_prompt_preview(
            self.root,
            prompt,
            now=self.now_provider(),
            route_metadata=self.route_metadata,
        )
