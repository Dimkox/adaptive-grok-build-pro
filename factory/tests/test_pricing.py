import json
import unittest

from fastapi.testclient import TestClient

from adaptive_factory.pricing import (
    PriceTableV1,
    PricingContractError,
    UsageTokens,
    calculate_cost_usd_micros,
    price_table_digest,
)
from adaptive_factory.protocol import (
    EventStreamParser,
    PROTOCOL_VERSION_V2,
    ProtocolError,
    validate_event_payload,
)
from adaptive_factory.api import Authenticator, create_app
from adaptive_factory.models import Actor
from factory.tests.test_api import FakeService


class PricedUsageService(FakeService):
    @staticmethod
    def _proposal(grant, **kwargs):
        proposal = FakeService._proposal(grant, **kwargs)
        payload = kwargs["payload"]
        if kwargs["event_type"] == "usage.reported" and "price_table" in payload:
            table = PriceTableV1.from_dict(payload["price_table"])
            proposal["cost_usd_micros"] = calculate_cost_usd_micros(
                UsageTokens(
                    payload["input_tokens"], payload["output_tokens"],
                    payload["reasoning_tokens"], payload["cached_input_tokens"],
                    payload["cache_write_tokens"],
                ),
                table,
                payload["price_table_digest"],
            )
        return proposal


class PricingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.table = PriceTableV1(
            schema_version=1,
            input_usd_micros_per_million=1_000_000,
            output_usd_micros_per_million=2_000_000,
            reasoning_usd_micros_per_million=3_000_000,
            cached_input_usd_micros_per_million=250_000,
            cache_write_usd_micros_per_million=500_000,
        )

    def test_prices_each_of_the_five_exclusive_token_buckets(self) -> None:
        """A missing or swapped rate must change the derived total."""
        usage = UsageTokens(
            input_tokens=2_000_000,
            output_tokens=3_000_000,
            reasoning_tokens=4_000_000,
            cached_input_tokens=5_000_000,
            cache_write_tokens=6_000_000,
        )

        self.assertEqual(
            calculate_cost_usd_micros(usage, self.table, price_table_digest(self.table)),
            24_250_000,
        )

    def test_accepts_explicit_zero_cache_usage(self) -> None:
        """Treating zero cache facts as absent would reject a valid report."""
        usage = UsageTokens(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            reasoning_tokens=0,
            cached_input_tokens=0,
            cache_write_tokens=0,
        )

        self.assertEqual(
            calculate_cost_usd_micros(usage, self.table, price_table_digest(self.table)),
            3_000_000,
        )

    def test_rejects_a_digest_that_does_not_bind_the_complete_price_table(self) -> None:
        """A forged digest must never authorize a cost calculation."""
        usage = UsageTokens(1, 1, 1, 1, 1)

        with self.assertRaisesRegex(PricingContractError, "price_table_digest_mismatch"):
            calculate_cost_usd_micros(usage, self.table, "0" * 64)

    def test_floors_each_fractional_component_before_summing(self) -> None:
        """Moving floor division after summation would overcharge this usage."""
        usage = UsageTokens(1, 1, 1, 1, 1)
        fractional_table = PriceTableV1(1, 500_000, 500_000, 500_000, 500_000, 500_000)

        self.assertEqual(
            calculate_cost_usd_micros(usage, fractional_table, price_table_digest(fractional_table)),
            0,
        )

    def test_digests_the_canonical_closed_table(self) -> None:
        """Changing a rate or canonical field set must change the table identity."""
        self.assertEqual(
            price_table_digest(self.table),
            "4d554ab3d98a6a993d6801c3033a8102e2fe6e84bd5e582e377096cac0a8e12b",
        )

    def test_rejects_negative_or_boolean_token_and_rate_values(self) -> None:
        """Permitting Python booleans or negative amounts corrupts billing facts."""
        with self.assertRaisesRegex(PricingContractError, "invalid_nonnegative_integer"):
            UsageTokens(-1, 0, 0, 0, 0)
        with self.assertRaisesRegex(PricingContractError, "invalid_nonnegative_integer"):
            PriceTableV1(1, True, 0, 0, 0, 0)

    def test_v2_protocol_accepts_closed_priced_usage_and_rejects_forged_fields(self) -> None:
        payload = {
            "provider_call_id": "call-v2-1",
            "price_table": self.table.to_dict(),
            "price_table_digest": price_table_digest(self.table),
            "input_tokens": 10, "output_tokens": 4, "reasoning_tokens": 2,
            "cached_input_tokens": 3, "cache_write_tokens": 5, "output_bytes": 20,
        }
        parsed = EventStreamParser(
            "task-001", "run-001", "a" * 64, ("usage",)
        ).feed(json.dumps({
            "protocol_version": PROTOCOL_VERSION_V2,
            "task_id": "task-001", "run_id": "run-001",
            "packet_digest": "a" * 64, "sequence": 1,
            "event_type": "usage.reported", "payload": payload,
        }, separators=(",", ":")).encode() + b"\n")
        self.assertEqual((len(parsed), parsed[0].payload["cached_input_tokens"]), (1, 3))
        for invalid in ({**payload, "price_table": None}, {**payload, "cost_usd_micros": 999}):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ProtocolError, "payload_fields"):
                validate_event_payload("usage.reported", invalid, protocol_version=PROTOCOL_VERSION_V2)

    def test_v3_usage_endpoint_derives_cost_and_v2_terminal_uses_v2_protocol(self) -> None:
        credential = "fixture"
        actor = Actor("worker-01", "worker", frozenset({"task:execute"}), frozenset({"owner/repository"}))
        service = PricedUsageService()
        client = TestClient(create_app(service, Authenticator({credential: actor})))
        headers = {"Authorization": f"Bearer {credential}", "Idempotency-Key": "priced-usage-001", "X-Correlation-ID": "priced-usage"}
        grant = {"task_id": "00000000-0000-0000-0000-000000000001", "run_id": "00000000-0000-0000-0000-000000000002", "owner": "worker-01", "role": "writer", "fence": 7, "expires_at": "2026-09-02T01:00:00Z", "packet_digest": "0" * 64}
        common = {"grant": grant, "packet_digest": "d" * 64, "sequence": 3}
        response = client.post("/v3/execution/usage", headers=headers, json={
            **common, "provider_call_id": "priced-call", "price_table": self.table.to_dict(),
            "price_table_digest": price_table_digest(self.table), "input_tokens": 1,
            "output_tokens": 2, "reasoning_tokens": 0, "cached_input_tokens": 0,
            "cache_write_tokens": 0, "output_bytes": 4,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["proposal"]["cost_usd_micros"], 5)
        self.assertEqual(service.calls[-1][2]["protocol_version"], PROTOCOL_VERSION_V2)
        terminal = client.post("/v2/execution/terminal", headers={**headers, "Idempotency-Key": "v2-terminal-001"}, json={**common, "terminal_type": "run.completed", "summary": "complete"})
        self.assertEqual((terminal.status_code, service.calls[-1][2]["protocol_version"]), (200, PROTOCOL_VERSION_V2))


if __name__ == "__main__":
    unittest.main()
