from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from adaptive_factory.contracts import ContractError, TaskIntakeV1, canonical_digest


NOW = datetime(2026, 8, 31, 20, 0, tzinfo=timezone.utc)


def valid_intake():
    return {
        "contract_version": 1,
        "request_id": "request-001",
        "repository_id": "owner/repository",
        "source_type": "manual",
        "source_id": "ticket-42",
        "source_digest": "d" * 64,
        "route_id": "b7f288f1e81e",
        "change_id": "20260831-m4-control-plane",
        "exact_base_sha": "1" * 40,
        "spec_digest": "a" * 64,
        "architecture": {
            "architecture_contract_version": 1,
            "architecture_digest": "b" * 64,
            "architecture_evidence_digest": "c" * 64,
            "exact_base_sha": "2" * 40,
            "exact_head_sha": "3" * 40,
        },
        "governance": {
            "governance_contract_version": 1,
            "governance_digest": "e" * 64,
            "governance_evidence_digest": "f" * 64,
            "architecture_digest": "b" * 64,
            "exact_base_sha": "2" * 40,
            "exact_head_sha": "3" * 40,
        },
        "policy_digest": "06ecf1c875bc" + "9" * 52,
        "m0_authority": {
            "observed_at": NOW.isoformat(),
            "check_name": "adaptive-trust-ci/verified@06ecf1c875bc",
            "exact_head_sha": "3" * 40,
        },
        "acceptance_ids": ["AC-001", "AC-002"],
        "limits": {
            "wall_seconds": 14400,
            "max_cost_usd_micros": 25000000,
            "max_token_units": 2000000,
            "max_output_bytes": 10000000,
            "max_events": 100000,
            "infrastructure_retries": 2,
            "semantic_repairs": 3,
        },
    }


class ContractTests(unittest.TestCase):
    def test_valid_intake_binds_all_frozen_authorities(self):
        intake = TaskIntakeV1.from_dict(valid_intake(), now=NOW)
        self.assertEqual(intake.spec_digest, "a" * 64)
        self.assertEqual(intake.architecture.architecture_contract_version, 1)
        self.assertEqual(intake.governance.governance_contract_version, 1)
        self.assertEqual(len(intake.intent_digest), 64)
        self.assertEqual(len(intake.idempotency_key), 64)
        self.assertEqual(intake.limits.wall_seconds, 14400)

    def test_complete_frozen_intent_defines_duplicate_identity(self):
        original = valid_intake()
        replay = TaskIntakeV1.from_dict(original, now=NOW)
        self.assertEqual(replay.idempotency_key, TaskIntakeV1.from_dict(valid_intake(), now=NOW).idempotency_key)
        changed_limits = valid_intake()
        changed_limits["limits"]["max_events"] -= 1
        changed_head = valid_intake()
        for handoff in (changed_head["architecture"], changed_head["governance"]):
            handoff["exact_head_sha"] = "4" * 40
        changed_head["m0_authority"]["exact_head_sha"] = "4" * 40
        changed_evidence = valid_intake()
        changed_evidence["architecture"]["architecture_evidence_digest"] = "8" * 64
        for changed in (changed_limits, changed_head, changed_evidence):
            parsed = TaskIntakeV1.from_dict(changed, now=NOW)
            self.assertNotEqual(parsed.intent_digest, replay.intent_digest)
            self.assertNotEqual(parsed.idempotency_key, replay.idempotency_key)

    def test_transport_and_m0_proof_do_not_change_semantic_work_identity(self):
        original_payload = valid_intake()
        original = TaskIntakeV1.from_dict(original_payload, now=NOW)
        refreshed_payload = valid_intake()
        refreshed_payload["request_id"] = "request-002"
        refreshed_payload["m0_authority"]["observed_at"] = (
            NOW + timedelta(seconds=1)
        ).isoformat()
        refreshed = TaskIntakeV1.from_dict(
            refreshed_payload,
            now=NOW + timedelta(seconds=1),
        )

        self.assertNotEqual(original.intent_digest, refreshed.intent_digest)
        self.assertEqual(original.idempotency_key, refreshed.idempotency_key)
        work_identity = original.to_dict()
        for field in ("request_id", "m0_authority", "intent_digest", "idempotency_key"):
            work_identity.pop(field)
        self.assertEqual(
            original.idempotency_key,
            canonical_digest(
                {
                    "contract": "adaptive-factory.work-identity/v1",
                    "work": work_identity,
                }
            ),
        )

    def test_each_semantic_work_field_changes_identity_but_m0_form_does_not(self):
        baseline_payload = valid_intake()
        baseline = TaskIntakeV1.from_dict(baseline_payload, now=NOW)

        def changed(path, value, *companions):
            payload = deepcopy(baseline_payload)
            for item_path, item_value in ((path, value), *companions):
                target = payload
                for component in item_path[:-1]:
                    target = target[component]
                target[item_path[-1]] = item_value
            return payload

        cases = [
            ("repository_id", changed(("repository_id",), "other/repository")),
            ("source_type", changed(("source_type",), "api")),
            ("source_id", changed(("source_id",), "ticket-43")),
            ("source_digest", changed(("source_digest",), "8" * 64)),
            ("route_id", changed(("route_id",), "other-route")),
            ("change_id", changed(("change_id",), "other-change")),
            ("exact_base_sha", changed(("exact_base_sha",), "4" * 40)),
            ("spec_digest", changed(("spec_digest",), "8" * 64)),
            (
                "architecture_digest",
                changed(
                    ("architecture", "architecture_digest"),
                    "8" * 64,
                    (("governance", "architecture_digest"), "8" * 64),
                ),
            ),
            (
                "architecture_evidence_digest",
                changed(("architecture", "architecture_evidence_digest"), "8" * 64),
            ),
            (
                "handoff_exact_base_sha",
                changed(
                    ("architecture", "exact_base_sha"),
                    "4" * 40,
                    (("governance", "exact_base_sha"), "4" * 40),
                ),
            ),
            (
                "handoff_exact_head_sha",
                changed(
                    ("architecture", "exact_head_sha"),
                    "4" * 40,
                    (("governance", "exact_head_sha"), "4" * 40),
                    (("m0_authority", "exact_head_sha"), "4" * 40),
                ),
            ),
            ("governance_digest", changed(("governance", "governance_digest"), "8" * 64)),
            (
                "governance_evidence_digest",
                changed(("governance", "governance_evidence_digest"), "8" * 64),
            ),
            (
                "policy_digest",
                changed(
                    ("policy_digest",),
                    "abcdefabcdef" + "8" * 52,
                    (
                        ("m0_authority", "check_name"),
                        "adaptive-trust-ci/verified@abcdefabcdef",
                    ),
                ),
            ),
            (
                "acceptance_ids",
                changed(("acceptance_ids",), ["AC-001", "AC-002", "AC-003"]),
            ),
        ]
        limit_values = {
            "wall_seconds": 14_399,
            "max_cost_usd_micros": 24_999_999,
            "max_token_units": 1_999_999,
            "max_output_bytes": 9_999_999,
            "max_events": 99_999,
            "infrastructure_retries": 1,
            "semantic_repairs": 2,
        }
        cases.extend(
            (f"limits.{name}", changed(("limits", name), value))
            for name, value in limit_values.items()
        )
        for name, payload in cases:
            with self.subTest(field=name):
                parsed = TaskIntakeV1.from_dict(payload, now=NOW)
                self.assertNotEqual(parsed.idempotency_key, baseline.idempotency_key)

        bootstrap_payload = deepcopy(baseline_payload)
        bootstrap_payload["m0_authority"] = {
            "bootstrap_exception": "M0-bootstrap-semantic-identity",
            "issuer": "repository-owner",
            "scope": "m4-disposable-local",
            "expires_at": (NOW + timedelta(minutes=10)).isoformat(),
        }
        bootstrap = TaskIntakeV1.from_dict(bootstrap_payload, now=NOW)
        self.assertNotEqual(bootstrap.intent_digest, baseline.intent_digest)
        self.assertEqual(bootstrap.idempotency_key, baseline.idempotency_key)

    def test_observed_m0_check_suffix_must_match_policy_identity(self):
        payload = valid_intake()
        payload["policy_digest"] = "9" * 64
        with self.assertRaisesRegex(ContractError, "m0_policy_mismatch"):
            TaskIntakeV1.from_dict(payload, now=NOW)

    def test_unknown_fields_versions_dirty_sha_and_excessive_limits_fail(self):
        cases = []
        unknown = valid_intake()
        unknown["command"] = "git push"
        cases.append((unknown, "unknown_fields"))
        version = valid_intake()
        version["contract_version"] = 2
        cases.append((version, "unsupported_version"))
        sha = valid_intake()
        sha["exact_base_sha"] = "dirty"
        cases.append((sha, "invalid_sha"))
        limits = valid_intake()
        limits["limits"]["wall_seconds"] = 14401
        cases.append((limits, "limit_exceeded"))
        for payload, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                TaskIntakeV1.from_dict(payload, now=NOW)

    def test_handoff_mismatch_duplicate_acceptance_and_stale_m0_fail(self):
        mismatch = valid_intake()
        mismatch["governance"]["architecture_digest"] = "8" * 64
        duplicate = valid_intake()
        duplicate["acceptance_ids"] = ["AC-001", "AC-001"]
        stale = valid_intake()
        stale["m0_authority"]["observed_at"] = (NOW - timedelta(seconds=301)).isoformat()
        for payload, code in ((mismatch, "handoff_mismatch"), (duplicate, "acceptance_ids"), (stale, "stale_m0")):
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, code):
                TaskIntakeV1.from_dict(payload, now=NOW)

    def test_named_bootstrap_exception_is_bounded(self):
        payload = valid_intake()
        payload["m0_authority"] = {
            "bootstrap_exception": "M0-bootstrap-2026-08-31",
            "issuer": "repository-owner",
            "scope": "m4-disposable-local",
            "expires_at": (NOW + timedelta(minutes=10)).isoformat(),
        }
        intake = TaskIntakeV1.from_dict(payload, now=NOW)
        self.assertEqual(intake.m0_authority.bootstrap_exception, "M0-bootstrap-2026-08-31")

    def test_canonical_digest_is_order_independent(self):
        self.assertEqual(canonical_digest({"b": 2, "a": 1}), canonical_digest({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
