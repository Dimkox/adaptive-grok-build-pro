from copy import deepcopy
import json
import unittest
from pathlib import Path

from adaptive_factory.contracts import ContractError
from adaptive_factory.decision_contracts import DecisionRecordV1, summarize_cost, summarize_timing
from adaptive_factory.migrations import discover_migrations
from adaptive_factory.store import PostgresFactoryStore
from factory.tests.decision_fixtures import decision_facts
from tests.json_schema_subset import SubsetValidator


def actual_cost_entry(amount=120):
    return dict(
        usage_id="call-1", source="provider", currency="USD",
        pricing_version="p1", amount_usd_micros=amount, status="actual",
    )


class DecisionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            Path("factory/contracts/v15/decision-record.v1.schema.json").read_text()
        )
        cls.validator = SubsetValidator(cls.schema)

    def test_json_schema_is_closed_and_accepts_the_structural_contract(self):
        candidate = decision_facts()
        self.validator.validate(candidate)

        mutations = []
        missing = deepcopy(candidate)
        del missing["decision_id"]
        mutations.append(missing)
        extra = deepcopy(candidate)
        extra["unexpected"] = True
        mutations.append(extra)
        nested_extra = deepcopy(candidate)
        nested_extra["facts"][0]["unexpected"] = True
        mutations.append(nested_extra)
        wrong_kind = deepcopy(candidate)
        wrong_kind["decision_kind"] = "authority"
        mutations.append(wrong_kind)
        bad_digest = deepcopy(candidate)
        bad_digest["context_digest"] = "not-a-digest"
        mutations.append(bad_digest)
        boolean_fence = deepcopy(candidate)
        boolean_fence["fence"] = True
        mutations.append(boolean_fence)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertFalse(self.validator.is_valid(mutation))
                with self.assertRaises(ContractError):
                    DecisionRecordV1.from_dict(mutation)

    def test_parser_rejects_unsafe_refs_timestamps_digests_and_scalars(self):
        for name, key, value in (
            ("unsafe_ref", "evidence_refs", ["../report.json"]),
            ("secret_ref", "evidence_refs", ["keys/operator.pem"]),
            ("invalid_timestamp", "observed_at", "not-a-time"),
            ("invalid_digest", "profile_digest", "g" * 64),
            ("invalid_spec_digest", "spec_digest", "g" * 64),
            ("invalid_sha", "base_sha", "A" * 40),
            ("invalid_fact_scalar", "facts", [dict(name="risk", value=1.5)]),
        ):
            candidate = decision_facts()
            candidate[key] = value
            with self.subTest(name=name), self.assertRaises(ContractError):
                DecisionRecordV1.from_dict(candidate)

    def test_schema_documents_runtime_only_semantic_admission(self):
        runtime_only = set(self.schema["x-admission"]["runtime_only"])
        self.assertGreaterEqual(
            runtime_only,
            {"safe_fact_text", "no_self_supersession", "unique_fact_names"},
        )

        secret = decision_facts()
        secret["facts"][0]["value"] = "password=synthetic-secret"
        self.validator.validate(secret)
        with self.assertRaises(ContractError):
            DecisionRecordV1.from_dict(secret)

        self_superseding = decision_facts()
        self_superseding["supersedes"] = self_superseding["decision_id"]
        self.validator.validate(self_superseding)
        with self.assertRaises(ContractError):
            DecisionRecordV1.from_dict(self_superseding)

    def test_record_boundaries(self):
        facts = decision_facts()
        record = DecisionRecordV1.from_dict(facts)
        self.assertEqual(record.to_dict()["next_step"], "verify")
        self.assertEqual(record.record_digest, DecisionRecordV1.from_dict(deepcopy(facts)).record_digest)
        for key, value in [
            ("outcome", "success"),
            ("fence", True),
            ("head_sha", "bad"),
            ("supersedes", "decision-1"),
        ]:
            changed = deepcopy(facts)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                DecisionRecordV1.from_dict(changed)
        facts["facts"][0]["value"] = "password=synthetic-secret"
        with self.assertRaises(ContractError):
            DecisionRecordV1.from_dict(facts)

        prediction = decision_facts()
        prediction["decision_kind"] = "prediction"
        DecisionRecordV1.from_dict(prediction)

    def test_identity_uuids_are_canonical(self):
        for field in ("task_id", "run_id", "attempt_id"):
            for value in (
                "not-a-uuid",
                "00000000-0000-0000-0000-00000000000A",
                "{00000000-0000-0000-0000-000000000001}",
            ):
                candidate = decision_facts()
                candidate[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                    DecisionRecordV1.from_dict(candidate)

    def test_collection_boundaries(self):
        facts = decision_facts()
        dup_fact = deepcopy(facts)
        dup_fact["facts"].append(deepcopy(dup_fact["facts"][0]))
        dup_ref = deepcopy(facts)
        dup_ref["evidence_refs"] *= 2
        dup_constraint = deepcopy(facts)
        dup_constraint["constraints"] *= 2
        oversized = deepcopy(facts)
        oversized["facts"] = [
            dict(name=f"fact-{index}", value=index) for index in range(33)
        ]
        for candidate in (
            dup_fact,
            dup_ref,
            dup_constraint,
            oversized,
        ):
            with self.assertRaises(ContractError):
                DecisionRecordV1.from_dict(candidate)

    def test_cost_boundaries(self):
        entry = actual_cost_entry()
        self.assertFalse(summarize_cost([entry])["complete"])
        self.assertFalse(summarize_cost([entry], expected_usage_ids=["call-1", "call-2"])["complete"])
        self.assertTrue(summarize_cost([entry], expected_usage_ids=["call-1"])["complete"])
        with self.assertRaises(ContractError):
            summarize_cost([entry], expected_usage_ids=["call-1", "call-1"])
        with self.assertRaises(ContractError):
            summarize_cost([entry], expected_usage_ids=[])
        with self.assertRaises(ContractError):
            summarize_cost(
                [dict(entry, amount_usd_micros=-1)], expected_usage_ids=["call-1"]
            )

    def test_cost_completeness_and_invalid_entries(self):
        actual = actual_cost_entry()
        unknown = dict(
            actual, usage_id="call-2", pricing_version=None,
            amount_usd_micros=None, status="unknown",
        )
        estimated = dict(actual, usage_id="call-2", amount_usd_micros=30, status="estimated")
        incomplete = dict(
            known_usd_micros=120, complete=False, total_usd_micros=None,
            unknown_items=1, estimated_items=0,
        )
        self.assertEqual(
            summarize_cost([actual], expected_usage_ids=["call-1"]),
            dict(incomplete, complete=True, total_usd_micros=120, unknown_items=0),
        )
        self.assertEqual(
            summarize_cost([actual, unknown], expected_usage_ids=["call-1", "call-2"]),
            incomplete,
        )
        self.assertEqual(
            summarize_cost([actual, estimated], expected_usage_ids=["call-1", "call-2"]),
            dict(incomplete, known_usd_micros=150, unknown_items=0, estimated_items=1),
        )
        self.assertEqual(
            summarize_cost([actual], expected_usage_ids=["call-1", "call-2"]),
            incomplete,
        )
        invalid = (
            ("duplicate", [actual, actual]),
            ("currency", [dict(actual, currency="EUR")]),
            ("status", [dict(actual, status="projected")]),
            ("missing_pricing", [dict(actual, pricing_version=None)]),
            ("invalid_pricing", [dict(actual, pricing_version=7)]),
            ("unknown_with_amount", [dict(unknown, amount_usd_micros=0)]),
            ("boolean_amount", [dict(actual, amount_usd_micros=True)]),
            ("oversized_amount", [dict(actual, amount_usd_micros=2**63)]),
        )
        for name, entries in invalid:
            with self.subTest(name=name), self.assertRaises(ContractError):
                summarize_cost(entries, expected_usage_ids=["call-1"])

    def test_cumulative_cost_accepts_signed_bigint_maximum(self):
        actual = actual_cost_entry(2**63 - 1)
        for entries in (
            [actual],
            [dict(actual, amount_usd_micros=2**63 - 2),
             dict(actual, usage_id="call-2", amount_usd_micros=1),
             dict(actual, usage_id="call-3", amount_usd_micros=0)],
        ):
            with self.subTest(entries=entries):
                self.assertEqual(
                    summarize_cost(entries, expected_usage_ids=[entry["usage_id"] for entry in entries]),
                    dict(known_usd_micros=2**63 - 1, complete=True,
                         total_usd_micros=2**63 - 1, unknown_items=0, estimated_items=0),
                )

    def test_cumulative_cost_rejects_overflow_even_when_incomplete(self):
        actual = actual_cost_entry(2**63 - 1)
        second = dict(actual, usage_id="call-2", amount_usd_micros=1)
        unknown = dict(
            actual, usage_id="call-3", pricing_version=None,
            amount_usd_micros=None, status="unknown",
        )
        cases = (
            ("complete", [actual, second], ["call-1", "call-2"]),
            ("no_coverage", [actual, second], None),
            ("missing_usage", [actual, second], ["call-1", "call-2", "call-3"]),
            ("estimated", [actual, dict(second, status="estimated")], ["call-1", "call-2"]),
            ("unknown", [unknown, actual, second], ["call-1", "call-2", "call-3"]),
        )
        for name, entries, expected in cases:
            with self.subTest(name=name), self.assertRaisesRegex(
                ContractError, "invalid_integer: total_usd_micros"
            ):
                summarize_cost(entries, expected_usage_ids=expected)

    def test_timing_boundaries(self):
        intervals = [
            dict(
                phase="analysis",
                start="2026-09-30T12:00:00Z",
                end="2026-09-30T12:00:10Z",
            ),
            dict(
                phase="execution",
                start="2026-09-30T12:00:05Z",
                end="2026-09-30T12:00:15Z",
            ),
        ]
        summary = summarize_timing("2026-09-30T12:00:00Z", "2026-09-30T12:00:20Z", intervals)
        self.assertEqual(
            summary,
            dict(
                age_seconds=20,
                accepted_seconds=None,
                observed_wall_seconds=15,
                resource_seconds=20,
                human_seconds=None,
            ),
        )

    def test_timing_acceptance_human_and_invalid_intervals(self):
        admitted = "2026-09-30T12:00:00Z"
        observed = "2026-09-30T12:00:10Z"
        interval = dict(
            phase="analysis", start="2026-09-30T12:00:02Z", end="2026-09-30T12:00:08Z",
        )
        self.assertEqual(
            summarize_timing(
                admitted, observed, [interval],
                accepted_at="2026-09-30T12:00:01Z", human_seconds=3,
            ),
            dict(age_seconds=10, accepted_seconds=1, observed_wall_seconds=6,
                 resource_seconds=6, human_seconds=3),
        )
        self.assertEqual(
            summarize_timing(admitted, observed, [], human_seconds=2**63 - 1)["human_seconds"],
            2**63 - 1,
        )
        invalid = (
            ("reversed_observation", observed, admitted, [], None, None),
            ("early_start", admitted, observed,
             [dict(interval, start="2026-09-30T11:59:59Z")], None, None),
            ("late_end", admitted, observed,
             [dict(interval, end="2026-09-30T12:00:11Z")], None, None),
            ("reversed_interval", admitted, observed,
             [dict(interval, start=interval["end"], end=interval["start"])], None, None),
            ("early_acceptance", admitted, observed, [], "2026-09-30T11:59:59Z", None),
            ("late_acceptance", admitted, observed, [], "2026-09-30T12:00:11Z", None),
            ("invalid_timestamp", "bad-time", observed, [], None, None),
            ("boolean_human", admitted, observed, [], None, True),
            ("negative_human", admitted, observed, [], None, -1),
            ("oversized_human", admitted, observed, [], None, 2**63),
        )
        for name, start, end, intervals, accepted, human in invalid:
            with self.subTest(name=name), self.assertRaises(ContractError):
                summarize_timing(
                    start, end, intervals, accepted_at=accepted, human_seconds=human,
                )

    def test_persistence_seam(self):
        versions = {migration.version for migration in discover_migrations()}
        self.assertIn(23, versions)
        self.assertTrue(hasattr(PostgresFactoryStore, "append_decision"))
        sql = Path("factory/src/adaptive_factory/resources/023_factory_v15_decisions.sql").read_text()
        for required in ("SECURITY DEFINER", "factory.persist_phase_decision_v1",
                         "REVOKE INSERT ON factory.decision_records_v1"):
            self.assertIn(required, sql)
        self.assertNotIn("GRANT SELECT, INSERT ON factory.decision_records_v1", sql)
