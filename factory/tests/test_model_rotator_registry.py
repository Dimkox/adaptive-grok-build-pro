from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import unittest

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
    assert registry.upstream.commit == "27955ebaca6bb3390de841a516ec1d0bf728ac09"
    assert registry.upstream.tree_sha1 == "c558dfc97cc55b25a49479b04182d77d8a2b85b0"
    assert registry.upstream.archive_kind == "github_api_tarball"
    assert registry.upstream.archive_url == (
        "https://api.github.com/repos/Dimkox/qwen-model-rotator/tarball/"
        "27955ebaca6bb3390de841a516ec1d0bf728ac09"
    )
    assert registry.upstream.archive_sha256 == "2ac88782216333dedcee6db30c2e3f885017100951af782934baf241b50b12b9"
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


def test_literal_payload_and_digest_are_independent_golden_evidence() -> None:
    expected = {
        "schema_version": "model-rotator-registry.v1",
        "enabled": False,
        "provider": "openrouter",
        "dashscope_enabled": False,
        "free_claim": None,
        "selection_strategy": "best_first",
        "selection_strategy_version": "best_first.v1",
        "models": list(EXPECTED_MODELS),
        "upstream": {
            "repository": "https://github.com/Dimkox/qwen-model-rotator",
            "commit": "27955ebaca6bb3390de841a516ec1d0bf728ac09",
            "tree_sha1": "c558dfc97cc55b25a49479b04182d77d8a2b85b0",
            "archive_kind": "github_api_tarball",
            "archive_url": (
                "https://api.github.com/repos/Dimkox/qwen-model-rotator/tarball/"
                "27955ebaca6bb3390de841a516ec1d0bf728ac09"
            ),
            "archive_sha256": "2ac88782216333dedcee6db30c2e3f885017100951af782934baf241b50b12b9",
            "models_file": "models.txt",
            "models_file_sha256": "cf2e502a8af917d77bd6710d1eb3a68377f72c0c9e839c3479a5ed19c4d21b20",
        },
    }

    assert DEFAULT_MODEL_ROTATOR_REGISTRY.to_dict() == {
        **expected,
        "registry_digest": "09b9df8a94d742644154a854ecd1700de0e7b4fd799a01ebcd739c09a635cfb7",
    }
    for field in ("archive_sha256", "models_file_sha256", "tree_sha1"):
        mutated = json.loads(json.dumps(expected))
        mutated["upstream"][field] = "0" * len(mutated["upstream"][field])
        mutated_digest = hashlib.sha256(
            json.dumps(mutated, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        assert mutated_digest != DEFAULT_MODEL_ROTATOR_REGISTRY.registry_digest
    removed = json.loads(json.dumps(expected))
    del removed["upstream"]["archive_sha256"]
    removed_digest = hashlib.sha256(
        json.dumps(removed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert removed_digest != DEFAULT_MODEL_ROTATOR_REGISTRY.registry_digest


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


def test_candidate_selection_rejects_invalid_time_without_effects() -> None:
    registry = DEFAULT_MODEL_ROTATOR_REGISTRY
    for bad_now in (float("nan"), float("inf"), -1.0):
        cooldowns = {registry.models[0]: 200.0}
        with unittest.TestCase().assertRaisesRegex(ValueError, "now"):
            registry.ordered_candidates(cooling_until=cooldowns, now=bad_now)
        assert cooldowns == {registry.models[0]: 200.0}


def test_registry_rejects_order_and_provenance_mutations() -> None:
    base = DEFAULT_MODEL_ROTATOR_REGISTRY

    with unittest.TestCase().assertRaises(ValueError):
        ModelRotatorRegistry(
            enabled=False,
            dashscope_enabled=False,
            free_claim=None,
            models=base.models[:-1],
            upstream=base.upstream,
        )
    with unittest.TestCase().assertRaises(ValueError):
        ModelRotatorRegistry(
            enabled=False,
            dashscope_enabled=False,
            free_claim=None,
            models=base.models[::-1],
            upstream=base.upstream,
        )
    with unittest.TestCase().assertRaises(ValueError):
        ModelRotatorRegistry(
            enabled=False,
            dashscope_enabled=False,
            free_claim=None,
            models=base.models,
            upstream=dataclasses.replace(base.upstream, tree_sha1="0" * 40),
        )
    with unittest.TestCase().assertRaises(ValueError):
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


def test_clean_import_cannot_open_socket_spawn_or_write_settings_or_environment(tmp_path: Path) -> None:
    guard = tmp_path / "guard.py"
    guard.write_text(
        """
import builtins
import os
from pathlib import Path
import socket
import subprocess

def deny(*args, **kwargs):
    raise AssertionError("import attempted a forbidden side effect")

socket.socket = deny
subprocess.Popen = deny
Path.write_text = deny
Path.write_bytes = deny
Path.touch = deny
os.putenv = deny
os.unsetenv = deny

class GuardedEnvironment(dict):
    def __setitem__(self, key, value): deny()
    def __delitem__(self, key): deny()
    def clear(self): deny()
    def pop(self, key, default=None): deny()
    def popitem(self): deny()
    def setdefault(self, key, default=None): deny()
    def update(self, *args, **kwargs): deny()

os.environ = GuardedEnvironment(os.environ)
from adaptive_factory.model_rotator_registry import DEFAULT_MODEL_ROTATOR_REGISTRY
assert DEFAULT_MODEL_ROTATOR_REGISTRY.enabled is False
"""
    )
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    completed = subprocess.run(
        [sys.executable, str(guard)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr


def _test_clean_import_with_stdlib_tempdir() -> None:
    with tempfile.TemporaryDirectory(prefix="rotator-import-test-") as raw:
        test_clean_import_cannot_open_socket_spawn_or_write_settings_or_environment(Path(raw))


_UNITTEST_FUNCTIONS = (
    test_registry_is_default_off_and_pins_exact_upstream_provenance,
    test_registry_digest_binds_version_strategy_models_and_provenance,
    test_literal_payload_and_digest_are_independent_golden_evidence,
    test_weak_and_dashscope_models_are_not_admitted,
    test_best_first_order_ignores_request_and_cursor_and_demotes_cooling_models,
    test_expired_or_unknown_cooldowns_do_not_change_order,
    test_candidate_selection_rejects_invalid_time_without_effects,
    test_registry_rejects_order_and_provenance_mutations,
    test_selection_is_pure_and_has_no_runtime_interfaces,
    _test_clean_import_with_stdlib_tempdir,
)


def test_unittest_discovery_inventory_is_exact() -> None:
    assert len(_UNITTEST_FUNCTIONS) == 10
    assert {test.__name__ for test in _UNITTEST_FUNCTIONS} == {
        "test_registry_is_default_off_and_pins_exact_upstream_provenance",
        "test_registry_digest_binds_version_strategy_models_and_provenance",
        "test_literal_payload_and_digest_are_independent_golden_evidence",
        "test_weak_and_dashscope_models_are_not_admitted",
        "test_best_first_order_ignores_request_and_cursor_and_demotes_cooling_models",
        "test_expired_or_unknown_cooldowns_do_not_change_order",
        "test_candidate_selection_rejects_invalid_time_without_effects",
        "test_registry_rejects_order_and_provenance_mutations",
        "test_selection_is_pure_and_has_no_runtime_interfaces",
        "_test_clean_import_with_stdlib_tempdir",
    }


def load_tests(loader, tests, pattern):
    del loader, tests, pattern
    return unittest.TestSuite(
        unittest.FunctionTestCase(test)
        for test in (*_UNITTEST_FUNCTIONS, test_unittest_discovery_inventory_is_exact)
    )
