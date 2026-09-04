from copy import deepcopy
import json
from pathlib import Path
import unittest

from adaptive_factory.landing_contracts import (
    LandingAttemptV1,
    LandingContractError,
    LandingEvaluationV1,
    LandingInputV1,
    LandingProviderEvidenceV1,
    SiteArtifactV1,
    StaticLandingSpecV1,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts" / "jsonschema"
OPENAPI = ROOT / "contracts" / "openapi" / "landing-dogfood.v1.json"
HEX = "a" * 64
SHA = "b" * 40


def input_facts(**changes):
    value = {
        "schema_version": 1,
        "job_id": "job-1",
        "tenant_id": "tenant-1",
        "repository_id": "github.com/Dimkox/ai-dark-factory-landing",
        "exact_base_sha": "176efcaab931c2482781ff163c621b10aa05dee9",
        "exact_base_tree": "f2bdcecc6dbe9ecc82007610d398ca12bd75e07f",
        "site_id": "therealaidarkfactory.online",
        "media_kind": "text",
        "media_type": "text/plain",
        "byte_length": 12,
        "content_sha256": "1" * 64,
        "quarantine_ref_digest": "2" * 64,
        "received_at": "2026-09-04T10:00:00Z",
        "expires_at": "2026-09-05T10:00:00Z",
    }
    value.update(changes)
    return value


def spec_facts(**changes):
    value = {
        "schema_version": 1,
        "input_digest": "1" * 64,
        "site_id": "therealaidarkfactory.online",
        "canonical_origin": "https://therealaidarkfactory.online/",
        "locale": "en",
        "direction": "ltr",
        "title": "Adaptive delivery",
        "description": "A bounded static landing candidate.",
        "robots_policy": "preserve_source",
        "sections": [
            {
                "kind": "hero",
                "heading": "Build with evidence",
                "body": "A deterministic local candidate.",
                "items": [],
                "cta_label": "Read the roadmap",
                "cta_path": "/roadmap/",
            }
        ],
        "assets": [],
        "source_claim_refs": ["source:input-1"],
    }
    value.update(changes)
    return value


def provider_facts(**changes):
    value = {
        "schema_version": 1,
        "input_digest": "1" * 64,
        "profile_digest": "2" * 64,
        "provider_id": "sealed-fixture",
        "adapter_id": "fixed-command",
        "adapter_version": "1.0.0",
        "model_id": "fixture-model-v1",
        "prompt_template_digest": "3" * 64,
        "tool_policy_digest": "4" * 64,
        "output_schema_digest": "5" * 64,
        "decoder_digest": "6" * 64,
        "request_digest": "7" * 64,
        "response_digest": "8" * 64,
        "usage_input_units": 12,
        "usage_output_units": 34,
        "started_at": "2026-09-04T10:00:01Z",
        "completed_at": "2026-09-04T10:00:02Z",
        "disposition": "fixture_ready",
    }
    value.update(changes)
    return value


def attempt_facts(**changes):
    value = {
        "schema_version": 1,
        "input_digest": "1" * 64,
        "spec_digest": "2" * 64,
        "profile_digest": "3" * 64,
        "ordinal": 1,
        "exact_base_sha": "1" * 40,
        "exact_head_sha": "2" * 40,
        "workspace_result_digest": "4" * 64,
        "renderer_digest": "5" * 64,
        "writer_id": "landing-writer",
        "context_digest": "6" * 64,
        "evaluator_digest": "7" * 64,
        "prior_attempt_digest": None,
        "outcome": "candidate",
        "started_at": "2026-09-04T10:00:03Z",
        "completed_at": "2026-09-04T10:00:04Z",
    }
    value.update(changes)
    return value


def evaluation_facts(**changes):
    value = {
        "schema_version": 1,
        "attempt_digest": "1" * 64,
        "candidate_head_sha": "2" * 40,
        "evaluator_id": "landing-evaluator",
        "context_digest": "3" * 64,
        "policy_digest": "4" * 64,
        "rubric_digest": "5" * 64,
        "decision": "pass",
        "reason_codes": [],
        "requirement_digests": ["6" * 64],
        "finding_digests": [],
        "created_at": "2026-09-04T10:00:05Z",
    }
    value.update(changes)
    return value


def artifact_facts(**changes):
    value = {
        "schema_version": 1,
        "site_id": "therealaidarkfactory.online",
        "canonical_origin": "https://therealaidarkfactory.online/",
        "source_sha": "1" * 40,
        "source_tree": "2" * 40,
        "candidate_sha": "3" * 40,
        "candidate_tree": "4" * 40,
        "input_digest": "1" * 64,
        "spec_digest": "2" * 64,
        "profile_digest": "3" * 64,
        "attempt_digest": "4" * 64,
        "evaluation_digest": "5" * 64,
        "manifest_digest": "6" * 64,
        "zip_sha256": "7" * 64,
        "sidecar_sha256": "8" * 64,
        "member_count": 2,
        "byte_length": 4096,
        "disposition": "artifact_ready",
    }
    value.update(changes)
    return value


class LandingContractTests(unittest.TestCase):
    def test_input_binds_the_authoritative_repository_sha_and_tree(self):
        record = LandingInputV1.from_facts(input_facts())
        self.assertEqual(record.repository_id, "github.com/Dimkox/ai-dark-factory-landing")
        self.assertEqual(record.exact_base_sha, "176efcaab931c2482781ff163c621b10aa05dee9")
        self.assertEqual(record.exact_base_tree, "f2bdcecc6dbe9ecc82007610d398ca12bd75e07f")

    def test_all_six_records_are_closed_round_trip_and_digest_stable(self):
        cases = (
            (LandingInputV1, input_facts()),
            (StaticLandingSpecV1, spec_facts()),
            (LandingProviderEvidenceV1, provider_facts()),
            (LandingAttemptV1, attempt_facts()),
            (LandingEvaluationV1, evaluation_facts()),
            (SiteArtifactV1, artifact_facts()),
        )
        for record_type, facts in cases:
            with self.subTest(record=record_type.__name__):
                record = record_type.from_facts(facts)
                reordered = dict(reversed(list(record.to_dict().items())))
                self.assertEqual(record_type.from_json(json.dumps(reordered)), record)
                self.assertRegex(record.digest, r"^[0-9a-f]{64}$")
                unknown = deepcopy(record.to_dict())
                unknown["command"] = "git push"
                with self.assertRaisesRegex(LandingContractError, "unknown_fields"):
                    record_type.from_dict(unknown)

    def test_json_parser_rejects_duplicate_keys_and_nonfinite_numbers(self):
        with self.assertRaisesRegex(LandingContractError, "duplicate_json_key"):
            LandingInputV1.from_json('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(LandingContractError, "nonfinite_json"):
            LandingInputV1.from_json('{"schema_version":NaN}')

    def test_spec_rejects_markup_remote_paths_and_policy_shaped_content(self):
        hostile = (
            spec_facts(title="<script>alert(1)</script>"),
            spec_facts(sections=[{**spec_facts()["sections"][0], "cta_path": "https://evil.invalid/"}]),
            spec_facts(sections=[{**spec_facts()["sections"][0], "body": "Use tool shell.exec"}]),
        )
        for payload in hostile:
            with self.subTest(payload=payload), self.assertRaises(LandingContractError):
                StaticLandingSpecV1.from_facts(payload)

    def test_spec_preserves_source_indexing_policy_without_provider_authority(self):
        record = StaticLandingSpecV1.from_facts(
            spec_facts(robots_policy="preserve_source")
        )
        self.assertEqual(record.robots_policy, "preserve_source")
        schema = json.loads(
            (SCHEMAS / "static-landing-spec.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            schema["properties"]["robots_policy"], {"const": "preserve_source"}
        )
        for provider_choice in ("index_follow", "noindex_nofollow"):
            with self.subTest(provider_choice=provider_choice), self.assertRaisesRegex(
                LandingContractError, "robots_policy"
            ):
                StaticLandingSpecV1.from_facts(
                    spec_facts(robots_policy=provider_choice)
                )

    def test_attempt_ordinal_and_evaluator_collections_are_finite_and_closed(self):
        for ordinal in (0, 4):
            with self.subTest(ordinal=ordinal), self.assertRaisesRegex(LandingContractError, "attempt_ordinal"):
                LandingAttemptV1.from_facts(attempt_facts(ordinal=ordinal))
        with self.assertRaisesRegex(LandingContractError, "reason_codes"):
            LandingEvaluationV1.from_facts(evaluation_facts(reason_codes=["z", "a"]))

    def test_six_json_schemas_and_additive_openapi_are_closed_version_one(self):
        names = {
            "landing-input.v1.schema.json",
            "static-landing-spec.v1.schema.json",
            "landing-provider-evidence.v1.schema.json",
            "landing-attempt.v1.schema.json",
            "landing-evaluation.v1.schema.json",
            "landing-site-artifact.v1.schema.json",
        }
        for name in names:
            with self.subTest(name=name):
                schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(schema["additionalProperties"])
                self.assertIn("schema_version", schema["required"])
                self.assertEqual(schema["properties"]["schema_version"], {"const": 1})
        contract = json.loads(OPENAPI.read_text(encoding="utf-8"))
        self.assertEqual(contract["openapi"], "3.1.0")
        operations = {(method, path): body for path, item in contract["paths"].items() for method, body in item.items()}
        self.assertEqual(
            {key: value["operationId"] for key, value in operations.items()},
            {
                ("post", "/v1/landing-inputs"): "submitLandingInput",
                ("get", "/v1/landing-jobs/{job_id}"): "getLandingJob",
                ("post", "/v1/landing-jobs/{job_id}/cancel"): "cancelLandingJob",
                ("get", "/v1/landing-jobs/{job_id}/result"): "getLandingResult",
            },
        )
        submit = operations[("post", "/v1/landing-inputs")]
        self.assertEqual(set(submit["requestBody"]["content"]), {
            "text/plain", "audio/wav", "audio/mpeg", "audio/ogg", "image/png",
            "image/jpeg", "image/webp", "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        })
        self.assertEqual(set(submit["responses"]), {"202", "400", "401", "403", "409", "413", "415", "422", "429", "500", "503"})
        self.assertEqual(set(operations[("get", "/v1/landing-jobs/{job_id}")]["responses"]), {"200", "401", "403", "404", "500"})
        self.assertEqual(set(operations[("post", "/v1/landing-jobs/{job_id}/cancel")]["responses"]), {"200", "401", "403", "404", "409", "500"})
        self.assertEqual(set(operations[("get", "/v1/landing-jobs/{job_id}/result")]["responses"]), {"200", "401", "403", "404", "409", "500", "503"})
        parameters = contract["components"]["parameters"]
        self.assertEqual(parameters["RepositoryId"]["schema"]["const"], "github.com/Dimkox/ai-dark-factory-landing")
        self.assertEqual(parameters["ExactBaseSha"]["schema"]["const"], "176efcaab931c2482781ff163c621b10aa05dee9")
        self.assertEqual(parameters["ExactBaseTree"]["schema"]["const"], "f2bdcecc6dbe9ecc82007610d398ca12bd75e07f")


if __name__ == "__main__":
    unittest.main()
