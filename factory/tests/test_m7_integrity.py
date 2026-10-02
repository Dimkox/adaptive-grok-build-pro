"""Regressions for the canonical M7 boundary; no external sources."""
import importlib.util
import unittest


class M7IntegrityTests(unittest.TestCase):
    def test_durable_boundary_exists_without_enabling_sources(self):
        self.assertIsNotNone(importlib.util.find_spec("adaptive_factory.shadow_lookup"))

    def test_unsorted_and_duplicate_references_are_refused(self):
        self.assertIsNotNone(importlib.util.find_spec("adaptive_factory.shadow_lookup"))
        from adaptive_factory.contracts import ContractError
        from adaptive_factory.shadow_lookup import M7MeasurementsV1
        payload = {"schema_version": 1, "cost_usd_micros": None, "latency_ms": None,
                   "repair_count": None, "rollback_count": None, "regression_count": None,
                   "intervention_count": 0, "intervention_coverage": "partial",
                   "session_started_at": None, "session_ended_at": None}
        for refs in (["z", "a"], ["a", "a"]):
            with self.subTest(refs=refs), self.assertRaises(ContractError):
                M7MeasurementsV1.from_dict({**payload, "intervention_source_refs": refs})

    def test_canonical_boundary_rejects_decomposed_controls_and_byte_overflow(self):
        self.assertIsNotNone(importlib.util.find_spec("adaptive_factory.shadow_lookup"))
        from adaptive_factory.contracts import ContractError
        from adaptive_factory.shadow_lookup import canonical_m7_bytes
        self.assertEqual(canonical_m7_bytes({"name": "caf\u00e9"}), b'{"name":"caf\xc3\xa9"}')
        for text in ("cafe\u0301", "a\u007f", "a\u0085", "\u00e9" * 2049):
            with self.subTest(text=text[:8]), self.assertRaises(ContractError):
                canonical_m7_bytes({"name": text})

    def test_digest_uses_one_domain_and_exact_canonical_bytes(self):
        self.assertIsNotNone(importlib.util.find_spec("adaptive_factory.shadow_lookup"))
        import hashlib
        from adaptive_factory.shadow_lookup import m7_digest
        expected = hashlib.sha256(b"synthetic/v1\0" + b'{"name":"caf\xc3\xa9"}').hexdigest()
        self.assertEqual(m7_digest("synthetic/v1", {"name": "caf\u00e9"}), expected)

    def test_lookup_distinguishes_found_missing_stale_ambiguous_invalid_unavailable(self):
        from factory.tests.test_shadow_lookup import result_fixture
        self.assertEqual(result_fixture().lookup_outcome, "found")
        for reason, outcome in (("registration_missing", "not_found"), ("epoch_expired", "stale"),
                                ("github_source_conflict", "ambiguous"), ("check_corrupt", "invalid"),
                                ("reader_unconfigured", "unavailable")):
            with self.subTest(reason=reason):
                self.assertEqual(result_fixture(registration=None, outcome=None, check=None,
                    github=None, epoch=None, unavailable_reasons=(reason,)).lookup_outcome, outcome)


if __name__ == "__main__":
    unittest.main()
