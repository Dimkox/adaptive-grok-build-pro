import json
from pathlib import Path
import unittest
from contextlib import redirect_stdout
import io
import threading

from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.model_rotator import (
    ModelRotator,
    InMemoryRotationStore,
    RotationAuthorityGrant,
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
            "commit": "f91ead60dfab81912e8224f9eab503e8cbc09976",
            "observed_at": "2026-09-30T22:16:22Z",
            "source_sha256": "7e53bc18c9e7517a70c2eb7f3972ad6fdc1b05df6de3d4d3e065b65011c88bbe",
        },
        "models": [
            {"provider_id": "openrouter", "model_id": "qwen/a:free", "free_claim": None, "quota_mode": "request", "enabled": True, "priority": 10},
            {"provider_id": "openrouter", "model_id": "qwen/b:free", "free_claim": None, "quota_mode": "request", "enabled": True, "priority": 20},
            {"provider_id": "qwen", "model_id": "qwen-c", "free_claim": None, "quota_mode": "token", "enabled": True, "priority": 30},
        ],
        "policy": {"max_attempts": 3, "max_cooldown_seconds": 600,
                   "token_quota": 1000, "request_quota": 10, "per_attempt_token_limit": 200, **policy},
    })


def binding(reg, **changes):
    data = dict(schema_version=1, tenant_id="owner/project", repository_id="owner/project",
                task_id="task-1", run_id="run-1", attempt_id="attempt-1", fence=7,
                budget_reservation_id="budget-1", budget_digest="a" * 64,
                registry_digest=reg.registry_digest, operation_id="operation-1",
                requested_provider_id="openrouter", requested_model_id="qwen/a:free",
                remaining_token_units=600, remaining_request_units=10)
    data.update(changes)
    return RotationBindingV1.from_dict(data)


def ready_rotator(reg, bind=None, *, enabled=True, store=None):
    store = store or InMemoryRotationStore()
    if bind is not None:
        authorize(store, bind)
    return ModelRotator(reg, store, enabled=enabled), store


def authorize(store, bind):
    store.authorize(RotationAuthorityGrant.from_authoritative_facts(
        repository_id=bind.repository_id, task_id=bind.task_id, run_id=bind.run_id,
        attempt_id=bind.attempt_id, fence=bind.fence, reservation_id=bind.budget_reservation_id,
        budget_digest=bind.budget_digest, token_capacity=bind.remaining_token_units,
        request_capacity=bind.remaining_request_units))


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
        reg = registry(); rotator, _ = ready_rotator(reg)
        bind = binding(reg)
        self.assertEqual(("openrouter", "qwen/a:free"), rotator.select(bind, {}, now=100))
        cooldowns = {"openrouter/qwen/a:free": 200,
                     "openrouter/qwen/b:free": 150}
        self.assertEqual(("qwen", "qwen-c"), rotator.select(bind, cooldowns, now=100))
        cooldowns["qwen/qwen-c"] = 101
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
        rotator, _ = ready_rotator(reg, bind)
        result = rotator.execute(bind, transport, now=100)
        self.assertEqual([("openrouter", "qwen/a:free", 200),
                          ("openrouter", "qwen/b:free", 200)], calls)
        self.assertEqual("selected", result["status"])
        self.assertEqual(30, result["usage"]["known_tokens"])
        self.assertTrue(result["usage"]["complete"])
        self.assertEqual(7, result["binding"]["fence"])
        self.assertEqual(64, len(result["binding"]["budget_reservation_digest"]))
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
            reg = registry(); bind = binding(reg); rotator, _ = ready_rotator(reg, bind)
            result = rotator.execute(bind, lambda *args: calls.append(args) or response, now=100)
            with self.subTest(response=response):
                self.assertEqual(1, len(calls))
                self.assertIn(result["status"], {"stopped", "needs_human"})
                if response.response_started:
                    self.assertEqual("needs_human", result["status"])

    def test_unknown_usage_is_not_zero_and_blocks_further_dispatch(self):
        reg = registry(); calls = []
        bind = binding(reg); rotator, _ = ready_rotator(reg, bind)
        result = rotator.execute(
            bind, lambda *args: calls.append(args) or
            TransportResult.failure(503, "unavailable", response_started=False), now=100)
        self.assertEqual(1, len(calls))
        self.assertEqual("needs_human", result["status"])
        self.assertEqual(1, result["usage"]["unknown_attempts"])
        self.assertFalse(result["usage"]["complete"])
        self.assertIsNone(result["attempts"][0]["usage_input_units"])

    def test_default_off_and_budget_or_binding_mismatch_dispatch_nothing(self):
        reg = registry(); calls = []
        with self.assertRaisesRegex(ContractError, "rotator_disabled"):
            bind = binding(reg); rotator, _ = ready_rotator(reg, bind, enabled=False)
            rotator.execute(bind, lambda *args: calls.append(args), now=100)
        self.assertEqual([], calls)
        for kwargs in ({"remaining_request_units": -1}, {"registry_digest": "f" * 64},
                       {"fence": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ContractError):
                bad = binding(reg, **kwargs)
                rotator, _ = ready_rotator(reg, bad)
                rotator.execute(bad, lambda *args: calls.append(args), now=100)
        self.assertEqual([], calls)

    def test_attempt_cap_and_token_quota_are_hard_bounds(self):
        reg = registry(max_attempts=2, token_quota=400)
        calls = []
        def failed(*args):
            calls.append(args)
            return TransportResult.failure(503, "unavailable", response_started=False,
                                           input_tokens=100, output_tokens=100)
        bind = binding(reg, remaining_token_units=400); rotator, _ = ready_rotator(reg, bind)
        result = rotator.execute(bind, failed, now=100)
        self.assertEqual(2, len(calls))
        self.assertEqual("exhausted", result["status"])
        self.assertEqual(400, result["usage"]["known_tokens"])

    def test_transport_result_constructor_is_closed_by_invariants(self):
        cases = (
            dict(ok=True,status_code=503,category="success",response_started=True,response_digest="b"*64,input_tokens=1,output_tokens=1),
            dict(ok=False,status_code=503,category="success",response_started=False,response_digest=None,input_tokens=1,output_tokens=1),
            dict(ok=False,status_code=99,category="transport",response_started=False,response_digest=None,input_tokens=1,output_tokens=1),
            dict(ok=False,status_code=503,category="transport",response_started=False,response_digest="b"*64,input_tokens=1,output_tokens=1),
            dict(ok=False,status_code=503,category="transport",response_started=False,response_digest=None,input_tokens=-1,output_tokens=1),
            dict(ok=False,status_code=503,category="made_up",response_started=False,response_digest=None,input_tokens=1,output_tokens=1),
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ContractError): TransportResult(**case)

    def test_store_authority_idempotent_replay_and_concurrent_claim(self):
        reg=registry(); bind=binding(reg); store=InMemoryRotationStore(); authorize(store,bind)
        rotator=ModelRotator(reg,store,enabled=True); calls=[]
        transport=lambda *a: calls.append(a) or TransportResult.success(response_digest="b"*64,input_tokens=1,output_tokens=1)
        first=rotator.execute(bind,transport,now=100); second=rotator.execute(bind,transport,now=100)
        self.assertEqual(first,second); self.assertEqual(1,len(calls))
        ungranted=binding(reg,operation_id="operation-2",attempt_id="attempt-2")
        with self.assertRaisesRegex(ContractError,"authority_not_granted"): rotator.execute(ungranted,transport,now=100)
        conflict=binding(reg,remaining_token_units=500); authorize(store,conflict)
        with self.assertRaisesRegex(ContractError,"idempotency_conflict"): rotator.execute(conflict,transport,now=100)

        bind2=binding(reg,operation_id="operation-3",requested_model_id="qwen/b:free"); authorize(store,bind2)
        requested=canonical_digest({"provider_id":"openrouter","model_id":"qwen/b:free"})
        store.claim(bind2,reg.registry_digest,1,requested,101)
        with self.assertRaisesRegex(ContractError,"operation_already_claimed"):
            store.claim(bind2,reg.registry_digest,1,requested,101)

    def test_durable_cooldown_is_consumed_and_overrun_stops(self):
        reg=registry(); store=InMemoryRotationStore(); first=binding(reg); authorize(store,first)
        rotator=ModelRotator(reg,store,enabled=True); calls=[]
        responses=iter((TransportResult.failure(429,"rate_limit",response_started=False,input_tokens=1,output_tokens=1),
                        TransportResult.success(response_digest="b"*64,input_tokens=1,output_tokens=1)))
        rotator.execute(first,lambda *a: calls.append(a) or next(responses),now=100)
        second=binding(reg,operation_id="operation-2",requested_provider_id="qwen",requested_model_id="qwen-c"); authorize(store,second); calls.clear()
        rotator.execute(second,lambda *a: calls.append(a) or TransportResult.success(response_digest="c"*64,input_tokens=1,output_tokens=1),now=101)
        self.assertNotEqual("qwen/a:free",calls[0][1])
        token_store=InMemoryRotationStore(); third=binding(reg,operation_id="operation-3",requested_provider_id="qwen",requested_model_id="qwen-c"); authorize(token_store,third)
        over=ModelRotator(reg,token_store,enabled=True).execute(third,lambda *a: TransportResult.success(response_digest="d"*64,input_tokens=201,output_tokens=0),now=102)
        self.assertEqual("needs_human",over["status"]); self.assertTrue(over["attempts"][0]["budget_overrun"])

    def test_all_authenticated_cooldowns_produce_no_dispatch(self):
        reg=registry(); store=InMemoryRotationStore(); first=binding(reg,remaining_token_units=1000); authorize(store,first)
        rotator=ModelRotator(reg,store,enabled=True); rotator.execute(first,lambda *a: TransportResult.failure(503,"unavailable",response_started=False,input_tokens=1,output_tokens=1),now=100)
        second=binding(reg,operation_id="operation-2",remaining_token_units=1000,requested_provider_id="openrouter",requested_model_id="qwen/a:free"); authorize(store,second); calls=[]
        result=rotator.execute(second,lambda *a: calls.append(a),now=101)
        self.assertEqual([],calls); self.assertEqual("exhausted",result["status"])

    def test_sensitive_identifiers_and_unsupported_free_or_quota_claims_fail(self):
        reg=registry()
        with self.assertRaisesRegex(ContractError,"sensitive_identifier"): binding(reg,tenant_id="secret-token")
        for change in (("free_claim",True),("quota_mode","token")):
            raw=reg.to_dict(); raw["models"][0][change[0]]=change[1]
            with self.subTest(change=change), self.assertRaises(ContractError): ProviderRegistryV1.from_dict(raw)

    def test_migration_027_has_transactional_authority_and_no_payload_columns(self):
        sql=(Path(__file__).parents[1]/"src/adaptive_factory/resources/027_model_rotator_state.sql").read_text()
        for required in ("pg_advisory_xact_lock","FOR UPDATE","budget_reservations","current_fence","lease_expires_at","operation_already_claimed","p_wire","state_version","claim_expires_at","quarantined","held_token_units","settled_token_units","model_rotator_reconcile_v1"):
            self.assertIn(required,sql)
        for forbidden in ("authorization text","api_key","prompt text","response_body"):
            self.assertNotIn(forbidden,sql.lower())
        self.assertNotIn("SECURITY INVOKER",sql)
        self.assertNotRegex(sql,r"GRANT\s+(?:SELECT,)?\s*(?:INSERT|UPDATE|DELETE).+factory_runtime")
        runtime_grants=[line for line in sql.splitlines() if "TO factory_runtime" in line]
        self.assertFalse(any("model_rotator_reconcile_v1" in line for line in runtime_grants))
        self.assertIn("model_rotator_safe_status",sql)

    def test_bundled_registry_cursor_stays_with_enabled_tuple_across_two_operations(self):
        raw=json.loads((Path(__file__).parents[1]/"src/adaptive_factory/resources/model-rotator-registry.v1.json").read_text())
        reg=ProviderRegistryV1.from_dict(raw); store=InMemoryRotationStore(); calls=[]
        def make(operation):
            return binding(reg,operation_id=operation,requested_provider_id="openrouter",requested_model_id="qwen/qwen3-coder:free")
        for operation in ("bundle-1","bundle-2"):
            bind=make(operation); authorize(store,bind)
            ModelRotator(reg,store,enabled=True).execute(bind,lambda p,m,l: calls.append((p,m)) or TransportResult.success(response_digest="a"*64,input_tokens=1,output_tokens=1),now=100)
        self.assertEqual([("openrouter","qwen/qwen3-coder:free")]*2,calls)

    def test_real_threads_serialize_one_tenant_registry_claim(self):
        reg=registry(); bind=binding(reg); store=InMemoryRotationStore(); authorize(store,bind); rotator=ModelRotator(reg,store,enabled=True)
        entered=threading.Event(); release=threading.Event(); results=[]; errors=[]
        def transport(*args): entered.set(); release.wait(2); return TransportResult.success(response_digest="e"*64,input_tokens=1,output_tokens=1)
        first=threading.Thread(target=lambda: results.append(rotator.execute(bind,transport,now=100))); first.start(); self.assertTrue(entered.wait(1))
        second=threading.Thread(target=lambda: self._capture(errors,lambda: rotator.execute(bind,transport,now=100))); second.start(); second.join(1); release.set(); first.join(2)
        self.assertEqual(1,len(results)); self.assertEqual(1,len(errors)); self.assertIn("operation_already_claimed",str(errors[0]))

    @staticmethod
    def _capture(errors,call):
        try: call()
        except Exception as exc: errors.append(exc)

    def test_transport_crash_is_durable_quarantine_until_reconciled(self):
        reg=registry(); bind=binding(reg); store=InMemoryRotationStore(); authorize(store,bind); rotator=ModelRotator(reg,store,enabled=True)
        result=rotator.execute(bind,lambda *a: (_ for _ in ()).throw(OSError("sentinel-secret-body")),now=100)
        self.assertEqual("needs_human",result["status"]); self.assertNotIn("sentinel",json.dumps(result))
        next_binding=binding(reg,operation_id="operation-2"); authorize(store,next_binding)
        with self.assertRaisesRegex(ContractError,"reconciliation_required"): rotator.execute(next_binding,lambda *a: None,now=101)
        store.reconcile(result["binding"]["tenant_digest"],reg.registry_digest)

    def test_request_quota_not_token_threshold_and_is_one_per_dispatch(self):
        reg=registry(); bind=binding(reg,remaining_token_units=0,remaining_request_units=1); store=InMemoryRotationStore(); authorize(store,bind)
        result=ModelRotator(reg,store,enabled=True).execute(bind,lambda *a: TransportResult.success(response_digest="f"*64,input_tokens=999,output_tokens=999),now=100)
        self.assertEqual("selected",result["status"]); self.assertFalse(result["attempts"][0]["budget_overrun"])
        store2=InMemoryRotationStore(); bind2=binding(reg,operation_id="operation-2",remaining_request_units=1); authorize(store2,bind2); calls=[]
        stopped=ModelRotator(reg,store2,enabled=True).execute(bind2,lambda *a: calls.append(a) or TransportResult.failure(429,"rate_limit",response_started=False,input_tokens=1,output_tokens=1),now=100)
        self.assertEqual(1,len(calls)); self.assertEqual("stopped",stopped["status"])

    def test_operator_surface_is_read_only_and_default_off(self):
        from adaptive_factory.model_rotator_cli import main
        output=io.StringIO()
        with redirect_stdout(output): self.assertEqual(0,main(["status"]))
        status=json.loads(output.getvalue())
        self.assertEqual(False,status["enabled"]); self.assertEqual("NOT_RUN",status["live_qualification"])


if __name__ == "__main__":
    unittest.main()
