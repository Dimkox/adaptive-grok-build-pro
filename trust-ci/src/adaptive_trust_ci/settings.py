from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path


_IMAGE_DIGEST_RE = re.compile(r'^(?:sha256:[0-9a-f]{64}|.+@sha256:[0-9a-f]{64})$')


class SettingsError(ValueError):
    pass


def _required(name: str) -> str:
    value = os.environ.get(name, '').strip()
    if not value:
        raise SettingsError(f'required environment variable is missing: {name}')
    return value


def _float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f'{name} must be numeric') from exc
    if not minimum <= value <= maximum:
        raise SettingsError(f'{name} must be between {minimum} and {maximum}')
    return value


def _int(name: str, minimum: int = 1) -> int:
    raw = _required(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f'{name} must be an integer') from exc
    if value < minimum:
        raise SettingsError(f'{name} must be >= {minimum}')
    return value


def _optional_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f'{name} must be an integer') from exc
    if not minimum <= value <= maximum:
        raise SettingsError(f'{name} must be between {minimum} and {maximum}')
    return value


def _immutable_image(name: str) -> str:
    value = _required(name)
    if not _IMAGE_DIGEST_RE.fullmatch(value):
        raise SettingsError(f'{name} must be an immutable image reference with sha256 digest')
    return value


@dataclass(frozen=True)
class CommonSettings:
    database_url: str
    policy_path: Path
    public_base_url: str
    kill_switch_path: Path

    @classmethod
    def load(cls) -> 'CommonSettings':
        public_base_url = _required('TRUST_CI_PUBLIC_BASE_URL').rstrip('/')
        if not public_base_url.startswith(('https://', 'http://localhost', 'http://127.0.0.1')):
            raise SettingsError('TRUST_CI_PUBLIC_BASE_URL must be HTTPS outside localhost')
        return cls(
            database_url=_required('TRUST_CI_DATABASE_URL'),
            policy_path=Path(_required('TRUST_CI_POLICY_PATH')).resolve(),
            public_base_url=public_base_url,
            kill_switch_path=Path(os.environ.get('TRUST_CI_KILL_SWITCH_PATH', '/run/adaptive-trust-ci/STOP')).resolve(),
        )

    @property
    def stopped(self) -> bool:
        return self.kill_switch_path.exists()


@dataclass(frozen=True)
class ApiSettings:
    common: CommonSettings
    webhook_secret: str
    trust_store_path: Path
    read_token: str
    promotion_environment: str = 'production'
    promotion_max_ttl_seconds: int = 900
    promotion_rate_limit_per_minute: int = 60
    deployer_token: str = ''
    deployer_database_url: str = ''
    promotion_manifest_path: Path | None = None
    promotion_artifact_path: Path | None = None
    promotion_manifest_sha256: str = ''
    promotion_consume_rate_limit_per_minute: int = 60
    protected_ref: str = 'refs/heads/main'

    def __post_init__(self) -> None:
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', self.promotion_environment):
            raise SettingsError('promotion environment must be a lowercase identifier')
        if (
            type(self.promotion_max_ttl_seconds) is not int
            or not 60 <= self.promotion_max_ttl_seconds <= 3600
        ):
            raise SettingsError('promotion maximum TTL must be between 60 and 3600 seconds')
        if (
            type(self.promotion_rate_limit_per_minute) is not int
            or not 1 <= self.promotion_rate_limit_per_minute <= 10_000
        ):
            raise SettingsError('promotion rate limit must be between 1 and 10000 per minute')
        if self.deployer_token and (
            self.deployer_token != self.deployer_token.strip()
            or not 16 <= len(self.deployer_token.encode('utf-8')) <= 512
            or any(ord(character) < 32 or ord(character) == 127 for character in self.deployer_token)
        ):
            raise SettingsError('deployer token must be between 16 and 512 safe UTF-8 bytes')
        if (self.promotion_manifest_path is None) != (self.promotion_artifact_path is None):
            raise SettingsError('promotion manifest and artifact paths must be configured together')
        if self.promotion_manifest_path is not None and not re.fullmatch(
            r'[0-9a-f]{64}', self.promotion_manifest_sha256
        ):
            raise SettingsError('promotion manifest SHA-256 must be configured canonically')
        if self.promotion_manifest_path is None and self.promotion_manifest_sha256:
            raise SettingsError('promotion manifest SHA-256 requires promotion paths')
        if (
            type(self.promotion_consume_rate_limit_per_minute) is not int
            or not 1 <= self.promotion_consume_rate_limit_per_minute <= 10_000
        ):
            raise SettingsError('promotion consume rate limit must be between 1 and 10000 per minute')
        _validate_protected_ref(self.protected_ref)

    @classmethod
    def load(cls) -> 'ApiSettings':
        return cls(
            common=CommonSettings.load(),
            webhook_secret=_required('TRUST_CI_WEBHOOK_SECRET'),
            trust_store_path=Path(_required('TRUST_CI_TRUST_STORE_PATH')).resolve(),
            read_token=_required('TRUST_CI_READ_TOKEN'),
            promotion_environment=os.environ.get(
                'TRUST_CI_PROMOTION_ENVIRONMENT', 'production'
            ).strip(),
            promotion_max_ttl_seconds=_optional_int(
                'TRUST_CI_PROMOTION_MAX_TTL_SECONDS', 900, 60, 3600
            ),
            promotion_rate_limit_per_minute=_optional_int(
                'TRUST_CI_PROMOTION_RATE_LIMIT_PER_MINUTE', 60, 1, 10_000
            ),
            deployer_token=_required('TRUST_CI_DEPLOYER_TOKEN'),
            deployer_database_url=_required('TRUST_CI_DEPLOYER_DATABASE_URL'),
            promotion_manifest_path=Path(
                _required('TRUST_CI_PROMOTION_MANIFEST_PATH')
            ).resolve(),
            promotion_artifact_path=Path(
                _required('TRUST_CI_PROMOTION_ARTIFACT_PATH')
            ).resolve(),
            promotion_manifest_sha256=_required(
                'TRUST_CI_PROMOTION_MANIFEST_SHA256'
            ),
            promotion_consume_rate_limit_per_minute=_optional_int(
                'TRUST_CI_PROMOTION_CONSUME_RATE_LIMIT_PER_MINUTE', 60, 1, 10_000
            ),
            protected_ref=_protected_ref(),
        )


@dataclass(frozen=True)
class WorkerSettings:
    common: CommonSettings
    ci_signing_key_path: Path
    github_app_id: int
    github_installation_id: int
    github_app_private_key_path: Path
    runner_image: str
    workspace_root: Path
    workspace_host_root: Path
    holdout_host_path: Path
    worker_id: str
    poll_interval_seconds: float
    protected_ref: str
    protected_repository: str
    protected_repository_id: int
    supply_chain_dir: Path
    protected_artifact_path: Path
    cosign_public_key_path: Path
    reconciliation_interval_seconds: float

    @classmethod
    def load(cls) -> 'WorkerSettings':
        workspace_root = Path(os.environ.get('TRUST_CI_WORKSPACE_ROOT', '/var/lib/adaptive-trust-ci/workspaces')).resolve()
        workspace_host_root = Path(_required('TRUST_CI_WORKSPACE_HOST_ROOT'))
        holdout_host_path = Path(_required('TRUST_CI_HOLDOUT_HOST_PATH'))
        if not workspace_host_root.is_absolute() or not holdout_host_path.is_absolute():
            raise SettingsError('Docker daemon paths must be absolute')
        worker_id = os.environ.get('TRUST_CI_WORKER_ID', f'{socket.gethostname()}-{os.getpid()}').strip()
        if not worker_id:
            raise SettingsError('TRUST_CI_WORKER_ID cannot be empty')
        return cls(
            common=CommonSettings.load(),
            ci_signing_key_path=Path(_required('TRUST_CI_SIGNING_KEY_PATH')).resolve(),
            github_app_id=_int('TRUST_CI_GITHUB_APP_ID'),
            github_installation_id=_int('TRUST_CI_GITHUB_INSTALLATION_ID'),
            github_app_private_key_path=Path(_required('TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH')).resolve(),
            runner_image=_immutable_image('TRUST_CI_RUNNER_IMAGE'),
            workspace_root=workspace_root,
            workspace_host_root=workspace_host_root,
            holdout_host_path=holdout_host_path,
            worker_id=worker_id,
            poll_interval_seconds=_float('TRUST_CI_POLL_INTERVAL_SECONDS', 2.0, 0.1, 300.0),
            protected_ref=_protected_ref(),
            protected_repository=_required('TRUST_CI_PROTECTED_REPOSITORY').lower(),
            protected_repository_id=_int('TRUST_CI_PROTECTED_REPOSITORY_ID'),
            supply_chain_dir=Path(_required('TRUST_CI_SUPPLY_CHAIN_DIR')).resolve(),
            protected_artifact_path=Path(
                _required('TRUST_CI_PROTECTED_ARTIFACT_PATH')
            ).resolve(),
            cosign_public_key_path=Path(
                _required('TRUST_CI_COSIGN_PUBLIC_KEY_PATH')
            ).resolve(),
            reconciliation_interval_seconds=_float(
                'TRUST_CI_RECONCILIATION_INTERVAL_SECONDS', 60.0, 10.0, 3600.0
            ),
        )


def _validate_protected_ref(value: str) -> str:
    if (
        not isinstance(value, str) or not value.startswith('refs/heads/')
        or value == 'refs/heads/' or len(value.encode('utf-8')) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise SettingsError('protected ref must be an immutable refs/heads/* value')
    return value


def _protected_ref() -> str:
    return _validate_protected_ref(_required('TRUST_CI_PROTECTED_REF'))
