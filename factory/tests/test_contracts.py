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
        "policy_digest": "9" * 64,
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
