import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from tests.json_schema_subset import SubsetValidator


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "factory" / "src"))

from adaptive_factory.contracts import ContractError, canonical_digest  # noqa: E402
from adaptive_factory.result_contracts import (  # noqa: E402
    ResultEnvelopeV1,
    ResultEnvelopeV2,
    result_channel_qualification_from_wire,
    result_channel_qualification_wire,
    result_channel_qualification_v2_from_wire,
    result_channel_qualification_v2_wire,
)


def _dependency_free_validation_schema(schema):
    """Remove annotation-only keywords outside the strict executable subset."""
    if isinstance(schema, dict):
        return {
            key: _dependency_free_validation_schema(value)
            for key, value in schema.items()
            if key not in {"title", "description", "x-transport"}
        }
    if isinstance(schema, list):
        return [_dependency_free_validation_schema(value) for value in schema]
    return schema


def _qualification_v2_subset_schema(schema):
    """Retain executable subset rules and verify the unsupported allOf constraints."""
    normalized = _dependency_free_validation_schema(schema)
    channel_clauses = normalized.pop("allOf")
    expected_channels = set(normalized["items"]["properties"]["channel"]["enum"])
    assert len(channel_clauses) == len(expected_channels) == 7
    observed_channels = []
    for clause in channel_clauses:
        assert set(clause) == {"contains", "minContains", "maxContains"}
        assert clause["minContains"] == clause["maxContains"] == 1
        contains = clause["contains"]
        assert set(contains) == {"properties", "required"}
        assert contains["required"] == ["channel"]
        assert set(contains["properties"]) == {"channel"}
        channel = contains["properties"]["channel"]
        assert set(channel) == {"const"}
        observed_channels.append(channel["const"])
    assert len(set(observed_channels)) == len(observed_channels)
    assert set(observed_channels) == expected_channels
    item_clauses = normalized["items"].pop("allOf")
    assert item_clauses == [
        {
            "properties": {
                "status": {"const": "unavailable"},
                "interception_point": {"type": "null"},
            }
        }
    ]
    normalized["items"]["properties"].update(item_clauses[0]["properties"])
    return normalized


def test_result_schemas_are_structural_and_semantic_admission_is_mandatory():
    root = ROOT / "factory/contracts/jsonschema"
    envelope_schema = json.loads((root / "result-envelope.v1.schema.json").read_text())
    envelope_v2_schema = json.loads((root / "result-envelope.v2.schema.json").read_text())
    qualification_schema = json.loads((root / "result-channel-qualification.v1.schema.json").read_text())
    envelope_validator = SubsetValidator(_dependency_free_validation_schema(envelope_schema))
    envelope_v2_validator = SubsetValidator(_dependency_free_validation_schema(envelope_v2_schema))
    qualification_validator = SubsetValidator(_dependency_free_validation_schema(qualification_schema))
    for schema in (envelope_schema, envelope_v2_schema, qualification_schema):
        assert schema["x-admission"]["semantic_validation_required"] is True
    qualification_wire = result_channel_qualification_wire()
    qualification_validator.validate(qualification_wire)
    assert result_channel_qualification_from_wire(qualification_wire)
    value = {
        "schema_version": 1, "channel": "native_tool_result",
        "content_type": "text/plain", "outcome": "allow", "reason_code": "accepted",
        "completeness": "complete", "policy_version": "result-sanitizer/1",
        "sanitized_payload": "safe", "sanitized_payload_digest": canonical_digest("safe"),
    }
    envelope_validator.validate(value)
    assert ResultEnvelopeV1.from_dict(value).channel == "native_tool_result"
    value_v2 = {
        "repository_id": "owner/repository",
        "task_id": "11111111-1111-4111-8111-111111111111",
        "run_id": "22222222-2222-4222-8222-222222222222",
        "fence": 7, "packet_digest": "3" * 64,
        "attempt_id": "44444444-4444-4444-8444-444444444444",
        "source_operation": "tool.call/read", "source_digest": "5" * 64,
        **value, "schema_version": 2,
    }
    envelope_v2_validator.validate(value_v2)
    assert ResultEnvelopeV2.from_dict(value_v2).record_digest == canonical_digest(value_v2)
    assert not envelope_v2_validator.is_valid({**value_v2, "fence": True})
    with unittest.TestCase().assertRaisesRegex(ContractError, "invalid_integer"):
        ResultEnvelopeV2.from_dict({**value_v2, "fence": True})
    structurally_valid_but_forged = {**value, "sanitized_payload_digest": "0" * 64}
    envelope_validator.validate(structurally_valid_but_forged)
    with unittest.TestCase().assertRaisesRegex(ContractError, "sanitized_payload_digest_mismatch"):
        ResultEnvelopeV1.from_dict(structurally_valid_but_forged)

    duplicate = deepcopy(qualification_wire)
    duplicate[-1] = deepcopy(duplicate[0])
    assert not qualification_validator.is_valid(duplicate)
    with unittest.TestCase().assertRaisesRegex(ContractError, "qualification_channel_set"):
        result_channel_qualification_from_wire(duplicate)
    semantic_duplicate = deepcopy(qualification_wire)
    semantic_duplicate[-1] = {**semantic_duplicate[0], "limitation": "different_reason"}
    qualification_validator.validate(semantic_duplicate)
    with unittest.TestCase().assertRaisesRegex(ContractError, "qualification_channel_set"):
        result_channel_qualification_from_wire(semantic_duplicate)
    with unittest.TestCase().assertRaisesRegex(ContractError, "qualification_channel_set"):
        result_channel_qualification_from_wire(qualification_wire[:-1])
    falsely_qualified = deepcopy(qualification_wire)
    falsely_qualified[0]["status"] = "qualified"
    falsely_qualified[0]["interception_point"] = "fake.callback"
    assert not qualification_validator.is_valid(falsely_qualified)
    with unittest.TestCase().assertRaisesRegex(ContractError, "channel_not_qualified"):
        result_channel_qualification_from_wire(falsely_qualified)
    for row in (None, [], {"extra": True}):
        with unittest.TestCase().assertRaises(ContractError):
            result_channel_qualification_from_wire([row] + qualification_wire[1:])
    malformed = deepcopy(qualification_wire)
    malformed[0]["channel"] = []
    with unittest.TestCase().assertRaisesRegex(ContractError, "invalid_channel"):
        result_channel_qualification_from_wire(malformed)
    malformed[0] = {**qualification_wire[0], "limitation": "\ud800"}
    with unittest.TestCase().assertRaisesRegex(ContractError, "invalid_text"):
        result_channel_qualification_from_wire(malformed)

    qualification_v2_schema = json.loads(
        (root / "result-channel-qualification.v2.schema.json").read_text()
    )
    qualification_v2_validator = SubsetValidator(
        _qualification_v2_subset_schema(qualification_v2_schema)
    )
    handoff_schema = json.loads((root / "native-result-handoff.v1.schema.json").read_text())
    handoff_validation_schema = _dependency_free_validation_schema(handoff_schema)
    assert handoff_validation_schema["oneOf"][0]["properties"]["result_envelope"] == {
        "$ref": "result-envelope.v2.schema.json"
    }
    handoff_validation_schema["oneOf"][0]["properties"]["result_envelope"] = (
        _dependency_free_validation_schema(envelope_v2_schema)
    )
    SubsetValidator(handoff_validation_schema)
    assert handoff_schema["x-transport"] == {
        "scope": "internal-uds-only", "tcp": False, "dns": False,
        "proxy": False, "redirects": False, "provider_or_model_invocation": False,
    }
    qualification_v2 = result_channel_qualification_v2_wire()
    qualification_v2_validator.validate(qualification_v2)
    assert all(row.status == "unavailable" for row in result_channel_qualification_v2_from_wire(qualification_v2))
    forged_v2 = deepcopy(qualification_v2)
    forged_v2[0]["status"] = "qualified"
    forged_v2[0]["interception_point"] = "fake.callback"
    assert not qualification_v2_validator.is_valid(forged_v2)
    with unittest.TestCase().assertRaisesRegex(ContractError, "channel_not_qualified"):
        result_channel_qualification_v2_from_wire(forged_v2)
    for malformed in (
        qualification_v2[:-1],
        [*qualification_v2[:-1], {**qualification_v2[0], "limitation": "duplicate"}],
    ):
        assert (
            not qualification_v2_validator.is_valid(malformed)
            or {row["channel"] for row in malformed}
            != {row["channel"] for row in qualification_v2}
        )
        with unittest.TestCase().assertRaisesRegex(ContractError, "qualification_channel_set"):
            result_channel_qualification_v2_from_wire(malformed)

    def require_closed(schema):
        assert schema["additionalProperties"] is False

    require_closed(envelope_schema)
    require_closed(envelope_v2_schema)
    require_closed(qualification_schema["items"])
    weakened = deepcopy(envelope_schema)
    weakened["additionalProperties"] = True
    with unittest.TestCase().assertRaises(AssertionError):
        require_closed(weakened)
    weakened_qualification = deepcopy(qualification_schema)
    weakened_qualification["items"]["additionalProperties"] = True
    with unittest.TestCase().assertRaises(AssertionError):
        require_closed(weakened_qualification["items"])


def test_qualification_v2_subset_rejects_extra_allof_clause():
    schema = json.loads(
        (
            ROOT
            / "factory/contracts/jsonschema/result-channel-qualification.v2.schema.json"
        ).read_text()
    )
    schema["allOf"].append(deepcopy(schema["allOf"][0]))
    with unittest.TestCase().assertRaises(AssertionError):
        _qualification_v2_subset_schema(schema)


def load_tests(loader, tests, pattern):
    del loader, tests, pattern
    return unittest.TestSuite(
        [
            unittest.FunctionTestCase(
                test_result_schemas_are_structural_and_semantic_admission_is_mandatory
            ),
            unittest.FunctionTestCase(
                test_qualification_v2_subset_rejects_extra_allof_clause
            ),
        ]
    )
