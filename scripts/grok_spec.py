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
    canonical_spec_digest,
    criterion_coverage,
    dump_canonical_spec,
    generate_spec,
    load_spec,
    map_evidence,
    spec_fingerprint,
    summarize_spec,
    validate_spec,
)
from adaptive_grok.state import get_active_change, get_active_route  # noqa: E402
from adaptive_grok.util import atomic_write_text, find_root  # noqa: E402


def _change_id(root: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    active = get_active_change(root) or {}
    route = get_active_route(root) or {}
    value = active.get("change_id") or route.get("change_id")
    if not value:
        raise SpecError("no active change id", code="usage")
    return str(value)


def _spec_path(root: Path, explicit_path: str | None, change_id: str | None) -> Path:
    if explicit_path:
        candidate = Path(explicit_path)
        candidate = candidate if candidate.is_absolute() else root / candidate
    else:
        candidate = root / "engineering" / "changes" / _change_id(root, change_id) / "change-spec.yaml"
    try:
        candidate.resolve(strict=False).relative_to(root.resolve())
    except ValueError as exc:
        raise SpecError("spec path must stay inside repository", code="usage") from exc
    return candidate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and inspect typed change specifications.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "summary", "summarize", "coverage", "map"):
        command = sub.add_parser(name)
        command.add_argument("path", nargs="?")
        command.add_argument("--change-id")
        command.add_argument("--json", action="store_true")
        if name == "validate":
            command.add_argument("--gate", action="store_true")
            command.add_argument("--schema-only", action="store_true", help=argparse.SUPPRESS)
    generate = sub.add_parser("generate")
    generate.add_argument("--change-id")
    generate.add_argument("--json", action="store_true")
    return parser


def _emit(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))


def main() -> int:
    args = _parser().parse_args()
    try:
        root = find_root(ROOT)
        route = get_active_route(root) or {}
        if args.command == "generate":
            change_id = _change_id(root, args.change_id)
            generated = generate_spec({**route, "change_id": change_id})
            path = _spec_path(root, None, change_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, dump_canonical_spec(generated))
            _emit({"change_id": change_id, "generated": True, "ok": True, "path": path.relative_to(root).as_posix()})
            return 0

        path = _spec_path(root, args.path, args.change_id)
        if not path.is_file():
            raise SpecError(f"missing spec: {path}", code="io")
        spec = load_spec(path, allow_legacy=args.command != "validate")
        if args.command == "validate":
            gate = bool(args.gate and not args.schema_only)
            errors = validate_spec(root, path, gate=gate, route=route)
            result = {
                "ok": not errors,
                "path": path.relative_to(root).as_posix(),
                "profile": "gate" if gate else "draft",
                "errors": errors,
                "digest": canonical_spec_digest(spec),
                "coverage": criterion_coverage(spec),
            }
            if not errors:
                result["fingerprint"] = spec_fingerprint(root, path, spec, route)
            _emit(result)
            return 0 if not errors else 1
        if args.command in {"summary", "summarize"}:
            _emit(summarize_spec(spec))
        elif args.command == "coverage":
            _emit(criterion_coverage(spec))
        else:
            _emit(map_evidence(spec))
        return 0
    except SpecError as exc:
        _emit({"code": exc.code, "error": str(exc), "ok": False})
        return 2 if exc.code in {"usage", "io"} else 1
    except OSError as exc:
        _emit({"code": "io", "error": str(exc), "ok": False})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
