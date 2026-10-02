"""Pinned, side-effect-free model registry for the optional v1.5 rotator.

This module records selection facts only.  It deliberately owns no provider
client, process, settings, credential, persistence, or command-line surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping


_MODELS = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "poolside/laguna-s-2.1:free",
    "cohere/north-mini-code:free",
    "dots-studio/dots-3-note-preview:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "openrouter/free",
)
_REPOSITORY = "https://github.com/Dimkox/qwen-model-rotator"
_COMMIT = "27955ebaca6bb3390de841a516ec1d0bf728ac09"
_TREE_SHA1 = "c558dfc97cc55b25a49479b04182d77d8a2b85b0"
_ARCHIVE_KIND = "github_api_tarball"
_ARCHIVE_URL = f"https://api.github.com/repos/Dimkox/qwen-model-rotator/tarball/{_COMMIT}"
# SHA-256 of the exact response bytes fetched from _ARCHIVE_URL, not of a
# locally regenerated ``git archive`` (whose representation is different).
_ARCHIVE_SHA256 = "2ac88782216333dedcee6db30c2e3f885017100951af782934baf241b50b12b9"
_MODELS_FILE_SHA256 = "cf2e502a8af917d77bd6710d1eb3a68377f72c0c9e839c3479a5ed19c4d21b20"


@dataclass(frozen=True, slots=True)
class RotatorUpstream:
    repository: str
    commit: str
    tree_sha1: str
    archive_kind: str
    archive_url: str
    archive_sha256: str
    models_file: str
    models_file_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "repository": self.repository,
            "commit": self.commit,
            "tree_sha1": self.tree_sha1,
            "archive_kind": self.archive_kind,
            "archive_url": self.archive_url,
            "archive_sha256": self.archive_sha256,
            "models_file": self.models_file,
            "models_file_sha256": self.models_file_sha256,
        }


_UPSTREAM = RotatorUpstream(
    repository=_REPOSITORY,
    commit=_COMMIT,
    tree_sha1=_TREE_SHA1,
    archive_kind=_ARCHIVE_KIND,
    archive_url=_ARCHIVE_URL,
    archive_sha256=_ARCHIVE_SHA256,
    models_file="models.txt",
    models_file_sha256=_MODELS_FILE_SHA256,
)


@dataclass(frozen=True, slots=True)
class ModelRotatorRegistry:
    """An immutable snapshot; activation and execution belong to later slices."""

    enabled: bool
    dashscope_enabled: bool
    free_claim: None
    models: tuple[str, ...]
    upstream: RotatorUpstream
    schema_version: str = "model-rotator-registry.v1"
    provider: str = "openrouter"
    selection_strategy: str = "best_first"
    selection_strategy_version: str = "best_first.v1"

    def __post_init__(self) -> None:
        if self.enabled or self.dashscope_enabled or self.free_claim is not None:
            raise ValueError("the registry snapshot must remain default-off and make no free claim")
        if self.models != _MODELS:
            raise ValueError("models must match the pinned upstream best-first allowlist")
        if self.upstream != _UPSTREAM:
            raise ValueError("upstream provenance must match the pinned source snapshot")
        if (
            self.schema_version != "model-rotator-registry.v1"
            or self.provider != "openrouter"
            or self.selection_strategy != "best_first"
            or self.selection_strategy_version != "best_first.v1"
        ):
            raise ValueError("registry identity and selection strategy are version-bound")

    def _digest_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "provider": self.provider,
            "dashscope_enabled": self.dashscope_enabled,
            "free_claim": self.free_claim,
            "selection_strategy": self.selection_strategy,
            "selection_strategy_version": self.selection_strategy_version,
            "models": list(self.models),
            "upstream": self.upstream.to_dict(),
        }

    @property
    def registry_digest(self) -> str:
        encoded = json.dumps(
            self._digest_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, object]:
        payload = self._digest_payload()
        payload["registry_digest"] = self.registry_digest
        return payload

    def ordered_candidates(
        self,
        *,
        cooling_until: Mapping[str, float],
        now: float,
        requested_model: str | None = None,
        cursor: int | None = None,
    ) -> tuple[str, ...]:
        """Return best-first candidates, demoting active cooldowns stably.

        ``requested_model`` and ``cursor`` are accepted only to make explicit
        that neither caller preference can reorder this pinned allowlist.
        """

        del requested_model, cursor
        if not isinstance(now, (int, float)) or isinstance(now, bool) or not math.isfinite(now) or now < 0:
            raise ValueError("now must be a finite non-negative number")
        active: set[str] = set()
        for model, deadline in cooling_until.items():
            if not isinstance(deadline, (int, float)) or isinstance(deadline, bool) or not math.isfinite(deadline):
                raise ValueError(f"cooldown deadline for {model!r} must be finite")
            if deadline > now and model in self.models:
                active.add(model)
        if len(active) == len(self.models):
            return self.models
        ready = tuple(model for model in self.models if model not in active)
        cooling = tuple(model for model in self.models if model in active)
        return ready + cooling


DEFAULT_MODEL_ROTATOR_REGISTRY = ModelRotatorRegistry(
    enabled=False,
    dashscope_enabled=False,
    free_claim=None,
    models=_MODELS,
    upstream=_UPSTREAM,
)
