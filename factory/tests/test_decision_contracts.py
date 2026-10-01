from copy import deepcopy
import json
import unittest
from pathlib import Path

from adaptive_factory.contracts import ContractError
from adaptive_factory.decision_contracts import DecisionRecordV1, summarize_cost, summarize_timing
from adaptive_factory.migrations import discover_migrations
from adaptive_factory.store import PostgresFactoryStore
from tests.json_schema_subset import SubsetValidator


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

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertFalse(self.validator.is_valid(mutation))

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

    def test_persistence_seam(self):
        versions = {migration.version for migration in discover_migrations()}
        self.assertIn(23, versions)
        self.assertTrue(hasattr(PostgresFactoryStore, "append_decision"))
        sql = Path("factory/src/adaptive_factory/resources/023_factory_v15_decisions.sql").read_text()
        for required in ("SECURITY DEFINER", "factory.persist_phase_decision_v1",
                         "REVOKE INSERT ON factory.decision_records_v1"):
            self.assertIn(required, sql)
        self.assertNotIn("GRANT SELECT, INSERT ON factory.decision_records_v1", sql)
