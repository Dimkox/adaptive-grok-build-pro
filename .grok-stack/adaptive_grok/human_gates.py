from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from .util import atomic_write_text, now_utc

GATE_SCOPE_FILES = (
    "brief.md",
    "change-spec.yaml",
    "architecture.md",
    "requirements.md",
    "test-plan.md",
)
GATE_ACTIONS = {
    "scope_and_design_approval": {"kind": "transition", "description": "change transition to approved"},
    "production_action_approval": {"kind": "production", "description": "production actions and release preparation"},
    "migration_or_external_write_approval": {"kind": "external-write", "description": "migration or external-write actions"},
}
PRODUCTION_ACTIONS = {
    "git-push-branch", "git-push-tag", "pull-request-merge", "docker-push", "npm-publish", "github-release"
}
EXTERNAL_ACTIONS = {"external-write"}
MIGRATION_PLAN_ACTION = "migration-plan"
ARTIFACT_NAME = "human-gates.json"
ARTIFACT_NOTICE = (
    "Local workflow evidence only; actor labels are caller supplied and not cryptographic identity. "
    "This record is not a delegated grant, Trust CI signed approval, merge authority, or authorization "
    "for an operation beyond an exact delegated grant."
)
_ARTIFACT_KEYS = {"schema_version", "change_id", "route_id", "decisions"}
_DECISION_KEYS = {
    "gate", "decision", "route_id", "change_id", "scope_digest", "action", "resource",
    "decided_at", "actor", "reason",
}


def route_gate_digest(route_id: str, gates: list[str]) -> str:
    payload = json.dumps(
        {"route_id": route_id, "human_gates": gates},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _context(root: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, Path | None, str | None]:
    from .state import get_active_change, get_active_route

    route = get_active_route(root)
    change = get_active_change(root)
    if not isinstance(route, dict) or not route.get("route_id"):
        return route, change, None, "active route is missing or malformed"
    if not isinstance(change, dict) or not change.get("change_id") or not change.get("path"):
        return route, change, None, "active change package is missing"
    if route.get("change_id") not in (None, change.get("change_id")):
        return route, change, None, "active route and change identities do not match"
    candidate = root / str(change["path"])
    if candidate.is_symlink():
        return route, change, None, "active change package must not be a symlink"
    package = candidate.resolve()
    try:
        relative = package.relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return route, change, None, "active change package escapes repository"
    if not relative.startswith("engineering/changes/") or not package.is_dir():
        return route, change, None, "active change package path is invalid"
    state = _read_json(package / "state.json")
    if not isinstance(state, dict) or state.get("change_id") != change.get("change_id"):
        return route, change, None, "active change package identity is invalid"
    if state.get("route_id") != route.get("route_id"):
        return route, change, None, "change package route identity does not match"
    persisted_gates = state.get("human_gates")
    route_snapshot = _read_json(package / "route.json")
    active_gates = route.get("human_gates", [])
    if (
        not isinstance(persisted_gates, list)
        or any(not isinstance(item, str) or not item for item in persisted_gates)
        or state.get("human_gates_digest") != route_gate_digest(state["route_id"], persisted_gates)
        or not isinstance(route_snapshot, dict)
        or route_snapshot.get("route_id") != state["route_id"]
        or route_snapshot.get("human_gates") != persisted_gates
        or active_gates != persisted_gates
    ):
        return route, change, None, "route gate declaration is missing, malformed, or changed"
    return route, change, package, None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _scope_digest(package: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    for name in GATE_SCOPE_FILES:
        digest.update(name.encode("utf-8") + b"\0")
        path = package / name
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"approved scope file is not a regular file: {name}")
            if path.stat().st_size > 1_000_000:
                raise ValueError(f"approved scope file exceeds its size bound: {name}")
            content = path.read_bytes()
        except OSError as exc:
            raise ValueError(f"approved scope file is unavailable: {name}") from exc
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def _declared_gates(route: dict[str, Any] | None) -> tuple[list[str], str | None]:
    if route is None:
        return [], "active route is missing"
    raw = route.get("human_gates", [])
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item for item in raw):
        return [], "route human_gates declaration is malformed"
    gates = list(dict.fromkeys(raw))
    unknown = sorted(set(gates) - GATE_ACTIONS.keys())
    if unknown:
        return gates, f"route declares unknown human gate(s): {', '.join(unknown)}"
    return gates, None


def _valid_artifact(root: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, Path | None, str | None, str | None]:
    route, change, package, context_error = _context(root)
    if context_error:
        return route, change, package, None, context_error
    assert route is not None and change is not None and package is not None
    path = package / ARTIFACT_NAME
    if path.is_symlink():
        return route, change, package, None, "decision artifact must not be a symlink"
    if not path.exists():
        return route, change, package, None, None
    try:
        if path.stat().st_size > 1_000_000:
            return route, change, package, None, "decision artifact exceeds its size bound"
    except OSError:
        return route, change, package, None, "decision artifact cannot be inspected"
    artifact = _read_json(path)
    if not isinstance(artifact, dict) or set(artifact) != _ARTIFACT_KEYS:
        return route, change, package, None, "decision artifact has an invalid shape"
    if artifact.get("schema_version") != 1 or not isinstance(artifact.get("decisions"), list):
        return route, change, package, None, "decision artifact version or decisions are invalid"
    if artifact.get("route_id") != route.get("route_id") or artifact.get("change_id") != change.get("change_id"):
        return route, change, package, artifact, "decision artifact route/change binding is stale"
    return route, change, package, artifact, None


def _decision_state(
    root: Path,
    gate: str,
    *,
    action: str | None = None,
    resource: str | None = None,
    _aggregate: bool = True,
) -> dict[str, Any]:
    route, change, package, artifact, artifact_error = _valid_artifact(root)
    path = package / ARTIFACT_NAME if package else None
    evidence_path = path.relative_to(root).as_posix() if path else None
    gates, declaration_error = _declared_gates(route)
    current_scope = None
    if package is not None:
        try:
            current_scope = _scope_digest(package)
        except ValueError:
            declaration_error = "approved scope files are unavailable"
    if declaration_error:
        return {"gate": gate, "state": "invalid", "reason": declaration_error, "evidence_path": evidence_path, "scope_digest": current_scope}
    if gate not in GATE_ACTIONS:
        return {"gate": gate, "state": "invalid", "reason": "unknown gate", "evidence_path": evidence_path, "scope_digest": current_scope}
    if gate not in gates:
        return {"gate": gate, "state": "not_required", "reason": "gate is not declared on active route", "evidence_path": evidence_path, "scope_digest": current_scope}
    if artifact_error:
        state = "stale" if "stale" in artifact_error or "binding" in artifact_error else "invalid"
        return {"gate": gate, "state": state, "reason": artifact_error, "evidence_path": evidence_path, "scope_digest": current_scope}
    if artifact is None:
        return {"gate": gate, "state": "pending", "reason": "no explicit decision recorded", "evidence_path": evidence_path, "scope_digest": current_scope}
    assert route is not None and change is not None
    decisions = artifact["decisions"]
    if len(decisions) > 200:
        return {"gate": gate, "state": "invalid", "reason": "decision artifact exceeds its bound", "evidence_path": evidence_path, "scope_digest": current_scope}
    if _aggregate and gate != "scope_and_design_approval" and action is None:
        targets: list[tuple[str | None, str | None]] = []
        for entry in decisions:
            if isinstance(entry, dict) and entry.get("gate") == gate:
                target = (entry.get("action"), entry.get("resource"))
                if target not in targets:
                    targets.append(target)
        if not targets:
            return {"gate": gate, "state": "pending", "reason": "no explicit decision recorded", "evidence_path": evidence_path, "scope_digest": current_scope}
        results = [
            _decision_state(root, gate, action=target_action, resource=target_resource, _aggregate=False)
            for target_action, target_resource in targets
        ]
        valid_states = [item["state"] for item in results]
        if "invalid" in valid_states:
            state = "invalid"
        elif valid_states and all(item == "approved" for item in valid_states):
            state = "approved"
        elif "rejected" in valid_states:
            state = "rejected"
        elif "stale" in valid_states:
            state = "stale"
        else:
            state = "pending"
        return {
            "gate": gate,
            "state": state,
            "reason": "aggregate is approved only when every listed exact target is approved",
            "targets": results,
            "evidence_path": evidence_path,
            "scope_digest": current_scope,
            "notice": ARTIFACT_NOTICE,
        }
    matching: list[dict[str, Any]] = []
    stale = False
    invalid = False
    for entry in decisions:
        if not isinstance(entry, dict) or set(entry) != _DECISION_KEYS:
            invalid = True
            continue
        if entry.get("gate") not in GATE_ACTIONS or entry.get("gate") not in gates:
            invalid = True
            continue
        if (
            entry.get("decision") not in {"approved", "rejected"}
            or not isinstance(entry.get("actor"), str) or not entry["actor"].strip() or len(entry["actor"]) > 128
            or not isinstance(entry.get("reason"), str) or not entry["reason"].strip() or len(entry["reason"]) > 1000
            or not isinstance(entry.get("decided_at"), str)
            or not isinstance(entry.get("scope_digest"), str)
        ):
            invalid = True
            continue
        try:
            datetime.fromisoformat(entry["decided_at"])
        except ValueError:
            invalid = True
            continue
        if entry.get("gate") != gate:
            continue
        if entry.get("route_id") != route.get("route_id") or entry.get("change_id") != change.get("change_id"):
            stale = True
            continue
        if entry.get("scope_digest") != current_scope:
            stale = True
            continue
        if gate == "scope_and_design_approval" and (entry.get("action") is not None or entry.get("resource") is not None):
            invalid = True
            continue
        if gate == "production_action_approval" and (entry.get("action") not in PRODUCTION_ACTIONS or entry.get("resource") is not None):
            invalid = True
            continue
        if gate == "migration_or_external_write_approval":
            target = entry.get("resource")
            plan_approval = entry.get("action") == MIGRATION_PLAN_ACTION and target is None
            external_approval = (
                entry.get("action") in EXTERNAL_ACTIONS
                and isinstance(target, str)
                and bool(target)
                and not any(char in target for char in "*?[")
            )
            if not (plan_approval or external_approval):
                invalid = True
                continue
        if entry.get("action") != action or entry.get("resource") != resource:
            continue
        matching.append(entry)
    if invalid:
        return {"gate": gate, "state": "invalid", "reason": "decision artifact contains malformed entries", "evidence_path": evidence_path, "scope_digest": current_scope}
    if matching:
        # Entries are append-only. The last valid entry for the same exact target
        # is the current decision; earlier entries remain visible as history.
        entry = matching[-1]
        return {
            "gate": gate,
            "state": entry["decision"],
            "reason": entry["reason"],
            "action": entry["action"],
            "resource": entry["resource"],
            "decision_history": [
                {"decision": item["decision"], "decided_at": item["decided_at"], "actor": item["actor"], "reason": item["reason"]}
                for item in matching
            ],
            "scope_digest": current_scope,
            "evidence_path": evidence_path,
            "notice": ARTIFACT_NOTICE,
        }
    if stale:
        state, reason = "stale", "recorded decision no longer matches route, change, or scope"
    elif invalid:
        state, reason = "invalid", "decision artifact contains malformed entries"
    else:
        state, reason = "pending", "no explicit decision recorded for this gate and target"
    return {"gate": gate, "state": state, "reason": reason, "evidence_path": evidence_path, "scope_digest": current_scope}


def gate_statuses(root: Path) -> list[dict[str, Any]]:
    route, _change, _package, context_error = _context(root)
    gates, declaration_error = _declared_gates(route)
    if context_error or declaration_error:
        return [{"gate": gate, "state": "invalid", "reason": context_error or declaration_error, "evidence_path": None} for gate in gates or ["__route_gates__"]]
    return [
        {
            **_decision_state(root, gate),
            "enforcement_scope": GATE_ACTIONS[gate]["description"],
            "local_workflow_evidence_only": True,
        }
        for gate in gates
    ]


def record_gate_decision(
    root: Path,
    gate: str,
    decision: str,
    reason: str,
    *,
    actor: str,
    action: str | None = None,
    resource: str | None = None,
) -> dict[str, Any]:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be explicitly approved or rejected")
    if not isinstance(reason, str) or not isinstance(actor, str) or not reason.strip() or not actor.strip():
        raise ValueError("explicit actor and decision reason are required")
    route, change, package, context_error = _context(root)
    if context_error or route is None or change is None or package is None:
        raise ValueError(context_error or "active route/change is unavailable")
    gates, declaration_error = _declared_gates(route)
    if declaration_error:
        raise ValueError(declaration_error)
    if gate not in GATE_ACTIONS or gate not in gates:
        raise ValueError(f"gate is not declared on active route: {gate}")
    if gate == "scope_and_design_approval" and (action is not None or resource is not None):
        raise ValueError("scope/design decisions cannot bind an action or resource")
    if gate == "production_action_approval" and (action not in PRODUCTION_ACTIONS or resource is not None):
        raise ValueError("production decisions require one supported exact action and no resource")
    if gate == "migration_or_external_write_approval":
        plan_approval = action == MIGRATION_PLAN_ACTION and resource is None
        external_approval = action in EXTERNAL_ACTIONS and isinstance(resource, str) and bool(resource) and not any(char in resource for char in "*?[")
        if not (plan_approval or external_approval):
            raise ValueError("migration gate decisions require migration-plan scope or action=external-write with one exact resource")
    if len(actor.strip()) > 128 or len(reason.strip()) > 1000:
        raise ValueError("actor and reason exceed their bounded lengths")
    path = package / ARTIFACT_NAME
    if path.is_symlink():
        raise ValueError("human gate decision artifact must not be a symlink")
    try:
        if path.exists() and path.stat().st_size > 1_000_000:
            raise ValueError("human gate decision artifact exceeds its size bound")
    except OSError as exc:
        raise ValueError("human gate decision artifact cannot be inspected") from exc
    existing = _read_json(path) if path.exists() else None
    if existing is None and path.exists():
        raise ValueError("existing human gate decision artifact is malformed")
    if existing is None:
        existing = {"schema_version": 1, "change_id": change["change_id"], "route_id": route["route_id"], "decisions": []}
    if not isinstance(existing, dict) or set(existing) != _ARTIFACT_KEYS or existing.get("schema_version") != 1 or not isinstance(existing.get("decisions"), list):
        raise ValueError("existing human gate decision artifact is malformed")
    if existing.get("change_id") != change["change_id"] or existing.get("route_id") != route["route_id"]:
        raise ValueError("existing human gate decision artifact is bound to another route or change")
    scope_digest = _scope_digest(package)
    entry = {
        "gate": gate,
        "decision": decision,
        "route_id": route["route_id"],
        "change_id": change["change_id"],
        "scope_digest": scope_digest,
        "action": action,
        "resource": resource,
        "decided_at": now_utc(),
        "actor": actor.strip(),
        "reason": reason.strip(),
    }
    decisions = [*existing["decisions"], entry]
    if len(decisions) > 200:
        raise ValueError("decision artifact reached its 200-entry bound")
    artifact = {"schema_version": 1, "change_id": change["change_id"], "route_id": route["route_id"], "decisions": decisions}
    atomic_write_text(path, json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {**entry, "evidence_path": path.relative_to(root).as_posix(), "notice": ARTIFACT_NOTICE}


def gate_block_reason(root: Path, scope: str, action: str, resource: str | None = None) -> str | None:
    from .state import get_active_change, get_active_route

    active_change = get_active_change(root)
    route = get_active_route(root)
    if not active_change and isinstance(route, dict):
        gates, declaration_error = _declared_gates(route)
        if declaration_error:
            return declaration_error
        if not gates:
            # No change package means there is no scoped route decision to consume.
            # Preserve existing ungated grant workflows; declared gates still fail closed.
            return None
        return "active change package is required for the route gate declaration"
    route, _change, _package, context_error = _context(root)
    if context_error:
        return context_error
    gates, declaration_error = _declared_gates(route)
    if declaration_error:
        return declaration_error
    if scope == "external-write" and "migration_or_external_write_approval" in gates and not resource:
        return "Route human gate migration_or_external_write_approval requires an exact target resource"
    required: list[str] = []
    if scope == "production" and "production_action_approval" in gates:
        required.append("production_action_approval")
    if scope == "external-write" and "migration_or_external_write_approval" in gates:
        required.append("migration_or_external_write_approval")
    for gate in required:
        status = _decision_state(root, gate, action=action, resource=resource)
        if status.get("state") != "approved":
            return f"Route human gate {gate} is {status.get('state')}: {status.get('reason')}"
    return None


def gate_transition_block_reason(root: Path, target: str, change_id: str | None = None) -> str | None:
    if target != "approved":
        return None
    route, _context_change, _context_package, context_error = _context(root)
    if context_error:
        return context_error
    gates, declaration_error = _declared_gates(route)
    if declaration_error:
        return declaration_error
    _active_route, active_change, _package, context_error = _context(root)
    if ("scope_and_design_approval" in gates or "migration_or_external_write_approval" in gates) and (
        context_error or active_change is None or active_change.get("change_id") != change_id
    ):
        return "route human gates cannot authorize a transition for a non-active change"
    if "scope_and_design_approval" in gates:
        status = _decision_state(root, "scope_and_design_approval")
        if status.get("state") != "approved":
            return f"Route human gate scope_and_design_approval is {status.get('state')}: {status.get('reason')}"
    if "migration_or_external_write_approval" in gates:
        status = _decision_state(root, "migration_or_external_write_approval", action=MIGRATION_PLAN_ACTION)
        if status.get("state") != "approved":
            return f"Route human gate migration_or_external_write_approval is {status.get('state')}: {status.get('reason')}"
    return None


def route_has_gate(root: Path, gate: str) -> bool:
    from .state import get_active_route

    gates, _error = _declared_gates(get_active_route(root))
    return gate in gates
