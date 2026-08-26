#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.architecture import (  # noqa: E402
    ArchitectureError,
    architecture_digests,
    contract_inventory,
    contract_inventory_digest,
    load_architecture,
    validate_architecture,
    validate_repository_drift,
)
from adaptive_grok.architecture_diagrams import (  # noqa: E402
    artifact_digests,
    compare_generated,
    render_diagrams,
    write_generated,
)
from adaptive_grok.architecture_fitness import diff_architecture, evaluate_fitness  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect executable architecture evidence.")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "summary", "drift"):
        command = commands.add_parser(name)
        command.add_argument("--json", action="store_true")
    diagram = commands.add_parser("diagram")
    diagram.add_argument("--check", action="store_true")
    diagram.add_argument("--json", action="store_true")
    for name in ("diff", "fitness"):
        command = commands.add_parser(name)
        command.add_argument("--base", required=True)
        head = command.add_mutually_exclusive_group(required=True)
        head.add_argument("--head")
        head.add_argument("--worktree", action="store_true")
        command.add_argument("--json", action="store_true")
        if name == "fitness":
            command.add_argument("--pre-risk", choices=("green", "yellow", "red"), default="green")
    return parser


def _emit(value: object, *, as_json: bool) -> None:
    if as_json or not isinstance(value, str):
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(value)


def _diff_payload(diff: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "base_architecture_digest": diff.base_architecture_digest,
        "baseline_introduced": diff.baseline_introduced,
        "changed_paths": list(diff.changed_paths),
        "changes": [dataclasses.asdict(item) for item in diff.changes],
        "artifacts": [dataclasses.asdict(item) for item in diff.artifacts],
        "diff_digest": diff.digest,
        "exact_base_sha": diff.base_sha,
        "head_architecture_digest": diff.head_architecture_digest,
        "head_kind": diff.head_kind,
        "repository_inventory_digest": diff.repository_inventory_digest,
    }
    if diff.head_kind == "commit":
        result["exact_head_sha"] = diff.head_sha
    return result


def _fitness_payload(diff: Any, report: Any) -> dict[str, Any]:
    result = _diff_payload(diff)
    result.update(
        {
            "architecture_evidence_digest": report.evidence_digest,
            "exemption_state": report.exemption_state,
            "fitness_results": [dataclasses.asdict(item) for item in report.results],
            "fitness_status": report.status,
            "required_scopes": list(report.required_scopes),
            "risk_escalation": report.escalation,
            "risk_post": report.post_risk,
            "risk_pre": report.pre_risk,
            "risk_triggers": list(report.triggers),
        }
    )
    return result


def main() -> int:
    args = _parser().parse_args()
    as_json = bool(getattr(args, "json", False))
    try:
        root = Path(args.root).resolve(strict=True)
        snapshot = load_architecture(root)
        if args.command == "validate":
            findings = validate_architecture(snapshot, root)
            payload = {"findings": [dataclasses.asdict(item) for item in findings], "ok": not findings}
            _emit(payload, as_json=as_json)
            return 0 if not findings else 1
        if args.command == "summary":
            digests = architecture_digests(snapshot)
            contracts = contract_inventory(root, snapshot)
            payload = {
                "architecture_id": snapshot.system["architecture_id"],
                "contract_count": len(contracts),
                "contract_inventory_digest": contract_inventory_digest(contracts),
                "edge_count": len(snapshot.system["edges"]),
                "node_count": len(snapshot.system["nodes"]),
                "rule_count": sum(len(snapshot.rules[name]) for name in snapshot.rules if isinstance(snapshot.rules[name], list)),
                "trust_domain_count": len(snapshot.system["trust_domains"]),
                **digests,
            }
            _emit(payload, as_json=as_json)
            return 0
        if args.command == "diagram":
            rendered = render_diagrams(snapshot)
            mismatches = compare_generated(root, rendered)
            if not args.check:
                written = write_generated(root, rendered)
                mismatches = ()
            else:
                written = ()
            payload = {
                "checked": bool(args.check),
                "digests": artifact_digests(rendered),
                "mismatches": list(mismatches),
                "ok": not mismatches,
                "written": list(written),
            }
            _emit(payload, as_json=as_json)
            return 0 if not mismatches else 1
        if args.command == "drift":
            findings = validate_repository_drift(root, snapshot)
            payload = {"findings": [dataclasses.asdict(item) for item in findings], "ok": not findings}
            _emit(payload, as_json=as_json)
            return 0 if not findings else 1

        diff = diff_architecture(
            root,
            base_sha=args.base,
            head_sha=args.head,
            worktree=bool(args.worktree),
        )
        if args.command == "diff":
            _emit(_diff_payload(diff), as_json=as_json)
            return 0
        report = evaluate_fitness(
            root,
            diff._head_state.snapshot,
            diff,
            diff.changed_paths,
            pre_risk=args.pre_risk,
        )
        _emit(_fitness_payload(diff, report), as_json=as_json)
        return 0 if report.status == "pass" else 1
    except (ArchitectureError, OSError, ValueError) as exc:
        payload = {"code": getattr(exc, "code", "io"), "error": str(exc), "ok": False}
        _emit(payload, as_json=True)
        return 2 if getattr(exc, "code", "") in {"git", "io", "missing", "usage"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
