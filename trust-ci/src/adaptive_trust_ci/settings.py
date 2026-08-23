from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path


class SettingsError(ValueError):
    pass


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SettingsError(f"required environment variable is missing: {name}")
    return value


def _float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be numeric") from exc
    if not minimum <= value <= maximum:
        raise SettingsError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class CommonSettings:
    database_url: str
    policy_path: Path
    github_token: str
    public_base_url: str
    kill_switch_path: Path

    @classmethod
    def load(cls) -> "CommonSettings":
        public_base_url = _required("TRUST_CI_PUBLIC_BASE_URL").rstrip("/")
        if not public_base_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise SettingsError("TRUST_CI_PUBLIC_BASE_URL must be HTTPS outside localhost")
        return cls(
            database_url=_required("TRUST_CI_DATABASE_URL"),
            policy_path=Path(_required("TRUST_CI_POLICY_PATH")).resolve(),
            github_token=_required("TRUST_CI_GITHUB_TOKEN"),
            public_base_url=public_base_url,
            kill_switch_path=Path(os.environ.get("TRUST_CI_KILL_SWITCH_PATH", "/run/adaptive-trust-ci/STOP")).resolve(),
        )

    @property
    def stopped(self) -> bool:
        return self.kill_switch_path.exists()


@dataclass(frozen=True)
class ApiSettings:
    common: CommonSettings
    webhook_secret: str
    trust_store_path: Path

    @classmethod
    def load(cls) -> "ApiSettings":
        return cls(
            common=CommonSettings.load(),
            webhook_secret=_required("TRUST_CI_WEBHOOK_SECRET"),
            trust_store_path=Path(_required("TRUST_CI_TRUST_STORE_PATH")).resolve(),
        )


@dataclass(frozen=True)
class WorkerSettings:
    common: CommonSettings
    ci_signing_key_path: Path
    workspace_root: Path
    worker_id: str
    poll_interval_seconds: float

    @classmethod
    def load(cls) -> "WorkerSettings":
        workspace_root = Path(os.environ.get("TRUST_CI_WORKSPACE_ROOT", "/var/lib/adaptive-trust-ci/workspaces")).resolve()
        worker_id = os.environ.get("TRUST_CI_WORKER_ID", f"{socket.gethostname()}-{os.getpid()}").strip()
        if not worker_id:
            raise SettingsError("TRUST_CI_WORKER_ID cannot be empty")
        return cls(
            common=CommonSettings.load(),
            ci_signing_key_path=Path(_required("TRUST_CI_SIGNING_KEY_PATH")).resolve(),
            workspace_root=workspace_root,
            worker_id=worker_id,
            poll_interval_seconds=_float("TRUST_CI_POLL_INTERVAL_SECONDS", 2.0, 0.1, 300.0),
        )
