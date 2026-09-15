"""Explicit server-owned landing resources. Defaults never acquire model credentials."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import stat

from .landing_host_config import _check_ancestry, _private_directory
from .landing_intake import PrivateLandingBlobStore
from .landing_runtime import compose_unavailable_landing, implemented_live_binding
from .landing_service import LandingApplicationService
from .landing_sqlite_store import SQLiteLandingJobStore
from .settings import FactorySettings, SettingsError


@dataclass
class OwnedLandingRuntime:
    service: LandingApplicationService
    store: SQLiteLandingJobStore | None

    def close(self) -> None:
        if self.store is not None:
            self.store.close()


def compose_server_landing(
    settings: FactorySettings, *, repository_root: Path, qwen_env_file: Path | None = None,
    provider_env_file: Path | None = None,
) -> OwnedLandingRuntime | None:
    settings.validate_landing()
    if provider_env_file is not None and qwen_env_file is not None:
        raise SettingsError("select one provider credential file")
    if settings.landing_quarantine_path is None:
        return None
    roots = tuple(path for path in (
        settings.landing_state_path, settings.landing_quarantine_path,
        settings.landing_scratch_path, settings.landing_output_path,
    ) if path is not None)
    # The legacy unavailable/in-memory mode retains its existing root creation.
    if settings.landing_state_path is not None:
        for path in roots:
            _private_directory(path, repository_root=repository_root)
    if settings.landing_live_enabled:
        from .landing_renderer import ExactGitLandingWorkspace

        source = settings.landing_source_path
        if provider_env_file is not None and (
            not provider_env_file.is_absolute() or provider_env_file.anchor == "//" or ".." in provider_env_file.parts
            or any(provider_env_file == root or root in provider_env_file.parents
                   for root in (*roots, source, repository_root) if root is not None)
        ):
            raise SettingsError("provider credential file must be outside landing roots")
        if qwen_env_file is not None and settings.landing_provider.startswith("qwen"):
            if (not qwen_env_file.is_absolute() or qwen_env_file.anchor == "//" or ".." in qwen_env_file.parts
                    or any(qwen_env_file == root or root in qwen_env_file.parents
                           for root in (*roots, source, repository_root) if root is not None)):
                raise SettingsError("Qwen credential file must be outside landing roots")
        _trusted_source(source, repository_root=repository_root)
        ExactGitLandingWorkspace(
            source, scratch_root=settings.landing_scratch_path
        ).validate_source()
    owned_store = None
    try:
        # Acquire the store's process-lifetime writer lock before quarantine
        # startup purges or interrupted-job recovery can affect another process.
        if settings.landing_state_path is not None:
            owned_store = SQLiteLandingJobStore(
                settings.landing_state_path, repository_root=repository_root
            )
        blobs = PrivateLandingBlobStore(
            settings.landing_quarantine_path, repository_root=repository_root
        )
        if not settings.landing_live_enabled:
            service = compose_unavailable_landing(blobs, store=owned_store)
        else:
            from .landing_http import HttpLandingProfile
            from .landing_live_executors import (
                GROK_API_KEY_ENV,
                QWEN_API_KEY_ENV,
                api_key_from_environ,
                qwen_api_key,
                compose_landing_live_grok,
                compose_landing_live_qwen,
                compose_landing_live_provider,
                provider_api_key,
            )

            profile = HttpLandingProfile.for_provider(settings.landing_provider, available=True)
            compose = (
                compose_landing_live_grok if settings.landing_provider in {"grok", "grok-vision"}
                else compose_landing_live_qwen if profile.provider_id == "qwen"
                else compose_landing_live_provider
            )
            key_name = GROK_API_KEY_ENV if settings.landing_provider in {"grok", "grok-vision"} else QWEN_API_KEY_ENV
            # This is runtime-only opt-in acquisition, after all path/source
            # validation and ownership checks. Never persist or log the value.
            service = compose(
                api_key=(provider_api_key(profile.provider_id, env_file=provider_env_file)
                         if provider_env_file is not None or profile.provider_id not in {"qwen", "grok"}
                         else api_key_from_environ(key_name) if profile.provider_id == "grok"
                         else qwen_api_key(env_file=qwen_env_file)),
                binding=implemented_live_binding(enabled=True),
                profile=profile,
                source_repository=settings.landing_source_path,
                scratch_root=settings.landing_scratch_path,
                output_directory=settings.landing_output_path,
                blobs=blobs, store=owned_store,
            )
        return OwnedLandingRuntime(service, owned_store)
    except BaseException:
        if owned_store is not None:
            owned_store.close()
        raise


def _trusted_source(path: Path, *, repository_root: Path) -> None:
    _check_ancestry(path)
    if path == repository_root or repository_root in path.parents or path in repository_root.parents:
        raise SettingsError("landing source must be separate from the control repository")
    metadata = (path / ".git").lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise SettingsError("landing source must be an independent checkout")
