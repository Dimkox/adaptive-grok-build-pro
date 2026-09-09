"""Explicit, default-unavailable command line boundary for the live pilot."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
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
    validation_root: Path
    source_repository: Path
    git_executable: str
    git_sha256: str
    gh_executable: str
    gh_sha256: str
    bwrap_executable: str
    bwrap_sha256: str
    profile: PilotProfileV1


def load_runtime_config(path: Path) -> RuntimeConfig:
    try:
        metadata = path.lstat()
        if (
            not path.is_absolute()
            or not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_nlink != 1
            or metadata.st_mode & 0o077
        ):
            raise CliError("invalid_live_config")
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CliError("invalid_live_config") from exc
    fields = {
        "schema_version", "job_id", "issue_number", "state_root", "workspace_root",
        "validation_root", "source_repository", "provider_mode", "codex_executable",
        "codex_sha256", "codex_version", "model_id", "python_executable",
        "python_sha256", "git_executable", "git_sha256", "gh_executable",
        "gh_sha256", "bwrap_executable", "bwrap_sha256",
    }
    if not isinstance(value, dict) or set(value) != fields or value.get("schema_version") != 2:
        raise CliError("invalid_live_config")
    if len(raw) > 16_384 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}", str(value["job_id"])):
        raise CliError("invalid_live_config")
    issue_number = value["issue_number"]
    if issue_number != 1:
        raise CliError("invalid_live_config")
    paths = tuple(Path(str(value[key])) for key in ("state_root", "workspace_root", "validation_root", "source_repository"))
    if any(not item.is_absolute() or ".." in item.parts for item in paths):
        raise CliError("invalid_live_config")
    if len(set(paths)) != len(paths):
        raise CliError("invalid_live_config")
    for key in ("codex_sha256", "python_sha256", "git_sha256", "gh_sha256", "bwrap_sha256"):
        if HEX64.fullmatch(str(value[key])) is None:
            raise CliError("invalid_live_config")
    for key in ("git_executable", "gh_executable", "bwrap_executable"):
        executable = Path(str(value[key]))
        if not executable.is_absolute() or ".." in executable.parts:
            raise CliError("invalid_live_config")
    profile = exact_landing_profile(
        codex_executable=str(value["codex_executable"]),
        codex_sha256=str(value["codex_sha256"]),
        codex_version=str(value["codex_version"]),
        model_id=str(value["model_id"]),
        python_executable=str(value["python_executable"]),
        python_sha256=str(value["python_sha256"]),
        provider_mode=str(value["provider_mode"]),
    )
    return RuntimeConfig(
        str(value["job_id"]),
        issue_number,
        *paths,
        str(value["git_executable"]),
        str(value["git_sha256"]),
        str(value["gh_executable"]),
        str(value["gh_sha256"]),
        str(value["bwrap_executable"]),
        str(value["bwrap_sha256"]),
        profile,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    phase_runner: Callable[[str, RuntimeConfig], Mapping[str, object]] | None = None,
    stdout: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    parser = argparse.ArgumentParser(prog="python3 -m pilot")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "publish-branch", "publish-proposal"):
        command = subparsers.add_parser(name)
        command.add_argument("--live", action="store_true")
        command.add_argument("--config")
    status = subparsers.add_parser("status")
    status.add_argument("--config")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command != "status" and not args.live:
        return _emit(output, {"status": "unavailable", "reason": "live_disabled"}, 2)
    if not args.config:
        return _emit(output, {"status": "unavailable", "reason": "live_config_required"}, 2)
    try:
        config = load_runtime_config(Path(args.config))
        runner = phase_runner or _default_phase_runner
        result = dict(runner(args.command, config))
        encoded = canonical_json(result)
        if len(encoded) > 65_536:
            raise CliError("live_result")
    except (CliError, TypeError, ValueError) as exc:
        return _emit(output, {"status": "unavailable", "reason": _reason(exc)}, 2)
    except Exception as exc:
        return _emit(output, {"status": "unavailable", "reason": _reason(exc)}, 2)
    output.write(encoded.decode("utf-8") + "\n")
    return 0


def _emit(output: TextIO, value: Mapping[str, object], status: int) -> int:
    output.write(canonical_json(dict(value)).decode("utf-8") + "\n")
    return status


def _default_phase_runner(phase: str, config: RuntimeConfig) -> Mapping[str, object]:
    from .live import run_live_phase

    return run_live_phase(phase, config)


def _reason(exc: Exception) -> str:
    value = str(exc)
    return value if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) else "live_phase_failed"
