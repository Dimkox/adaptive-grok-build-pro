"""Schema parity for M8; contains no factual cohort or acceptance evidence."""

from dataclasses import fields
import json
from pathlib import Path
import unittest

from adaptive_factory.autonomy import (
    AutonomyProfileV1,
    AutonomyTupleV1,
    CohortEvidenceV1,
    CohortTaskEvidenceV1,
    DemotionDecisionV1,
    PromotionRecommendationV1,
)
from adaptive_factory.m7_autonomy_bridge import M7ProviderMappingV1
from factory.tests.test_autonomy import valid_cohort_payload, valid_handoff_payload


FACTORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = FACTORY_ROOT / "contracts" / "jsonschema"
M8_SCHEMA_NAME = "earned-autonomy.v1.schema.json"
M7_BRIDGE_SCHEMA_NAME = "m7-autonomy-bridge.v1.schema.json"


def object_nodes(value: object):
    if isinstance(value, dict):
        if value.get("type") == "object":
            yield value
        for nested in value.values():
            yield from object_nodes(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from object_nodes(nested)


class AutonomySchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((SCHEMA_ROOT / M8_SCHEMA_NAME).read_text(encoding="utf-8"))
        self.bridge_schema = json.loads(
            (SCHEMA_ROOT / M7_BRIDGE_SCHEMA_NAME).read_text(encoding="utf-8")
        )

    def test_m8_schema_inventory_and_dialect_are_exact(self):
        actual = {
            path.name
            for path in SCHEMA_ROOT.glob("*.json")
            if json.loads(path.read_text(encoding="utf-8")).get("$id", "").startswith(
                "urn:adaptive-factory:m8:"
            )
        }
        duplicate_root = FACTORY_ROOT / "contracts" / "schemas"
        duplicate_names = set() if not duplicate_root.exists() else {
            path.name for path in duplicate_root.glob("*autonomy*.json")
        }
        self.assertEqual(actual, {M8_SCHEMA_NAME, M7_BRIDGE_SCHEMA_NAME})
        self.assertEqual(duplicate_names, set())
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(self.schema["$id"], "urn:adaptive-factory:m8:earned-autonomy:v1")

    def test_every_object_shape_is_closed_complete_and_versioned(self):
        for schema_name, schema in (
            (M8_SCHEMA_NAME, self.schema),
            (M7_BRIDGE_SCHEMA_NAME, self.bridge_schema),
        ):
            for index, node in enumerate(object_nodes(schema)):
                with self.subTest(schema=schema_name, object=index):
                    self.assertIs(node.get("additionalProperties"), False)
                    self.assertEqual(
                        set(node.get("required", [])), set(node.get("properties", {}))
                    )
                    if "schema_version" in node.get("properties", {}):
                        self.assertEqual(node["properties"]["schema_version"], {"const": 1})

    def test_schema_fields_match_all_six_python_records(self):
        parity = (
            ("autonomy_tuple", AutonomyTupleV1),
            ("cohort_task_evidence", CohortTaskEvidenceV1),
            ("cohort_evidence", CohortEvidenceV1),
            ("autonomy_profile", AutonomyProfileV1),
            ("promotion_recommendation", PromotionRecommendationV1),
            ("demotion_decision", DemotionDecisionV1),
        )
        for definition, contract in parity:
            with self.subTest(definition=definition):
                self.assertEqual(
                    set(self.schema["$defs"][definition]["properties"]),
                    {field.name for field in fields(contract)},
                )

        self.assertEqual(
            set(self.bridge_schema["$defs"]["provider_mapping"]["properties"]),
            {field.name for field in fields(M7ProviderMappingV1)},
        )

    def test_synthetic_closed_values_have_exact_root_schema_shapes(self):
        self.assertEqual(
            set(valid_handoff_payload()),
            set(self.bridge_schema["$defs"]["handoff"]["properties"]),
        )
        self.assertEqual(
            set(valid_cohort_payload()),
            set(self.schema["$defs"]["cohort_evidence"]["properties"]),
        )
        self.assertEqual(
            self.schema["$defs"]["cohort_evidence"]["properties"]["m7_handoff"],
            {"$ref": f'{self.bridge_schema["$id"]}#/$defs/handoff'},
        )

    def test_schema_freezes_authority_limits_and_has_no_effect_surface(self):
        definitions = self.schema["$defs"]
        tuple_properties = definitions["autonomy_tuple"]["properties"]
        recommendation = definitions["promotion_recommendation"]["properties"]
        demotion = definitions["demotion_decision"]["properties"]
        self.assertEqual(tuple_properties["task_class"], {"const": "low_risk_text_only"})
        self.assertEqual(tuple_properties["authority_ceiling"], {"const": "L2"})
        self.assertEqual(recommendation["external_action_authorized"], {"const": False})
        self.assertEqual(recommendation["separate_activation_required"], {"const": True})
        self.assertEqual(demotion["resulting_level"], {"const": "L0"})
        self.assertEqual(demotion["halt"], {"const": True})
        self.assertEqual(demotion["external_action_authorized"], {"const": False})

        forbidden = {
            "auto_merge",
            "command",
            "credential",
            "deploy",
            "merge",
            "network",
            "pull_request",
            "push",
            "remote_target",
            "token",
            "url",
        }
        for node in object_nodes(self.schema):
            self.assertTrue(forbidden.isdisjoint(node.get("properties", {})))

        wire_properties = {
            field
            for node in object_nodes(self.bridge_schema)
            for field in node.get("properties", {})
        }
        self.assertTrue(
            {"acceptance_status", "currentness_status", "factual_m7_restack_observed"}.isdisjoint(
                wire_properties
            )
        )
        self.assertNotIn("aggregate", wire_properties)
        self.assertNotIn("evaluation", wire_properties)


if __name__ == "__main__":
    unittest.main()
