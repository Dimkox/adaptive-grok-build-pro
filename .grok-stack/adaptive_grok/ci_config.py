from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_CHECKS = (
    "git-diff-check",
    "secret-scan",
    "contract-structure",
    "sql-safety",
    "ruff",
    "bandit",
    "python-unittest",
    "coverage",
)

DEFAULT_TRUSTED_PATHS = (
    ".grok/**",
    ".grok-stack/**",
    ".github/**",
    "AGENTS.md",
    "decisions.md",
    "mistakes.md",
    "scripts/grok_ci.py",
    "scripts/grok_ci_verify.py",
    "scripts/grok_approve.py",
    "scripts/grok_verify.py",
    "scripts/install_self_hosted_ci.py",
    "scripts/install_into.py",
    "scripts/package_stack.py",
    "ops/self-hosted-ci/**",
    "tests/test_ci_*.py",
    ".coveragerc",
    "ruff.toml",
    "bandit.yaml",
    "VERSION",
)

DEFAULT_APPROVAL_PATH_RULES = {
    "production": (
        "ops/**",
        "infra/**",
        "terraform/**",
        "k8s/**",
        "deploy/**",
        "Dockerfile",
        "docker-compose*.yml",
        "docker-compose*.yaml",
    ),
    "protected-path": ("bitrix/**",),
}


class CIConfigError(ValueError):
    pass


def _resolve(base: Path, raw: Any, default: str) -> Path:
    value = Path(str(raw or default)).expanduser()
    return value.resolve() if value.is_absolute() else (base / value).resolve()


def _strings(raw: Any, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if raw is None:
        return default
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item.strip() for item in raw):
        raise CIConfigError("expected a list of non-empty strings")
    return tuple(dict.fromkeys(item.strip() for item in raw))


def _commands(raw: Any) -> tuple[tuple[str, ...], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise CIConfigError("external_commands must be a list")
    commands: list[tuple[str, ...]] = []
    for command in raw:
        if not isinstance(command, list) or not command or any(not isinstance(part, str) or not part for part in command):
            raise CIConfigError("each external command must be a non-empty argv list")
        commands.append(tuple(command))
    return tuple(commands)


def _approval_rules(raw: Any) -> dict[str, tuple[str, ...]]:
    if raw is None:
        return {scope: tuple(patterns) for scope, patterns in DEFAULT_APPROVAL_PATH_RULES.items()}
    if not isinstance(raw, dict):
        raise CIConfigError("approval_path_rules must be an object")
    result: dict[str, tuple[str, ...]] = {}
    for scope, patterns in raw.items():
        name = str(scope).strip()
        if not name:
            raise CIConfigError("approval scope must be non-empty")
        result[name] = _strings(patterns)
    return result


@dataclass(frozen=True)
class CIConfig:
    source: Path
    database: Path
    artifact_root: Path
    workspace_root: Path
    allowed_signers: Path
    receipt_signing_key: Path | None
    receipt_key_id: str | None
    github_token_env: str
    github_api_url: str
    webhook_secret_file: Path
    webhook_listen_host: str
    webhook_listen_port: int
    allowed_repositories: tuple[str, ...]
    webhook_required_approvals: tuple[str, ...]
    approval_path_rules: dict[str, tuple[str, ...]]
    status_context: str
    status_target_url: str | None
    default_branch: str
    lease_seconds: int
    poll_seconds: float
    max_attempts: int
    verification_mode: str
    verification_profiles: tuple[str, ...]
    required_checks: tuple[str, ...]
    trusted_paths: tuple[str, ...]
    external_commands: tuple[tuple[str, ...], ...]
    pass_environment: tuple[str, ...]
    sandbox_user: str
    sandbox_group: str
    require_root_controller: bool
    digest: str

    def is_trusted_path(self, path: str) -> bool:
        normalized = path.replace("\\", "/").lstrip("./")
        return any(
            fnmatch.fnmatchcase(normalized, pattern.replace("\\", "/").lstrip("./"))
            for pattern in self.trusted_paths
        )

    def approval_scopes_for_paths(self, paths: list[str]) -> set[str]:
        normalized = [path.replace("\\", "/").lstrip("./") for path in paths]
        scopes: set[str] = set()
        for scope, patterns in self.approval_path_rules.items():
            if any(fnmatch.fnmatchcase(path, pattern) for path in normalized for pattern in patterns):
                scopes.add(scope)
        return scopes


def load_ci_config(path: str | Path) -> CIConfig:
    source = Path(path).expanduser().resolve()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CIConfigError(f"cannot read trusted CI config: {source}") from exc
    if not isinstance(raw, dict):
        raise CIConfigError("trusted CI config root must be an object")
    base = source.parent

    lease_seconds = int(raw.get("lease_seconds", 1800))
    poll_seconds = float(raw.get("poll_seconds", 5))
    max_attempts = int(raw.get("max_attempts", 3))
    port = int(raw.get("webhook_listen_port", 8787))
    if lease_seconds < 60:
        raise CIConfigError("lease_seconds must be at least 60")
    if poll_seconds < 0.1:
        raise CIConfigError("poll_seconds must be at least 0.1")
    if max_attempts < 1:
        raise CIConfigError("max_attempts must be at least 1")
    if not 1 <= port <= 65535:
        raise CIConfigError("webhook_listen_port must be between 1 and 65535")
    mode = str(raw.get("verification_mode", "pr"))
    if mode not in {"fast", "pr", "release"}:
        raise CIConfigError("verification_mode must be fast, pr, or release")

    key_raw = raw.get("receipt_signing_key")
    signing_key = _resolve(base, key_raw, str(key_raw)) if isinstance(key_raw, str) and key_raw else None
    key_id = str(raw.get("receipt_key_id") or "").strip() or None
    if bool(signing_key) != bool(key_id):
        raise CIConfigError("receipt_signing_key and receipt_key_id must be configured together")

    normalized: dict[str, Any] = {
        "database": str(_resolve(base, raw.get("database"), "/var/lib/adaptive-grok-ci/state.sqlite3")),
        "artifact_root": str(_resolve(base, raw.get("artifact_root"), "/var/lib/adaptive-grok-ci/artifacts")),
        "workspace_root": str(_resolve(base, raw.get("workspace_root"), "/var/lib/adaptive-grok-ci/workspaces")),
        "allowed_signers": str(_resolve(base, raw.get("allowed_signers"), "/etc/adaptive-grok-ci/allowed-signers.json")),
        "receipt_signing_key": str(signing_key) if signing_key else None,
        "receipt_key_id": key_id,
        "github_token_env": str(raw.get("github_token_env", "ADAPTIVE_GROK_GITHUB_TOKEN")).strip(),
        "github_api_url": str(raw.get("github_api_url", "https://api.github.com")).rstrip("/"),
        "webhook_secret_file": str(_resolve(base, raw.get("webhook_secret_file"), "/etc/adaptive-grok-ci/webhook.secret")),
        "webhook_listen_host": str(raw.get("webhook_listen_host", "127.0.0.1")).strip(),
        "webhook_listen_port": port,
        "allowed_repositories": _strings(raw.get("allowed_repositories")),
        "webhook_required_approvals": _strings(raw.get("webhook_required_approvals")),
        "approval_path_rules": _approval_rules(raw.get("approval_path_rules")),
        "status_context": str(raw.get("status_context", "adaptive-grok-ci/trusted")).strip(),
        "status_target_url": str(raw.get("status_target_url")).strip() if raw.get("status_target_url") else None,
        "default_branch": str(raw.get("default_branch", "main")).strip(),
        "lease_seconds": lease_seconds,
        "poll_seconds": poll_seconds,
        "max_attempts": max_attempts,
        "verification_mode": mode,
        "verification_profiles": _strings(raw.get("verification_profiles"), ("base",)),
        "required_checks": _strings(raw.get("required_checks"), DEFAULT_REQUIRED_CHECKS),
        "trusted_paths": _strings(raw.get("trusted_paths"), DEFAULT_TRUSTED_PATHS),
        "external_commands": _commands(raw.get("external_commands")),
        "pass_environment": _strings(raw.get("pass_environment")),
        "sandbox_user": str(raw.get("sandbox_user", "adaptive-grok-ci-job")).strip(),
        "sandbox_group": str(raw.get("sandbox_group", "adaptive-grok-ci-job")).strip(),
        "require_root_controller": bool(raw.get("require_root_controller", True)),
    }
    for key in ("github_token_env", "webhook_listen_host", "status_context", "default_branch", "sandbox_user", "sandbox_group"):
        if not normalized[key]:
            raise CIConfigError(f"{key} is required")
    digest = hashlib.sha256(
        (json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()

    return CIConfig(
        source=source,
        database=Path(normalized["database"]),
        artifact_root=Path(normalized["artifact_root"]),
        workspace_root=Path(normalized["workspace_root"]),
        allowed_signers=Path(normalized["allowed_signers"]),
        receipt_signing_key=signing_key,
        receipt_key_id=key_id,
        github_token_env=normalized["github_token_env"],
        github_api_url=normalized["github_api_url"],
        webhook_secret_file=Path(normalized["webhook_secret_file"]),
        webhook_listen_host=normalized["webhook_listen_host"],
        webhook_listen_port=port,
        allowed_repositories=normalized["allowed_repositories"],
        webhook_required_approvals=normalized["webhook_required_approvals"],
        approval_path_rules=normalized["approval_path_rules"],
        status_context=normalized["status_context"],
        status_target_url=normalized["status_target_url"],
        default_branch=normalized["default_branch"],
        lease_seconds=lease_seconds,
        poll_seconds=poll_seconds,
        max_attempts=max_attempts,
        verification_mode=mode,
        verification_profiles=normalized["verification_profiles"],
        required_checks=normalized["required_checks"],
        trusted_paths=normalized["trusted_paths"],
        external_commands=normalized["external_commands"],
        pass_environment=normalized["pass_environment"],
        sandbox_user=normalized["sandbox_user"],
        sandbox_group=normalized["sandbox_group"],
        require_root_controller=normalized["require_root_controller"],
        digest=digest,
    )
