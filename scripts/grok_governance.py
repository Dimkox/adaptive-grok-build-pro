#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.governance import (  # noqa: E402
    GovernanceError,
    build_governance_handoff,
    governance_summary,
    load_architecture_evidence,
    load_governance,
    render_markdown_projections,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and project controlled governance evidence."
    )
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "summary"):
        command = commands.add_parser(name)
        command.add_argument("--now")
        command.add_argument("--json", action="store_true")
    handoff = commands.add_parser("handoff")
    handoff.add_argument("--base", required=True)
    handoff.add_argument("--head", required=True)
    handoff.add_argument("--architecture-evidence", required=True)
    handoff.add_argument("--now")
    handoff.add_argument("--json", action="store_true")
    for name in ("project", "check-projections"):
        command = commands.add_parser(name)
        command.add_argument("--now")
    return parser


def _evaluation_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if not value.endswith("Z"):
        raise GovernanceError("--now must be an RFC3339 UTC Z timestamp", code="usage")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise GovernanceError(
            "--now must be an RFC3339 UTC Z timestamp", code="usage"
        ) from exc
    return parsed.astimezone(timezone.utc)


def _emit(value: object) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )


def _merge_projection(existing: str, projection: str, *, name: str) -> str:
    begin = f"<!-- BEGIN ADAPTIVE GROK GOVERNANCE PROJECTION: {name} -->"
    end = f"<!-- END ADAPTIVE GROK GOVERNANCE PROJECTION: {name} -->"
    begin_count = existing.count(begin)
    end_count = existing.count(end)
    if begin_count != end_count or begin_count > 1:
        raise GovernanceError(
            f"{name}: governance projection markers are malformed", code="projection"
        )
    if begin_count == 1:
        start = existing.index(begin)
        finish = existing.index(end, start) + len(end)
        if finish < len(existing) and existing[finish : finish + 1] == "\n":
            finish += 1
        return existing[:start] + projection + existing[finish:]
    first_newline = existing.find("\n")
    if first_newline < 0:
        return existing + "\n\n" + projection
    insertion = first_newline + 1
    return existing[:insertion] + "\n" + projection + existing[insertion:]


def _projection_payload(
    root: Path,
    projections: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    proposed: dict[str, str] = {}
    digests: dict[str, str] = {}
    for name in sorted(projections):
        path = root / name
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise GovernanceError(f"cannot read {name}", code="io") from exc
        content = _merge_projection(existing, projections[name], name=name)
        proposed[name] = content
        digests[name] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return proposed, digests


def main() -> int:
    args = _parser().parse_args()
    try:
        root = Path(args.root).resolve(strict=True)
        now = _evaluation_time(getattr(args, "now", None))
        snapshot = load_governance(root)
        if args.command in {"validate", "summary"}:
            summary = governance_summary(snapshot, now=now)
            if args.command == "summary":
                _emit(summary)
            else:
                _emit(
                    {
                        "findings": summary["findings"],
                        "governance_digest": summary["governance_digest"],
                        "ok": summary["ok"],
                        "overall_status": summary["overall_status"],
                    }
                )
            return 0 if summary["ok"] else 1
        if args.command == "handoff":
            architecture = load_architecture_evidence(args.architecture_evidence)
            handoff = build_governance_handoff(
                snapshot,
                architecture=architecture,
                base_sha=args.base,
                head_sha=args.head,
                now=now,
            )
            _emit(handoff.to_dict())
            return 0
        projections = render_markdown_projections(snapshot, now=now)
        proposed, digests = _projection_payload(root, projections)
        if args.command == "project":
            _emit(
                {
                    "digests": digests,
                    "mutated": False,
                    "projections": proposed,
                }
            )
            return 0
        mismatches = sorted(
            name
            for name, content in proposed.items()
            if (root / name).read_text(encoding="utf-8") != content
        )
        _emit(
            {
                "digests": digests,
                "mismatches": mismatches,
                "mutated": False,
                "ok": not mismatches,
            }
        )
        return 0 if not mismatches else 1
    except GovernanceError as exc:
        _emit({"code": exc.code, "error": str(exc), "ok": False})
        return 2 if exc.code in {"git", "io", "usage"} else 1
    except OSError as exc:
        _emit({"code": "io", "error": str(exc), "ok": False})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
