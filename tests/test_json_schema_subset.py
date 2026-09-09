from __future__ import annotations

import unittest

from tests.json_schema_subset import (
    SchemaDefinitionError,
    SchemaValidationError,
    SubsetValidator,
)


class JsonSchemaSubsetTests(unittest.TestCase):
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

    def test_unsupported_schema_keywords_fail_closed(self) -> None:
        validator = SubsetValidator({"type": "string", "format": "date-time"})

        with self.assertRaises(SchemaDefinitionError):
            validator.validate("2026-09-04T00:00:00Z")
        with self.assertRaises(SchemaDefinitionError):
            validator.is_valid("2026-09-04T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
