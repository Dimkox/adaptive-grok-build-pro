from __future__ import annotations

import unittest

from tests.json_schema_subset import (
    SchemaDefinitionError,
    SchemaValidationError,
    SubsetValidator,
)


class JsonSchemaSubsetTests(unittest.TestCase):
    def test_constructor_preflights_unreached_nested_schema_nodes(self) -> None:
        malformed_schemas = (
            {"anyOf": [{"type": "string"}, 7]},
            {"oneOf": [{"type": "string"}, {"unknown": True}]},
            {"$defs": {"unused": {"format": 7}}, "type": "null"},
            {"properties": {"unused": {"required": "name"}}},
            {"items": []},
            {"additionalProperties": 1},
            {"components": {"schemas": {"Unused": {"type": "number"}}}},
        )

        for schema in malformed_schemas:
            with self.subTest(schema=schema):
                with self.assertRaises(SchemaDefinitionError):
                    SubsetValidator(schema)

    def test_constructor_validates_annotation_and_keyword_operand_shapes(self) -> None:
        malformed_schemas = (
            {"$schema": 202012},
            {"$id": 7},
            {"$ref": None},
            {"format": 7},
            {"x-admission": ["structural"]},
            {"$defs": []},
            {"properties": []},
            {"type": []},
            {"required": ["name", "name"]},
            {"enum": []},
            {"pattern": "["},
            {"minLength": -1},
            {"minimum": True},
            {"uniqueItems": "yes"},
        )

        for schema in malformed_schemas:
            with self.subTest(schema=schema):
                with self.assertRaises(SchemaDefinitionError):
                    SubsetValidator(schema)

    def test_constructor_resolves_every_reference_and_rejects_cycles(self) -> None:
        malformed_schemas = (
            {"$defs": {"unused": {"$ref": "#/$defs/missing"}}},
            {
                "$defs": {
                    "value": {"type": "string"},
                    "unused": {"$ref": "#/$defs/value~2"},
                }
            },
            {"$defs": {"unused": {"$ref": "#/properties/value"}}},
            {"$defs": {"unused": {"$ref": "../schemas/external.json"}}},
            {
                "components": {
                    "schemas": {"Unused": {"$ref": "#/components/schemas/Missing"}}
                }
            },
            {"$defs": {"node": {"$ref": "#/$defs/node"}}},
            {
                "$defs": {
                    "left": {"$ref": "#/$defs/right"},
                    "right": {"$ref": "#/$defs/left"},
                }
            },
        )

        for schema in malformed_schemas:
            with self.subTest(schema=schema):
                with self.assertRaises(SchemaDefinitionError):
                    SubsetValidator(schema)

    def test_constructor_accepts_shared_repeated_acyclic_references(self) -> None:
        validator = SubsetValidator(
            {
                "$defs": {
                    "digest/value": {"type": "string", "pattern": "^[a-f]+$"},
                    "first": {"$ref": "#/$defs/digest~1value"},
                    "second": {"$ref": "#/$defs/digest~1value"},
                },
                "type": "object",
                "required": ["first", "second"],
                "properties": {
                    "first": {"$ref": "#/$defs/first"},
                    "second": {"$ref": "#/$defs/second"},
                },
            }
        )

        validator.validate({"first": "face", "second": "cafe"})

    def test_component_refs_closed_objects_and_exact_one_are_enforced(self) -> None:
        validator = SubsetValidator(
            {
                "$ref": "#/components/schemas/Envelope",
                "components": {
                    "schemas": {
                        "Envelope": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["kind", "value"],
                            "properties": {
                                "kind": {"enum": ["short", "empty"]},
                                "value": {"type": ["string", "null"]},
                            },
                            "oneOf": [
                                {
                                    "properties": {
                                        "kind": {"const": "short"},
                                        "value": {
                                            "type": "string",
                                            "minLength": 1,
                                            "maxLength": 3,
                                        },
                                    }
                                },
                                {
                                    "properties": {
                                        "kind": {"const": "empty"},
                                        "value": {"type": "null"},
                                    }
                                },
                            ],
                        }
                    }
                },
            }
        )

        validator.validate({"kind": "short", "value": "abc"})
        self.assertTrue(validator.is_valid({"kind": "empty", "value": None}))
        self.assertFalse(validator.is_valid({"kind": "short", "value": None}))
        self.assertFalse(validator.is_valid({"kind": "short", "value": "abcd"}))
        self.assertFalse(
            validator.is_valid({"kind": "short", "value": "abc", "extra": True})
        )
        with self.assertRaises(SchemaValidationError):
            validator.validate({"kind": "empty"})

        exact_one = SubsetValidator(
            {
                "oneOf": [
                    {"type": "integer", "minimum": 0},
                    {"type": "integer", "maximum": 10},
                ]
            }
        )
        self.assertFalse(exact_one.is_valid(5))
        self.assertTrue(exact_one.is_valid(11))

    def test_scalar_union_pattern_length_enum_const_and_bounds_are_enforced(self) -> None:
        validator = SubsetValidator(
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["mode", "digest", "count", "note"],
                "properties": {
                    "mode": {"const": "bounded"},
                    "digest": {
                        "type": "string",
                        "pattern": "^[0-9a-f]+$",
                        "minLength": 2,
                        "maxLength": 4,
                    },
                    "count": {"type": "integer", "minimum": 1, "maximum": 3},
                    "note": {"type": ["string", "null"]},
                    "role": {"enum": ["reader", "writer"]},
                },
            }
        )

        validator.validate(
            {"mode": "bounded", "digest": "0a", "count": 3, "note": None}
        )
        self.assertFalse(
            validator.is_valid(
                {"mode": "bounded", "digest": "0G", "count": 3, "note": None}
            )
        )
        self.assertFalse(
            validator.is_valid(
                {"mode": "bounded", "digest": "0a", "count": 4, "note": None}
            )
        )
        self.assertFalse(
            validator.is_valid(
                {"mode": "other", "digest": "0a", "count": 3, "note": None}
            )
        )

    def test_array_items_uniqueness_and_count_are_enforced(self) -> None:
        validator = SubsetValidator(
            {
                "type": "array",
                "items": {"type": "string", "pattern": "^[a-z]+$"},
                "uniqueItems": True,
                "minItems": 1,
                "maxItems": 2,
            }
        )

        validator.validate(["alpha", "beta"])
        self.assertFalse(validator.is_valid([]))
        self.assertFalse(validator.is_valid(["alpha", "alpha"]))
        self.assertFalse(validator.is_valid(["alpha", "beta", "gamma"]))
        self.assertFalse(validator.is_valid(["UPPER"]))

    def test_local_defs_any_of_and_annotations_are_supported(self) -> None:
        validator = SubsetValidator(
            {
                "$id": "urn:test:manifest:v1",
                "$defs": {
                    "digest/value": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{4}$",
                    }
                },
                "x-admission": {"level": "structural"},
                "type": "object",
                "required": ["digest", "observed_at", "optional_digest"],
                "properties": {
                    "digest": {"$ref": "#/$defs/digest~1value"},
                    "observed_at": {"type": "string", "format": "date-time"},
                    "optional_digest": {
                        "anyOf": [
                            {"$ref": "#/$defs/digest~1value"},
                            {"type": "null"},
                        ]
                    },
                },
            }
        )

        validator.validate(
            {
                "digest": "0a1b",
                "observed_at": "2026-10-01T12:00:00Z",
                "optional_digest": None,
            }
        )
        self.assertTrue(
            validator.is_valid(
                {
                    "digest": "cafe",
                    "observed_at": "not-format-validated",
                    "optional_digest": "beef",
                }
            )
        )
        self.assertFalse(
            validator.is_valid(
                {
                    "digest": "wrong",
                    "observed_at": "2026-10-01T12:00:00Z",
                    "optional_digest": 7,
                }
            )
        )

    def test_any_of_requires_at_least_one_matching_schema(self) -> None:
        validator = SubsetValidator(
            {"anyOf": [{"type": "string"}, {"type": "integer", "minimum": 1}]}
        )

        validator.validate("value")
        validator.validate(1)
        with self.assertRaises(SchemaValidationError):
            validator.validate(None)

    def test_local_defs_references_fail_closed_for_invalid_targets(self) -> None:
        for schema in (
            {"$defs": {}, "$ref": "#/$defs/missing"},
            {"$defs": {"value": {"type": "string"}}, "$ref": "#/$defs/"},
            {"$defs": {"value": {"type": "string"}}, "$ref": "#/$defs/value/child"},
            {"$defs": {"value": {"type": "string"}}, "$ref": "#/$defs/value~2"},
            {"$defs": {"value": {"$ref": "#/$defs/value"}}, "$ref": "#/$defs/value"},
        ):
            with self.subTest(schema=schema):
                with self.assertRaises(SchemaDefinitionError):
                    SubsetValidator(schema).validate("value")

    def test_unknown_schema_keywords_still_fail_closed(self) -> None:
        with self.assertRaises(SchemaDefinitionError):
            SubsetValidator({"type": "string", "minProperties": 1})
        with self.assertRaises(SchemaDefinitionError):
            SubsetValidator(
                {
                    "type": "object",
                    "properties": {"nested": {"minProperties": 1}},
                }
            )


if __name__ == "__main__":
    unittest.main()
