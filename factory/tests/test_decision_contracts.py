from copy import deepcopy
import json
import subprocess
import unittest
from pathlib import Path

from adaptive_factory.contracts import ContractError
from adaptive_factory.decision_contracts import DecisionRecordV1, summarize_cost, summarize_timing
from adaptive_factory.migrations import discover_migrations
from adaptive_factory.store import PostgresFactoryStore


def decision_facts():
    return dict(
        schema_version=1,
        decision_id="decision-1",
        repository_id="owner/project",
        task_id="00000000-0000-0000-0000-000000000001",
        run_id="00000000-0000-0000-0000-000000000002",
        attempt_id="00000000-0000-0000-0000-000000000003",
        fence=1,
        observed_at="2026-09-30T12:00:00Z",
        decision_kind="state",
        rule_id="RULE-1",
        rule_version="1",
        facts=[
            dict(name="from_state", value="leased"),
            dict(name="target", value="analyzing"),
        ],
        outcome="observed",
        reason_code="phase_started",
        base_sha="1" * 40,
        head_sha="2" * 40,
        context_digest="3" * 64,
        spec_digest="4" * 64,
        profile_digest="5" * 64,
        evidence_refs=["evidence/report.json"],
        constraints=["scope_bound"],
        next_step="verify",
        supersedes=None,
    )


class DecisionContractTests(unittest.TestCase):
    def test_schema_and_parser_reject_closed_missing_and_malformed_records(self):
        schema = Path("factory/contracts/v15/decision-record.v1.schema.json")
        valid = decision_facts()
        self.assertEqual(
            subprocess.run(
                ["jsonschema", str(schema)], input=json.dumps(valid), text=True,
                capture_output=True,
            ).returncode,
            0,
        )
        mutations = []
        for name, mutate in (
            ("unknown", lambda value: value.update(unexpected=True)),
            ("missing", lambda value: value.pop("reason_code")),
            ("digest", lambda value: value.update(context_digest="f" * 63)),
            ("scalar", lambda value: value.update(fence=True)),
        ):
            candidate = deepcopy(valid)
            mutate(candidate)
            mutations.append((name, candidate))
        for name, candidate in mutations:
            with self.subTest(name=name):
                self.assertNotEqual(
                    subprocess.run(
                        ["jsonschema", str(schema)], input=json.dumps(candidate), text=True,
                        capture_output=True,
                    ).returncode,
                    0,
                )
                with self.assertRaises(ContractError):
                    DecisionRecordV1.from_dict(candidate)

    def test_parser_rejects_unsafe_refs_timestamps_digests_and_scalars(self):
        for name, key, value in (
            ("unsafe_ref", "evidence_refs", ["../report.json"]),
            ("secret_ref", "evidence_refs", ["keys/operator.pem"]),
            ("invalid_timestamp", "observed_at", "not-a-time"),
            ("invalid_digest", "profile_digest", "g" * 64),
            ("invalid_spec_digest", "spec_digest", "g" * 64),
            ("invalid_sha", "base_sha", "A" * 40),
            ("invalid_fact_scalar", "facts", [{"name": "risk", "value": 1.5}]),
        ):
            candidate = decision_facts()
            candidate[key] = value
            with self.subTest(name=name), self.assertRaises(ContractError):
                DecisionRecordV1.from_dict(candidate)

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
        entry = dict(
            usage_id="call-1",
            source="provider",
            currency="USD",
            pricing_version="p1",
            amount_usd_micros=120,
            status="actual",
        )
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

    def test_cost_completeness_and_mutation_matrix(self):
        actual = dict(usage_id="call-1", source="provider", currency="USD",
                      pricing_version="p1", amount_usd_micros=120, status="actual")
        unknown = dict(actual, usage_id="call-2", pricing_version=None,
                       amount_usd_micros=None, status="unknown")
        estimated = dict(actual, usage_id="call-2", amount_usd_micros=30,
                         status="estimated")
        self.assertEqual(
            summarize_cost([actual, unknown], expected_usage_ids=["call-1", "call-2"]),
            dict(known_usd_micros=120, complete=False, total_usd_micros=None,
                 unknown_items=1, estimated_items=0),
        )
        self.assertEqual(
            summarize_cost([actual, estimated], expected_usage_ids=["call-1", "call-2"]),
            dict(known_usd_micros=150, complete=False, total_usd_micros=None,
                 unknown_items=0, estimated_items=1),
        )
        self.assertEqual(
            summarize_cost([actual], expected_usage_ids=["call-1", "call-2"])["unknown_items"],
            1,
        )
        self.assertEqual(
            summarize_cost(
                [dict(actual, amount_usd_micros=2**63 - 1)],
                expected_usage_ids=["call-1"],
            )["total_usd_micros"],
            2**63 - 1,
        )
        invalid = (
            (actual, actual),
            (dict(actual, currency="EUR"),),
            (dict(actual, status="projected"),),
            (dict(actual, pricing_version=None),),
            (dict(actual, pricing_version=7),),
            (dict(unknown, amount_usd_micros=0),),
            (dict(actual, amount_usd_micros=True),),
            (dict(actual, amount_usd_micros=2**63),),
        )
        for index, entries in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(ContractError):
                summarize_cost(list(entries), expected_usage_ids=["call-1"])

        with self.assertRaises(ContractError):
            summarize_cost(
                [actual, dict(actual, usage_id="call-2", amount_usd_micros=2**63 - 1)],
                expected_usage_ids=["call-1", "call-2"],
            )

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

    def test_timing_acceptance_human_and_mutation_matrix(self):
        interval = dict(phase="analysis", start="2026-09-30T12:00:02Z",
                        end="2026-09-30T12:00:08Z")
        self.assertEqual(
            summarize_timing(
                "2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [interval],
                accepted_at="2026-09-30T12:00:01Z", human_seconds=3,
            ),
            dict(age_seconds=10, accepted_seconds=1, observed_wall_seconds=6,
                 resource_seconds=6, human_seconds=3),
        )
        invalid = (
            ("2026-09-30T12:00:10Z", "2026-09-30T12:00:00Z", [], None, None),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [dict(interval, start="2026-09-30T11:59:59Z")], None, None),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [dict(interval, end="2026-09-30T12:00:11Z")], None, None),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [dict(interval, start=interval["end"], end=interval["start"])], None, None),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [], "2026-09-30T11:59:59Z", None),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [], "2026-09-30T12:00:11Z", None),
            ("bad-time", "2026-09-30T12:00:10Z", [], None, None),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [], None, True),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [], None, -1),
            ("2026-09-30T12:00:00Z", "2026-09-30T12:00:10Z", [], None, 2**63),
        )
        for index, (admitted, observed, intervals, accepted, human) in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(ContractError):
                summarize_timing(admitted, observed, intervals,
                                 accepted_at=accepted, human_seconds=human)

    def test_persistence_seam(self):
        versions = {migration.version for migration in discover_migrations()}
        self.assertIn(23, versions)
        self.assertTrue(hasattr(PostgresFactoryStore, "append_decision"))
        sql = Path("factory/src/adaptive_factory/resources/023_factory_v15_decisions.sql").read_text()
        for required in ("SECURITY DEFINER", "factory.persist_phase_decision_v1",
                         "REVOKE INSERT ON factory.decision_records_v1"):
            self.assertIn(required, sql)
        self.assertNotIn("GRANT SELECT, INSERT ON factory.decision_records_v1", sql)
