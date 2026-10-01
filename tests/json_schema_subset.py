from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any


class SchemaDefinitionError(ValueError):
    """The test schema uses syntax outside the supported strict subset."""


class SchemaValidationError(ValueError):
    """The instance does not satisfy the supplied schema."""


class SubsetValidator:
    """Dependency-free validator for the JSON Schema subset used by structure tests."""

    _SUPPORTED_KEYWORDS = frozenset(
        {
            "$schema",
            "$id",
            "$defs",
            "$ref",
            "components",
            "format",
            "x-admission",
            "type",
            "required",
            "properties",
            "additionalProperties",
            "anyOf",
            "oneOf",
            "enum",
            "const",
            "pattern",
            "minLength",
            "maxLength",
            "items",
            "uniqueItems",
            "minItems",
            "maxItems",
            "minimum",
            "maximum",
        }
    )
    _SUPPORTED_TYPES = frozenset(
        {"array", "boolean", "integer", "null", "object", "string"}
    )

    def __init__(self, schema: Mapping[str, Any] | bool) -> None:
        if not isinstance(schema, (Mapping, bool)):
            raise SchemaDefinitionError("root schema must be an object or boolean")
        self._root = schema
        self._preflight_schema(schema, "$", set())

    def _preflight_schema(
        self,
        schema: Mapping[str, Any] | bool,
        path: str,
        active_nodes: set[int],
    ) -> None:
        if isinstance(schema, bool):
            return
        if not isinstance(schema, Mapping):
            raise SchemaDefinitionError(f"{path}: schema must be an object or boolean")
        node_id = id(schema)
        if node_id in active_nodes:
            raise SchemaDefinitionError(f"{path}: cyclic in-memory schema object")
        active_nodes.add(node_id)
        try:
            unsupported = set(schema) - self._SUPPORTED_KEYWORDS
            if unsupported:
                names = ", ".join(sorted(unsupported))
                raise SchemaDefinitionError(
                    f"{path}: unsupported schema keyword(s): {names}"
                )

            for keyword in ("$schema", "$id", "$ref", "format"):
                if keyword in schema and not isinstance(schema[keyword], str):
                    raise SchemaDefinitionError(f"{path}: {keyword} must be a string")

            if "$ref" in schema:
                reference = schema["$ref"]
                target = self._resolve_reference(reference)
                self._preflight_schema(
                    target, f"{path}.$ref({reference})", active_nodes
                )

            if "x-admission" in schema:
                annotation = schema["x-admission"]
                if not isinstance(annotation, Mapping):
                    raise SchemaDefinitionError(
                        f"{path}: x-admission must be an object annotation"
                    )
                self._preflight_json_value(annotation, f"{path}.x-admission", set())

            for keyword in ("$defs", "properties"):
                if keyword not in schema:
                    continue
                children = schema[keyword]
                if not isinstance(children, Mapping):
                    raise SchemaDefinitionError(f"{path}: {keyword} must be an object")
                for name, child in children.items():
                    if not isinstance(name, str):
                        raise SchemaDefinitionError(
                            f"{path}: {keyword} names must be strings"
                        )
                    self._preflight_schema(
                        child, f"{path}.{keyword}.{name}", active_nodes
                    )

            if "components" in schema:
                components = schema["components"]
                if not isinstance(components, Mapping):
                    raise SchemaDefinitionError(f"{path}: components must be an object")
                schemas = components.get("schemas")
                if schemas is not None:
                    if not isinstance(schemas, Mapping):
                        raise SchemaDefinitionError(
                            f"{path}: components/schemas must be an object"
                        )
                    for name, child in schemas.items():
                        if not isinstance(name, str):
                            raise SchemaDefinitionError(
                                f"{path}: component schema names must be strings"
                            )
                        self._preflight_schema(
                            child, f"{path}.components.schemas.{name}", active_nodes
                        )

            for keyword in ("anyOf", "oneOf"):
                if keyword not in schema:
                    continue
                variants = schema[keyword]
                if not isinstance(variants, list) or not variants:
                    raise SchemaDefinitionError(
                        f"{path}: {keyword} must be a non-empty array"
                    )
                for index, variant in enumerate(variants):
                    self._preflight_schema(
                        variant, f"{path}.{keyword}[{index}]", active_nodes
                    )

            if "items" in schema:
                self._preflight_schema(schema["items"], f"{path}.items", active_nodes)

            if "additionalProperties" in schema:
                additional = schema["additionalProperties"]
                if not isinstance(additional, (Mapping, bool)):
                    raise SchemaDefinitionError(
                        f"{path}: additionalProperties must be boolean or a schema"
                    )
                self._preflight_schema(
                    additional, f"{path}.additionalProperties", active_nodes
                )

            if "type" in schema:
                expected = schema["type"]
                if isinstance(expected, str):
                    expected_types = (expected,)
                elif (
                    isinstance(expected, Sequence)
                    and not isinstance(expected, (str, bytes))
                    and expected
                    and all(isinstance(item, str) for item in expected)
                ):
                    expected_types = tuple(expected)
                else:
                    raise SchemaDefinitionError(
                        f"{path}: type must be a string or non-empty string array"
                    )
                unsupported_types = set(expected_types) - self._SUPPORTED_TYPES
                if unsupported_types:
                    names = ", ".join(sorted(unsupported_types))
                    raise SchemaDefinitionError(
                        f"{path}: unsupported JSON type(s): {names}"
                    )

            if "required" in schema:
                required = schema["required"]
                if (
                    not isinstance(required, list)
                    or not all(isinstance(name, str) for name in required)
                    or len(set(required)) != len(required)
                ):
                    raise SchemaDefinitionError(
                        f"{path}: required must be a unique string array"
                    )

            if "enum" in schema:
                choices = schema["enum"]
                if not isinstance(choices, list) or not choices:
                    raise SchemaDefinitionError(f"{path}: enum must be a non-empty array")
                self._preflight_json_value(choices, f"{path}.enum", set())
            if "const" in schema:
                self._preflight_json_value(schema["const"], f"{path}.const", set())

            if "pattern" in schema:
                pattern = schema["pattern"]
                if not isinstance(pattern, str):
                    raise SchemaDefinitionError(f"{path}: pattern must be a string")
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise SchemaDefinitionError(
                        f"{path}: invalid pattern: {exc}"
                    ) from exc

            for keyword in ("minLength", "maxLength", "minItems", "maxItems"):
                self._nonnegative_integer_keyword(schema, keyword, path)

            if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
                raise SchemaDefinitionError(f"{path}: uniqueItems must be boolean")

            for keyword in ("minimum", "maximum"):
                if keyword in schema and (
                    not isinstance(schema[keyword], (int, float))
                    or isinstance(schema[keyword], bool)
                    or not math.isfinite(schema[keyword])
                ):
                    raise SchemaDefinitionError(f"{path}: {keyword} must be numeric")
        finally:
            active_nodes.remove(node_id)

    def _preflight_json_value(
        self, value: Any, path: str, active_nodes: set[int]
    ) -> None:
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            if math.isfinite(value):
                return
            raise SchemaDefinitionError(f"{path}: non-finite number is not JSON-safe")
        if isinstance(value, (list, Mapping)):
            node_id = id(value)
            if node_id in active_nodes:
                raise SchemaDefinitionError(f"{path}: cyclic value is not JSON-safe")
            active_nodes.add(node_id)
            try:
                if isinstance(value, list):
                    for index, item in enumerate(value):
                        self._preflight_json_value(
                            item, f"{path}[{index}]", active_nodes
                        )
                else:
                    for name, item in value.items():
                        if not isinstance(name, str):
                            raise SchemaDefinitionError(
                                f"{path}: JSON object keys must be strings"
                            )
                        self._preflight_json_value(
                            item, f"{path}.{name}", active_nodes
                        )
            finally:
                active_nodes.remove(node_id)
            return
        raise SchemaDefinitionError(f"{path}: value is not JSON-safe")

    def validate(self, instance: Any) -> None:
        self._validate(instance, self._root, "$", frozenset())

    def is_valid(self, instance: Any) -> bool:
        try:
            self.validate(instance)
        except SchemaValidationError:
            return False
        return True

    def _validate(
        self,
        instance: Any,
        schema: Mapping[str, Any] | bool,
        path: str,
        reference_stack: frozenset[str],
    ) -> None:
        if schema is True:
            return
        if schema is False:
            raise SchemaValidationError(f"{path}: rejected by false schema")
        if not isinstance(schema, Mapping):
            raise SchemaDefinitionError(f"{path}: schema must be an object or boolean")

        unsupported = set(schema) - self._SUPPORTED_KEYWORDS
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise SchemaDefinitionError(f"{path}: unsupported schema keyword(s): {names}")

        reference = schema.get("$ref")
        if reference is not None:
            if not isinstance(reference, str):
                raise SchemaDefinitionError(f"{path}: $ref must be a string")
            if reference in reference_stack:
                raise SchemaDefinitionError(f"{path}: cyclic $ref {reference!r}")
            self._validate(
                instance,
                self._resolve_reference(reference),
                path,
                reference_stack | {reference},
            )

        variants = schema.get("anyOf")
        if variants is not None:
            if not isinstance(variants, list) or not variants:
                raise SchemaDefinitionError(f"{path}: anyOf must be a non-empty array")
            for variant in variants:
                try:
                    self._validate(instance, variant, path, reference_stack)
                except SchemaValidationError:
                    continue
                break
            else:
                raise SchemaValidationError(f"{path}: anyOf did not match any schema")

        if "type" in schema:
            expected = schema["type"]
            if isinstance(expected, str):
                expected_types = (expected,)
            elif (
                isinstance(expected, Sequence)
                and not isinstance(expected, (str, bytes))
                and expected
                and all(isinstance(item, str) for item in expected)
            ):
                expected_types = tuple(expected)
            else:
                raise SchemaDefinitionError(f"{path}: type must be a string or non-empty string array")
            unsupported_types = set(expected_types) - self._SUPPORTED_TYPES
            if unsupported_types:
                names = ", ".join(sorted(unsupported_types))
                raise SchemaDefinitionError(f"{path}: unsupported JSON type(s): {names}")
            if not any(self._matches_type(instance, name) for name in expected_types):
                raise SchemaValidationError(
                    f"{path}: expected type {' or '.join(expected_types)}"
                )

        if "enum" in schema:
            choices = schema["enum"]
            if not isinstance(choices, list) or not choices:
                raise SchemaDefinitionError(f"{path}: enum must be a non-empty array")
            if not any(self._json_equal(instance, choice) for choice in choices):
                raise SchemaValidationError(f"{path}: value is not in enum")

        if "const" in schema and not self._json_equal(instance, schema["const"]):
            raise SchemaValidationError(f"{path}: value does not match const")

        variants = schema.get("oneOf")
        if variants is not None:
            if not isinstance(variants, list) or not variants:
                raise SchemaDefinitionError(f"{path}: oneOf must be a non-empty array")
            matches = 0
            for variant in variants:
                try:
                    self._validate(instance, variant, path, reference_stack)
                except SchemaValidationError:
                    continue
                matches += 1
            if matches != 1:
                raise SchemaValidationError(
                    f"{path}: oneOf matched {matches} schemas instead of exactly one"
                )

        if isinstance(instance, str):
            self._validate_string(instance, schema, path)
        if isinstance(instance, list):
            self._validate_array(instance, schema, path, reference_stack)
        if isinstance(instance, dict):
            self._validate_object(instance, schema, path, reference_stack)
        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            self._validate_number(instance, schema, path)

    def _resolve_reference(self, reference: str) -> Mapping[str, Any] | bool:
        for prefix, container_path, label in (
            ("#/components/schemas/", ("components", "schemas"), "OpenAPI component schema"),
            ("#/$defs/", ("$defs",), "local definition"),
        ):
            if reference.startswith(prefix):
                return self._resolve_root_container_reference(
                    reference, prefix, container_path, label
                )
        raise SchemaDefinitionError(
            "unsupported reference; expected one local $defs or OpenAPI component "
            f"schema: {reference!r}"
        )

    def _resolve_root_container_reference(
        self,
        reference: str,
        prefix: str,
        container_path: tuple[str, ...],
        label: str,
    ) -> Mapping[str, Any] | bool:
        encoded_name = reference.removeprefix(prefix)
        if (
            not encoded_name
            or "/" in encoded_name
            or re.search(r"~(?:[^01]|$)", encoded_name)
        ):
            raise SchemaDefinitionError(
                f"unsupported reference; expected one {label}: {reference!r}"
            )
        name = encoded_name.replace("~1", "/").replace("~0", "~")
        if not isinstance(self._root, Mapping):
            raise SchemaDefinitionError("boolean root schema cannot resolve references")
        container: Any = self._root
        for segment in container_path:
            if not isinstance(container, Mapping) or segment not in container:
                raise SchemaDefinitionError(
                    f"root schema has no {'/'.join(container_path)} object"
                )
            container = container[segment]
        if not isinstance(container, Mapping) or name not in container:
            raise SchemaDefinitionError(f"unknown {label}: {name!r}")
        target = container[name]
        if not isinstance(target, (Mapping, bool)):
            raise SchemaDefinitionError(f"{label} {name!r} is not an object or boolean")
        return target

    def _validate_string(
        self, instance: str, schema: Mapping[str, Any], path: str
    ) -> None:
        minimum = self._nonnegative_integer_keyword(schema, "minLength", path)
        maximum = self._nonnegative_integer_keyword(schema, "maxLength", path)
        if minimum is not None and len(instance) < minimum:
            raise SchemaValidationError(f"{path}: string is shorter than minLength")
        if maximum is not None and len(instance) > maximum:
            raise SchemaValidationError(f"{path}: string is longer than maxLength")
        pattern = schema.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                raise SchemaDefinitionError(f"{path}: pattern must be a string")
            try:
                matched = re.search(pattern, instance)
            except re.error as exc:
                raise SchemaDefinitionError(f"{path}: invalid pattern: {exc}") from exc
            if matched is None:
                raise SchemaValidationError(f"{path}: string does not match pattern")

    def _validate_array(
        self,
        instance: list[Any],
        schema: Mapping[str, Any],
        path: str,
        reference_stack: frozenset[str],
    ) -> None:
        minimum = self._nonnegative_integer_keyword(schema, "minItems", path)
        maximum = self._nonnegative_integer_keyword(schema, "maxItems", path)
        if minimum is not None and len(instance) < minimum:
            raise SchemaValidationError(f"{path}: array has fewer than minItems")
        if maximum is not None and len(instance) > maximum:
            raise SchemaValidationError(f"{path}: array has more than maxItems")
        unique = schema.get("uniqueItems", False)
        if not isinstance(unique, bool):
            raise SchemaDefinitionError(f"{path}: uniqueItems must be boolean")
        if unique and any(
            self._json_equal(instance[left], instance[right])
            for left in range(len(instance))
            for right in range(left + 1, len(instance))
        ):
            raise SchemaValidationError(f"{path}: array items are not unique")
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, (Mapping, bool)):
                raise SchemaDefinitionError(f"{path}: items must be an object or boolean")
            for index, item in enumerate(instance):
                self._validate(item, item_schema, f"{path}[{index}]", reference_stack)

    def _validate_object(
        self,
        instance: dict[str, Any],
        schema: Mapping[str, Any],
        path: str,
        reference_stack: frozenset[str],
    ) -> None:
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            raise SchemaDefinitionError(f"{path}: properties must be an object")
        required = schema.get("required", [])
        if (
            not isinstance(required, list)
            or not all(isinstance(name, str) for name in required)
            or len(set(required)) != len(required)
        ):
            raise SchemaDefinitionError(f"{path}: required must be a unique string array")
        missing = set(required) - set(instance)
        if missing:
            names = ", ".join(sorted(missing))
            raise SchemaValidationError(f"{path}: missing required properties: {names}")
        for name, property_schema in properties.items():
            if not isinstance(name, str) or not isinstance(property_schema, (Mapping, bool)):
                raise SchemaDefinitionError(f"{path}: property schemas must be keyed objects")
            if name in instance:
                self._validate(
                    instance[name], property_schema, f"{path}.{name}", reference_stack
                )

        additional = schema.get("additionalProperties", True)
        extras = set(instance) - set(properties)
        if additional is False and extras:
            names = ", ".join(sorted(extras))
            raise SchemaValidationError(f"{path}: additional properties: {names}")
        if isinstance(additional, Mapping):
            for name in extras:
                self._validate(
                    instance[name], additional, f"{path}.{name}", reference_stack
                )
        elif not isinstance(additional, bool):
            raise SchemaDefinitionError(
                f"{path}: additionalProperties must be boolean or a schema"
            )

    @staticmethod
    def _validate_number(
        instance: int | float, schema: Mapping[str, Any], path: str
    ) -> None:
        for keyword, relation in (("minimum", "below"), ("maximum", "above")):
            if keyword not in schema:
                continue
            boundary = schema[keyword]
            if not isinstance(boundary, (int, float)) or isinstance(boundary, bool):
                raise SchemaDefinitionError(f"{path}: {keyword} must be numeric")
            if keyword == "minimum" and instance < boundary:
                raise SchemaValidationError(f"{path}: number is {relation} {keyword}")
            if keyword == "maximum" and instance > boundary:
                raise SchemaValidationError(f"{path}: number is {relation} {keyword}")

    @staticmethod
    def _nonnegative_integer_keyword(
        schema: Mapping[str, Any], keyword: str, path: str
    ) -> int | None:
        if keyword not in schema:
            return None
        value = schema[keyword]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise SchemaDefinitionError(f"{path}: {keyword} must be a non-negative integer")
        return value

    @staticmethod
    def _matches_type(instance: Any, expected: str) -> bool:
        if expected == "null":
            return instance is None
        if expected == "boolean":
            return isinstance(instance, bool)
        if expected == "integer":
            return isinstance(instance, int) and not isinstance(instance, bool)
        if expected == "string":
            return isinstance(instance, str)
        if expected == "array":
            return isinstance(instance, list)
        if expected == "object":
            return isinstance(instance, dict)
        raise SchemaDefinitionError(f"unsupported JSON type: {expected}")

    @classmethod
    def _json_equal(cls, left: Any, right: Any) -> bool:
        if isinstance(left, bool) or isinstance(right, bool):
            return isinstance(left, bool) and isinstance(right, bool) and left == right
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left == right
        if isinstance(left, list) and isinstance(right, list):
            return len(left) == len(right) and all(
                cls._json_equal(a, b) for a, b in zip(left, right)
            )
        if isinstance(left, dict) and isinstance(right, dict):
            return set(left) == set(right) and all(
                cls._json_equal(left[key], right[key]) for key in left
            )
        return type(left) is type(right) and left == right
