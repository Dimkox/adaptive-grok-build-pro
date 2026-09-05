"""Explicit, default-unavailable command line boundary for the live pilot."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Callable, Mapping, Sequence, TextIO

from .contracts import HEX64, canonical_json
from .profile import PilotProfileV1, exact_landing_profile


class CliError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeConfig:
    job_id: str
    issue_number: int
    state_root: Path
    workspace_root: Path
    source_repository: Path
    profile: PilotProfileV1


def load_runtime_config(path: Path) -> RuntimeConfig:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CliError("invalid_live_config") from exc
    fields = {
        "schema_version", "job_id", "issue_number", "state_root", "workspace_root",
        "source_repository", "codex_executable", "codex_sha256", "codex_version",
        "model_id", "python_executable", "python_sha256",
    }
    if not isinstance(value, dict) or set(value) != fields or value.get("schema_version") != 1:
        raise CliError("invalid_live_config")
    if len(raw) > 16_384 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}", str(value["job_id"])):
        raise CliError("invalid_live_config")
    issue_number = value["issue_number"]
    if type(issue_number) is not int or not 1 <= issue_number <= 2_147_483_647:
        raise CliError("invalid_live_config")
    paths = tuple(Path(str(value[key])) for key in ("state_root", "workspace_root", "source_repository"))
    if any(not item.is_absolute() or ".." in item.parts for item in paths):
        raise CliError("invalid_live_config")
    for key in ("codex_sha256", "python_sha256"):
        if HEX64.fullmatch(str(value[key])) is None:
            raise CliError("invalid_live_config")
    profile = exact_landing_profile(
        codex_executable=str(value["codex_executable"]),
        codex_sha256=str(value["codex_sha256"]),
        codex_version=str(value["codex_version"]),
        model_id=str(value["model_id"]),
        python_executable=str(value["python_executable"]),
        python_sha256=str(value["python_sha256"]),
    )
    return RuntimeConfig(str(value["job_id"]), issue_number, *paths, profile)


def main(
    argv: Sequence[str] | None = None,
    *,
    live_runner: Callable[[RuntimeConfig], Mapping[str, object]] | None = None,
    stdout: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    parser = argparse.ArgumentParser(prog="python3 -m pilot")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="execute one explicitly enabled host-composed pilot")
    run.add_argument("--live", action="store_true")
    run.add_argument("--config")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command != "run" or not args.live:
        return _emit(output, {"status": "unavailable", "reason": "live_disabled"}, 2)
    if live_runner is None:
        return _emit(output, {"status": "unavailable", "reason": "live_adapter_unavailable"}, 2)
    if not args.config:
        return _emit(output, {"status": "unavailable", "reason": "live_config_required"}, 2)
    try:
        config = load_runtime_config(Path(args.config))
        result = dict(live_runner(config))
        encoded = canonical_json(result)
        if len(encoded) > 65_536:
            raise CliError("live_result")
    except (CliError, TypeError, ValueError) as exc:
        return _emit(output, {"status": "unavailable", "reason": str(exc)}, 2)
    output.write(encoded.decode("utf-8") + "\n")
    return 0


def _emit(output: TextIO, value: Mapping[str, object], status: int) -> int:
    output.write(canonical_json(dict(value)).decode("utf-8") + "\n")
    return status
