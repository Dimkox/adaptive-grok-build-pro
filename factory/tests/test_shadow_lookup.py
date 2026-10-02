"""Synthetic M7.1 contracts and observation-only preflight, with no live sources."""
from dataclasses import fields
import json
from pathlib import Path
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.shadow_contracts import ReadyForPrBundleV1
from adaptive_factory.shadow_lookup import (
    M7BundleRegistrationV1, M7LookupRequestV1, M7LookupResultV1,
    M7OutcomeObservationV1, M7CheckObservationV1, M7GitHubContextV1,
    M7EpochContextV1, M7MeasurementsV1, M7ProfileMetadataV1,
    M7SourceProvenanceV1, SourceUnavailable, build_lookup_result,
)
from adaptive_factory.shadow_sources import (
    UnavailableHumanOutcomeSource, UnavailableSignedCiSource,
    UnavailableGitHubCurrentSource, UnavailableDeployedEpochSource,
)
from adaptive_factory.m7_preflight import inspect_m7_durable_evidence
from factory.tests.test_shadow_contracts import build_bundle

NOW = "2026-09-10T12:00:00Z"


def registration_payload():
    return {"schema_version": 1, "generation": 1, "bundle": build_bundle().to_dict(), "profile": None}


def request_payload():
    bundle = build_bundle()
    return {
        "schema_version": 1, "repository_id": bundle.evidence.m5.repository_id,
        "task_id": bundle.evidence.m4.task_id, "run_id": bundle.evidence.m4.run_id,
        "generation": 1, "bundle_digest": bundle.digest, "profile_digest": None,
        "pr_number": 7, "base_sha": "1" * 40, "head_sha": "2" * 40,
        "app_id": 7, "check_name": "synthetic-check", "policy_digest": "7" * 64,
        "holdout_digest": "8" * 64,
    }


def provenance(kind="human_outcome", revision=1, predecessor=None):
    return {
        "schema_version": 1, "source_id": "synthetic-" + kind,
        "source_kind": kind, "adapter_version": "synthetic-v1",
        "source_event_id": "event-" + str(revision), "source_revision": revision,
        "predecessor_digest": predecessor, "source_issued_at": NOW,
        "observed_at": NOW, "valid_until": "2026-09-10T13:00:00Z",
        "trust_config_digest": "9" * 64, "evidence_ref": "synthetic:evidence",
        "verifier_id": "synthetic-verifier",
    }


def measurements(**overrides):
    return {
        "schema_version": 1, "cost_usd_micros": None, "latency_ms": None,
        "repair_count": None, "rollback_count": None, "regression_count": None,
        "intervention_count": None, "intervention_coverage": "unknown",
        "intervention_source_refs": [], "session_started_at": None, "session_ended_at": None,
        **overrides,
    }


def outcome_payload(**overrides):
    request = request_payload()
    return {
        "schema_version": 1, "repository_id": request["repository_id"],
        "bundle_digest": request["bundle_digest"], "result_head_sha": request["head_sha"],
        "provenance": provenance(), "decision": "accepted", "outcome": None,
        "profile": None, "measurements": measurements(), **overrides,
    }


def check_payload(**overrides):
    request = request_payload()
    return {
        "schema_version": 1,
        **{name: request[name] for name in ("repository_id", "pr_number", "base_sha", "head_sha", "policy_digest", "holdout_digest")},
        "external_job_id": "synthetic-job", "attestation_digest": "a" * 64,
        "signer_key_id": "synthetic-signer", "result": "passed",
        "provenance": provenance("signed_ci"), **overrides,
    }


def github_payload(**overrides):
    request = request_payload()
    return {
        "schema_version": 1,
        **{name: request[name] for name in ("repository_id", "pr_number", "base_sha", "head_sha", "app_id", "check_name")},
        "external_job_id": "synthetic-job", "check_id": 8,
        "check_state": "completed", "check_conclusion": "success", "revoked": False,
        "provenance": provenance("github_current"), **overrides,
    }


def epoch_payload(**overrides):
    request = request_payload()
    return {
        "schema_version": 1,
        **{name: request[name] for name in ("repository_id", "policy_digest", "holdout_digest", "app_id", "check_name")},
        "revoked": False, "provenance": provenance("deployed_epoch"), **overrides,
    }


def result_fixture(**overrides):
    facts = {
        "request": M7LookupRequestV1.from_dict(request_payload()), "observed_at": NOW,
        "registration": M7BundleRegistrationV1.from_dict(registration_payload()),
        "outcome": M7OutcomeObservationV1.from_dict(outcome_payload()),
        "check": M7CheckObservationV1.from_dict(check_payload()),
        "github": M7GitHubContextV1.from_dict(github_payload()),
        "epoch": M7EpochContextV1.from_dict(epoch_payload()),
        "unavailable_reasons": (), "source_modes": ("synthetic",),
    }
    return build_lookup_result(**{**facts, **overrides})


class M7LookupContractTests(unittest.TestCase):
    def test_default_preflight_and_four_source_defaults_are_unavailable(self):
        request = M7LookupRequestV1.from_dict(request_payload())
        result = inspect_m7_durable_evidence(request)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.authority_effect, "none")
        self.assertEqual(result.m8_qualification, "not_evaluated")
        self.assertIn("reader_unconfigured", result.unavailable_reasons)
        for source in (UnavailableHumanOutcomeSource(), UnavailableSignedCiSource(),
                       UnavailableGitHubCurrentSource(), UnavailableDeployedEpochSource()):
            self.assertIsInstance(source.resolve(request), SourceUnavailable)

    def test_partial_acceptance_stays_resolved_without_fabricating_metrics(self):
        result = result_fixture()
        self.assertEqual(result.acceptance, "accepted")
        self.assertEqual(result.signed_check, "valid")
        self.assertEqual(result.currentness, "current")
        self.assertEqual(result.coverage["profile"], "unknown")
        self.assertEqual(result.coverage["measurements"], "unknown")
        self.assertIsNone(result.outcome.measurements.intervention_count)
        self.assertEqual(result.authority_effect, "none")

    def test_rejection_and_withdrawal_are_resolved_negative_facts(self):
        for decision in ("rejected", "withdrawn"):
            result = result_fixture(outcome=M7OutcomeObservationV1.from_dict(outcome_payload(decision=decision)))
            self.assertEqual(result.acceptance, decision)
            self.assertEqual(result.status, "resolved")

    def test_contracts_reject_extra_caller_flags_and_nested_tampering(self):
        pairs = [
            (M7LookupRequestV1, request_payload()), (M7BundleRegistrationV1, registration_payload()),
            (M7OutcomeObservationV1, outcome_payload()), (M7CheckObservationV1, check_payload()),
            (M7GitHubContextV1, github_payload()), (M7EpochContextV1, epoch_payload()),
        ]
        for cls, valid in pairs:
            with self.subTest(contract=cls.__name__):
                with self.assertRaises(ContractError):
                    cls.from_dict({**valid, "verified": True})
        changed = registration_payload()
        changed["bundle"]["evidence"]["m6"]["verdict"]["subject_digest"] = "f" * 64
        with self.assertRaises(ContractError):
            M7BundleRegistrationV1.from_dict(changed)

    def test_integer_boolean_and_timestamp_bounds(self):
        for value in (True, 0, -1, 2**63, 1.0):
            with self.subTest(value=value), self.assertRaises(ContractError):
                M7LookupRequestV1.from_dict({**request_payload(), "pr_number": value})
        for value in ("2026-09-10", "2026-09-10T12:00:00", "2026-09-10T12:00:00+00:99"):
            with self.subTest(value=value), self.assertRaises(ContractError):
                M7SourceProvenanceV1.from_dict({**provenance(), "observed_at": value})

    def test_canonical_roundtrips_and_domain_separated_digests(self):
        result = result_fixture()
        self.assertEqual(M7LookupResultV1.from_dict(result.to_dict()), result)
        self.assertEqual(result.digest, M7LookupResultV1.from_dict(json.loads(json.dumps(result.to_dict()))).digest)
        self.assertEqual(result.request.digest, result.to_dict()["request_digest"])
        forged = result.to_dict()
        forged["currentness"] = "stale"
        with self.assertRaises(ContractError):
            M7LookupResultV1.from_dict(forged)

    def test_partial_zero_requires_coverage_and_full_sessions_require_boundaries(self):
        with self.assertRaises(ContractError):
            M7MeasurementsV1.from_dict(measurements(intervention_count=0))
        partial = M7MeasurementsV1.from_dict(measurements(
            intervention_count=0, intervention_coverage="partial", intervention_source_refs=["synthetic:events"]))
        self.assertEqual(partial.intervention_coverage, "partial")
        with self.assertRaises(ContractError):
            M7MeasurementsV1.from_dict({**partial.to_dict(), "intervention_coverage": "complete"})

    def test_new_context_and_expired_or_revoked_evidence_cannot_keep_old_green(self):
        for facts in (
            {"epoch": M7EpochContextV1.from_dict(epoch_payload(policy_digest="b" * 64))},
            {"github": M7GitHubContextV1.from_dict(github_payload(head_sha="c" * 40))},
            {"github": M7GitHubContextV1.from_dict(github_payload(revoked=True))},
            {"observed_at": "2026-09-10T14:00:00Z"},
        ):
            with self.subTest(facts=facts):
                self.assertNotEqual(result_fixture(**facts).currentness, "current")

    def test_subject_swaps_and_profile_repository_mismatch_are_rejected(self):
        with self.assertRaises(ContractError):
            result_fixture(outcome=M7OutcomeObservationV1.from_dict(outcome_payload(result_head_sha="f" * 40)))
        raw = registration_payload()
        raw["profile"] = {"repository_id": "other/repository"}
        with self.assertRaises(ContractError):
            M7BundleRegistrationV1.from_dict(raw)

    def test_profile_missing_fields_remain_unknown_and_unsupported_class_visible(self):
        partial = M7ProfileMetadataV1.from_dict({"task_class": "code_change"})
        outcome = outcome_payload(profile=partial.to_dict())
        result = result_fixture(outcome=M7OutcomeObservationV1.from_dict(outcome))
        self.assertEqual(result.coverage["profile"], "partial")
        self.assertEqual(result.coverage["task_class"], "unsupported")
        self.assertIn("prompt_digest", result.coverage["missing_profile_fields"])

    def test_result_reparses_nested_producer_objects(self):
        registration = M7BundleRegistrationV1.from_dict(registration_payload())
        object.__setattr__(registration.bundle, "bundle_digest", "f" * 64)
        with self.assertRaises(ContractError):
            result_fixture(registration=registration)

    def test_reader_outage_returns_no_cached_result(self):
        class Reader:
            def lookup(self, request):
                raise ConnectionError("synthetic outage")
        result = inspect_m7_durable_evidence(M7LookupRequestV1.from_dict(request_payload()), reader=Reader())
        self.assertEqual(result.status, "unavailable")
        self.assertIn("reader_unavailable", result.unavailable_reasons)

    def test_old_bundle_wire_status_remains_blocked(self):
        registration = M7BundleRegistrationV1.from_dict(registration_payload())
        self.assertEqual(ReadyForPrBundleV1.from_dict(registration.bundle.to_dict()).status,
                         "blocked_pending_durable_lookup")

    def test_policy_epoch_check_name_and_unconfigured_source_evidence(self):
        wire = {**request_payload(), "check_name": "adaptive-trust-ci/verified@" + "b" * 12}
        self.assertEqual(M7LookupRequestV1.from_dict(wire).check_name, wire["check_name"])
        self.assertEqual(result_fixture(source_modes=()).acceptance, "unavailable")
        with self.assertRaises(ContractError):
            M7SourceProvenanceV1.from_dict({**provenance(), "evidence_ref": "https://invalid.example/source"})

    def test_schema_is_closed_and_covers_every_representable_wire_record(self):
        schema_path = Path(__file__).resolve().parents[1] / "contracts/jsonschema/m7-durable-lookup.v1.schema.json"
        document = json.loads(schema_path.read_text())
        pairs = (
            (M7LookupRequestV1, request_payload()), (M7BundleRegistrationV1, registration_payload()),
            (M7SourceProvenanceV1, provenance()), (M7MeasurementsV1, measurements()),
            (M7OutcomeObservationV1, outcome_payload()), (M7CheckObservationV1, check_payload()),
            (M7GitHubContextV1, github_payload()), (M7EpochContextV1, epoch_payload()),
            (M7ProfileMetadataV1, {}), (SourceUnavailable, {"schema_version": 1, "reason": "source_unconfigured"}),
            (M7LookupResultV1, result_fixture().to_dict()),
        )
        for cls, payload in pairs:
            with self.subTest(contract=cls.__name__):
                schema = document["$defs"][cls.__name__]
                wire = cls.from_dict(payload).to_dict()
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(set(schema["properties"]), set(wire))
                self.assertEqual(set(schema["required"]), set(wire))
                self.assertGreaterEqual(len(schema["properties"]), len(fields(cls)))
                with self.assertRaises(ContractError):
                    cls.from_dict({**payload, "unexpected": "field"})


    def test_currentness_does_not_depend_on_acceptance_or_measurement_coverage(self):
        for reason, outcome in (("outcome_missing", None), ("outcome_rejected", M7OutcomeObservationV1.from_dict(outcome_payload(decision="rejected")))):
            result = result_fixture(outcome=outcome, unavailable_reasons=(reason,))
            self.assertEqual(result.currentness, "current")

    def test_sql_wire_catalog_matches_the_public_closed_schemas(self):
        root = Path(__file__).resolve().parents[1]
        schemas = {path.name: json.loads(path.read_text()) for path in (root / "contracts/jsonschema").glob("*.json")}
        by_id = {value["$id"]: value for value in schemas.values() if "$id" in value}
        def expand(value, current):
            if isinstance(value, list):
                return [expand(item, current) for item in value]
            if not isinstance(value, dict):
                return value
            if "$ref" in value:
                reference, _, pointer = value["$ref"].partition("#")
                target = current if not reference else schemas.get(reference, by_id.get(reference))
                self.assertIsNotNone(target)
                resolved = target
                for part in pointer.lstrip("/").split("/") if pointer else ():
                    resolved = resolved[part.replace("~1", "/").replace("~0", "~")]
                return expand(resolved, target)
            return {key: expand(item, current) for key, item in value.items()
                    if key not in {"$id", "$schema", "$defs", "title", "description", "$comment"}}
        schema = schemas["m7-durable-lookup.v1.schema.json"]
        sql = (root / "src/adaptive_factory/resources/026_m7_durable_evidence.sql").read_text()
        catalog = json.loads(sql.split("$json$", 2)[1])
        self.assertEqual(set(catalog), {"M7LookupRequestV1", "M7BundleRegistrationV1", "M7OutcomeObservationV1",
                                        "M7CheckObservationV1", "M7GitHubContextV1", "M7EpochContextV1"})
        for name, entry in catalog.items():
            self.assertEqual(entry, expand(schema["$defs"][name], schema))
