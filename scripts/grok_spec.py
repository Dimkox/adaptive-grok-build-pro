#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.spec import (  # noqa: E402
    SpecError,
    dump_yaml_subset,
    generate_spec,
    load_schema,
    load_spec,
    map_evidence,
    summarize_spec,
    validate_spec,
)
from adaptive_grok.state import get_active_route  # noqa: E402
from adaptive_grok.util import find_root  # noqa: E402


def _change_dir(root: Path, change_id: str) -> Path:
    return root / "engineering" / "changes" / change_id


def _resolve_change_id(root: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    route = get_active_route(root) or {}
    change_id = route.get("change_id")
    if not change_id:
        raise SpecError("no active change id", code="usage")
    return str(change_id)


def _spec_path(root: Path, change_id: str, override: str | None) -> Path:
    if override:
        return Path(override)
    return _change_dir(root, change_id) / "change-spec.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and generate typed change specs.")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--change-id")
    validate.add_argument("--path")
    validate.add_argument("--schema-only", action="store_true")
    generate = sub.add_parser("generate")
    generate.add_argument("--change-id")
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--change-id")
    mapped = sub.add_parser("map")
    mapped.add_argument("--change-id")
    args = parser.parse_args()
    try:
        root = find_root(ROOT)
        if args.command == "generate":
            route = get_active_route(root) or {}
            if args.change_id:
                route = {**route, "change_id": args.change_id}
            if not route.get("change_id"):
                raise SpecError("no active change id", code="usage")
            spec = generate_spec(route)
            path = _spec_path(root, str(route["change_id"]), None)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(dump_yaml_subset(spec), encoding="utf-8")
            result = {"ok": True, "path": str(path), "change_id": spec["change_id"], "generated": True}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        change_id = _resolve_change_id(root, args.change_id)
        path = _spec_path(root, change_id, getattr(args, "path", None))
        if not path.is_file():
            raise SpecError(f"missing spec: {path}", code="io")
        spec = load_spec(path)
        if args.command == "validate":
            result = validate_spec(spec, load_schema(), schema_only=args.schema_only)
            result["path"] = str(path)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "summarize":
            print(json.dumps(summarize_spec(spec), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(map_evidence(spec), ensure_ascii=False, indent=2))
        return 0
    except SpecError as exc:
        payload = {"ok": False, "error": str(exc), "code": exc.code}
        print(json.dumps(payload, ensure_ascii=False))
        return 2 if exc.code in {"usage", "io"} else 1
    except OSError as exc:
        payload = {"ok": False, "error": str(exc), "code": "io"}
        print(json.dumps(payload, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
