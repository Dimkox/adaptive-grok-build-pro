import json
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.model_rotator import (
    ModelRotator,
    ProviderRegistryV1,
    RotationBindingV1,
    TransportResult,
)


def registry(**policy):
    return ProviderRegistryV1.from_dict({
        "schema_version": 1,
        "registry_id": "free-models-20260930",
        "registry_version": "1.0.0",
        "provenance": {
            "repository": "Dimkox/qwen-model-rotator",
            "commit": "b76a09849c132ab62f73bee76f949bd600bc4649",
            "observed_at": "2026-09-30T00:00:00Z",
        },
        "models": [
            {"provider_id": "openrouter", "model_id": "qwen/a:free", "free_claim": True, "enabled": True, "priority": 10},
            {"provider_id": "openrouter", "model_id": "qwen/b:free", "free_claim": True, "enabled": True, "priority": 20},
            {"provider_id": "qwen", "model_id": "qwen-c", "free_claim": True, "enabled": True, "priority": 30},
        ],
        "policy": {"max_attempts": 3, "max_cooldown_seconds": 600,
                   "token_quota": 1000, "per_attempt_token_limit": 200, **policy},
    })


def binding(reg, **changes):
    data = dict(schema_version=1, tenant_id="tenant-1", repository_id="owner/project",
                task_id="task-1", run_id="run-1", attempt_id="attempt-1", fence=7,
                budget_reservation_id="budget-1", budget_digest="a" * 64,
                registry_digest=reg.registry_digest, operation_id="operation-1",
                requested_provider_id="openrouter", requested_model_id="qwen/a:free",
                remaining_token_units=600)
    data.update(changes)
    return RotationBindingV1.from_dict(data)


class ModelRotatorTests(unittest.TestCase):
    def test_registry_is_closed_versioned_unique_and_secret_free(self):
        good = registry()
        self.assertEqual(["qwen/a:free", "qwen/b:free", "qwen-c"],
                         [m.model_id for m in good.models])
        raw = good.to_dict()
        for mutation in (
            lambda x: x.update(api_key="leak"),
            lambda x: x["models"][0].update(authorization="Bearer leak"),
            lambda x: x["models"].append(dict(x["models"][0])),
            lambda x: x.update(schema_version=2),
        ):
            changed = json.loads(json.dumps(raw)); mutation(changed)
            with self.subTest(changed=changed), self.assertRaises(ContractError):
                ProviderRegistryV1.from_dict(changed)

    def test_selection_is_deterministic_and_active_cooldown_is_never_bypassed(self):
        reg = registry(); rotator = ModelRotator(reg)
        bind = binding(reg)
        self.assertEqual(("openrouter", "qwen/a:free"), rotator.select(bind, {}, now=100))
        cooldowns = {("openrouter", "qwen/a:free"): 200,
                     ("openrouter", "qwen/b:free"): 150}
        self.assertEqual(("qwen", "qwen-c"), rotator.select(bind, cooldowns, now=100))
        cooldowns[("qwen", "qwen-c")] = 101
        self.assertIsNone(rotator.select(bind, cooldowns, now=100))
        self.assertEqual(("qwen", "qwen-c"), rotator.select(bind, cooldowns, now=101))

    def test_pre_response_retry_records_usage_and_full_authority_binding(self):
        reg = registry(); bind = binding(reg); calls = []
        def transport(provider, model, limit):
            calls.append((provider, model, limit))
            if len(calls) == 1:
                return TransportResult.failure(429, "rate_limit", response_started=False,
                                               input_tokens=10, output_tokens=0)
            return TransportResult.success(response_digest="b" * 64, input_tokens=12, output_tokens=8)
        result = ModelRotator(reg, enabled=True).execute(bind, transport, now=100)
        self.assertEqual([("openrouter", "qwen/a:free", 200),
                          ("openrouter", "qwen/b:free", 200)], calls)
        self.assertEqual("selected", result["status"])
        self.assertEqual(30, result["usage"]["known_tokens"])
        self.assertTrue(result["usage"]["complete"])
        self.assertEqual(7, result["binding"]["fence"])
        self.assertEqual("budget-1", result["binding"]["budget_reservation_id"])
        self.assertTrue(all(row["binding_digest"] == bind.binding_digest for row in result["attempts"]))
        self.assertEqual("none", result["authority_effect"])
        self.assertIsNone(result["cost_usd"])

    def test_fatal_and_post_response_failures_never_rotate(self):
        for response in (
            TransportResult.failure(401, "authentication", response_started=False),
            TransportResult.failure(402, "payment", response_started=False),
            TransportResult.failure(429, "daily_limit", response_started=False),
            TransportResult.failure(503, "unavailable", response_started=True),
        ):
            calls = []
            result = ModelRotator(registry(), enabled=True).execute(
                binding(registry()), lambda *args: calls.append(args) or response, now=100)
            with self.subTest(response=response):
                self.assertEqual(1, len(calls))
                self.assertIn(result["status"], {"stopped", "needs_human"})
                if response.response_started:
                    self.assertEqual("needs_human", result["status"])

    def test_unknown_usage_is_not_zero_and_blocks_further_dispatch(self):
        reg = registry(); calls = []
        result = ModelRotator(reg, enabled=True).execute(
            binding(reg), lambda *args: calls.append(args) or
            TransportResult.failure(503, "unavailable", response_started=False), now=100)
        self.assertEqual(1, len(calls))
        self.assertEqual("needs_human", result["status"])
        self.assertEqual(1, result["usage"]["unknown_attempts"])
        self.assertFalse(result["usage"]["complete"])
        self.assertIsNone(result["attempts"][0]["usage_input_units"])

    def test_default_off_and_budget_or_binding_mismatch_dispatch_nothing(self):
        reg = registry(); calls = []
        with self.assertRaisesRegex(ContractError, "rotator_disabled"):
            ModelRotator(reg).execute(binding(reg), lambda *args: calls.append(args), now=100)
        self.assertEqual([], calls)
        for kwargs in ({"remaining_token_units": 199}, {"registry_digest": "f" * 64},
                       {"fence": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ContractError):
                bad = binding(reg, **kwargs)
                ModelRotator(reg, enabled=True).execute(bad, lambda *args: calls.append(args), now=100)
        self.assertEqual([], calls)

    def test_attempt_cap_and_token_quota_are_hard_bounds(self):
        reg = registry(max_attempts=2, token_quota=400)
        calls = []
        def failed(*args):
            calls.append(args)
            return TransportResult.failure(503, "unavailable", response_started=False,
                                           input_tokens=100, output_tokens=100)
        result = ModelRotator(reg, enabled=True).execute(binding(reg, remaining_token_units=400), failed, now=100)
        self.assertEqual(2, len(calls))
        self.assertEqual("exhausted", result["status"])
        self.assertEqual(400, result["usage"]["known_tokens"])


if __name__ == "__main__":
    unittest.main()
