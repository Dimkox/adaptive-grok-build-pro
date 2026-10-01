from __future__ import annotations

import dataclasses
import hashlib
import json

import pytest

from adaptive_factory.model_rotator_registry import (
    DEFAULT_MODEL_ROTATOR_REGISTRY,
    ModelRotatorRegistry,
)


EXPECTED_MODELS = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "poolside/laguna-s-2.1:free",
    "cohere/north-mini-code:free",
    "dots-studio/dots-3-note-preview:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "openrouter/free",
)


def test_registry_is_default_off_and_pins_exact_upstream_provenance() -> None:
    registry = DEFAULT_MODEL_ROTATOR_REGISTRY

    assert registry.enabled is False
    assert registry.dashscope_enabled is False
    assert registry.free_claim is None
    assert registry.models == EXPECTED_MODELS
    assert registry.upstream.repository == "https://github.com/Dimkox/qwen-model-rotator"
    assert registry.upstream.commit == "fbcb200e8a4bcff19a24fc0e4ccafb1b37615fe8"
    assert registry.upstream.tree_sha1 == "b4951988bce3d1b5aadef15bf51e7df4ab5c025e"
    assert registry.upstream.archive_sha256 == "b2dc6e18653111adb83085430ba8af3e7d909092c2528830f4276fb8a8de917d"
    assert registry.upstream.models_file_sha256 == "cf2e502a8af917d77bd6710d1eb3a68377f72c0c9e839c3479a5ed19c4d21b20"


def test_registry_digest_binds_version_strategy_models_and_provenance() -> None:
    registry = DEFAULT_MODEL_ROTATOR_REGISTRY
    payload = registry.to_dict()
    unbound = dict(payload)
    digest = unbound.pop("registry_digest")

    assert registry.schema_version == "model-rotator-registry.v1"
    assert registry.selection_strategy == "best_first"
    assert registry.selection_strategy_version == "best_first.v1"
    assert digest == hashlib.sha256(
        json.dumps(unbound, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()

    mutated = dict(unbound)
    mutated["models"] = list(reversed(mutated["models"]))
    assert hashlib.sha256(
        json.dumps(mutated, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest() != registry.registry_digest
    assert dataclasses.replace(registry.upstream, tree_sha1="0" * 40) != registry.upstream


def test_weak_and_dashscope_models_are_not_admitted() -> None:
    names = DEFAULT_MODEL_ROTATOR_REGISTRY.models
    forbidden = {
        "nvidia/nemotron-3.5-lightning:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "poolside/laguna-xs-2.1:free",
        "liquid/lfm-2.5-2.6b:free",
    }

    assert forbidden.isdisjoint(names)
    assert "qwen/qwen3-coder:free" not in names
    assert all("/" in name for name in names)


def test_best_first_order_ignores_request_and_cursor_and_demotes_cooling_models() -> None:
    registry = DEFAULT_MODEL_ROTATOR_REGISTRY
    cooling = {
        registry.models[0]: 200.0,
        registry.models[2]: 150.0,
    }

    expected = registry.models[1:2] + registry.models[3:] + (registry.models[0], registry.models[2])
    assert registry.ordered_candidates(
        cooling_until=cooling,
        now=100.0,
        requested_model=registry.models[-1],
        cursor=5,
    ) == expected
    assert registry.ordered_candidates(
        cooling_until=cooling,
        now=100.0,
        requested_model="unknown/request:free",
        cursor=1,
    ) == expected


def test_expired_or_unknown_cooldowns_do_not_change_order() -> None:
    registry = DEFAULT_MODEL_ROTATOR_REGISTRY

    assert registry.ordered_candidates(
        cooling_until={registry.models[0]: 99.0, "unknown/request:free": 999.0},
        now=100.0,
    ) == registry.models
    assert registry.ordered_candidates(
        cooling_until={model: 101.0 for model in registry.models},
        now=100.0,
    ) == registry.models


@pytest.mark.parametrize("bad_now", [float("nan"), float("inf"), -1.0])
def test_candidate_selection_rejects_invalid_time_without_effects(bad_now: float) -> None:
    registry = DEFAULT_MODEL_ROTATOR_REGISTRY
    cooldowns = {registry.models[0]: 200.0}

    with pytest.raises(ValueError, match="now"):
        registry.ordered_candidates(cooling_until=cooldowns, now=bad_now)
    assert cooldowns == {registry.models[0]: 200.0}


def test_registry_rejects_order_and_provenance_mutations() -> None:
    base = DEFAULT_MODEL_ROTATOR_REGISTRY

    with pytest.raises(ValueError):
        ModelRotatorRegistry(
            enabled=False,
            dashscope_enabled=False,
            free_claim=None,
            models=base.models[:-1],
            upstream=base.upstream,
        )
    with pytest.raises(ValueError):
        ModelRotatorRegistry(
            enabled=False,
            dashscope_enabled=False,
            free_claim=None,
            models=base.models[::-1],
            upstream=base.upstream,
        )
    with pytest.raises(ValueError):
        ModelRotatorRegistry(
            enabled=False,
            dashscope_enabled=False,
            free_claim=None,
            models=base.models,
            upstream=dataclasses.replace(base.upstream, tree_sha1="0" * 40),
        )
    with pytest.raises(ValueError):
        ModelRotatorRegistry(
            enabled=True,
            dashscope_enabled=False,
            free_claim=None,
            models=base.models,
            upstream=base.upstream,
        )


def test_selection_is_pure_and_has_no_runtime_interfaces() -> None:
    registry = DEFAULT_MODEL_ROTATOR_REGISTRY
    before = registry.to_dict()

    registry.ordered_candidates(cooling_until={}, now=0.0)

    assert registry.to_dict() == before
    for forbidden_attribute in (
        "connect",
        "execute",
        "request",
        "settings",
        "credentials",
        "cursor",
        "save",
    ):
        assert not hasattr(registry, forbidden_attribute)
