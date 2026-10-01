import json
from copy import deepcopy
from pathlib import Path
import sys

from jsonschema import Draft202012Validator
import pytest


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "factory" / "src"))

from adaptive_factory.contracts import ContractError, canonical_digest  # noqa: E402
from adaptive_factory.result_contracts import (  # noqa: E402
    ResultEnvelopeV2,
    result_channel_qualification_from_wire,
    result_channel_qualification_wire,
    result_channel_qualification_v2_from_wire,
    result_channel_qualification_v2_wire,
)


def test_result_schemas_are_structural_and_semantic_admission_is_mandatory():
    root = ROOT / "factory/contracts/jsonschema"
    envelope_schema = json.loads((root / "result-envelope.v2.schema.json").read_text())
    qualification_schema = json.loads((root / "result-channel-qualification.v1.schema.json").read_text())
    Draft202012Validator.check_schema(envelope_schema)
    Draft202012Validator.check_schema(qualification_schema)
    qualification_wire = result_channel_qualification_wire()
    assert not list(Draft202012Validator(qualification_schema).iter_errors(qualification_wire))
    assert result_channel_qualification_from_wire(qualification_wire)
    value = {
        "repository_id": "owner/repository",
        "task_id": "11111111-1111-4111-8111-111111111111",
        "run_id": "22222222-2222-4222-8222-222222222222",
        "fence": 1,
        "packet_digest": "3" * 64,
        "attempt_id": "44444444-4444-4444-8444-444444444444",
        "source_operation": "tool.call/read",
        "source_digest": "5" * 64,
        "schema_version": 2, "channel": "native_tool_result",
        "content_type": "text/plain", "outcome": "allow", "reason_code": "accepted",
        "completeness": "complete", "policy_version": "result-sanitizer/1",
        "sanitized_payload": "safe", "sanitized_payload_digest": canonical_digest("safe"),
    }
    assert not list(Draft202012Validator(envelope_schema).iter_errors(value))
    assert ResultEnvelopeV2.from_dict(value).channel == "native_tool_result"
    structurally_valid_but_forged = {**value, "sanitized_payload_digest": "0" * 64}
    assert not list(Draft202012Validator(envelope_schema).iter_errors(structurally_valid_but_forged))
    with pytest.raises(ContractError, match="sanitized_payload_digest_mismatch"):
        ResultEnvelopeV2.from_dict(structurally_valid_but_forged)

    duplicate = deepcopy(qualification_wire)
    duplicate[-1] = deepcopy(duplicate[0])
    assert list(Draft202012Validator(qualification_schema).iter_errors(duplicate))
    with pytest.raises(ContractError, match="qualification_channel_set"):
        result_channel_qualification_from_wire(duplicate)
    semantic_duplicate = deepcopy(qualification_wire)
    semantic_duplicate[-1] = {**semantic_duplicate[0], "limitation": "different_reason"}
    assert not list(Draft202012Validator(qualification_schema).iter_errors(semantic_duplicate))
    with pytest.raises(ContractError, match="qualification_channel_set"):
        result_channel_qualification_from_wire(semantic_duplicate)
    with pytest.raises(ContractError, match="qualification_channel_set"):
        result_channel_qualification_from_wire(qualification_wire[:-1])
    falsely_qualified = deepcopy(qualification_wire)
    falsely_qualified[0]["status"] = "qualified"
    falsely_qualified[0]["interception_point"] = "fake.callback"
    assert list(Draft202012Validator(qualification_schema).iter_errors(falsely_qualified))
    with pytest.raises(ContractError, match="channel_not_qualified"):
        result_channel_qualification_from_wire(falsely_qualified)

    qualification_v2_schema = json.loads(
        (root / "result-channel-qualification.v2.schema.json").read_text()
    )
    Draft202012Validator.check_schema(qualification_v2_schema)
    qualification_v2 = result_channel_qualification_v2_wire()
    assert not list(Draft202012Validator(qualification_v2_schema).iter_errors(qualification_v2))
    assert result_channel_qualification_v2_from_wire(qualification_v2)[0].status == "qualified"
    assert all(row["status"] == "unavailable" for row in qualification_v2[1:])
    forged_v2 = deepcopy(qualification_v2)
    forged_v2[0]["interception_point"] = "fake.callback"
    assert list(Draft202012Validator(qualification_v2_schema).iter_errors(forged_v2))
    with pytest.raises(ContractError, match="unproved_interception_point"):
        result_channel_qualification_v2_from_wire(forged_v2)

    def require_closed(schema):
        assert schema["additionalProperties"] is False

    require_closed(envelope_schema)
    require_closed(qualification_schema["items"])
    weakened = deepcopy(envelope_schema)
    weakened["additionalProperties"] = True
    with pytest.raises(AssertionError):
        require_closed(weakened)
    weakened_qualification = deepcopy(qualification_schema)
    weakened_qualification["items"]["additionalProperties"] = True
    with pytest.raises(AssertionError):
        require_closed(weakened_qualification["items"])
