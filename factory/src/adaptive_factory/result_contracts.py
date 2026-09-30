"""Pre-model result boundary for the explicitly intercepted native profile.

Opaque external CLI internal model requests are unavailable, never silently protected.
"""

import math
import re
from .brokers import BrokerError
from .contracts import ContractError, canonical_json
from .v15_contracts import FrozenWire, closed, version, identity, digest, sha, sequence, safe_text, integer, redact


CHANNELS = ("structured", "stdout", "stderr", "error", "stream", "attachment", "cache", "resume")
MAX_RESULT_BYTES = 65536
_SECRET_KEY = re.compile(r"(?i)(?:password|credential|secret|token|api.?key|private.?key|authorization)")


def _sanitize(value, *, depth=0, budget=None):
    if budget is None:
        budget = [512]
    budget[0] -= 1
    if depth > 8 or budget[0] < 0:
        raise ContractError("result_structure_limit")
    if isinstance(value, str):
        return redact(value, MAX_RESULT_BYTES)
    if value is None or type(value) in (int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if isinstance(value, list):
        return [_sanitize(item, depth=depth + 1, budget=budget) for item in value]
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            if not isinstance(key, str) or len(key.encode()) > 128:
                raise ContractError("invalid_result_key")
            cleaned_key = redact(key, 128)
            if cleaned_key != key:
                raise ContractError("unsafe_result_key")
            clean[key] = "[REDACTED]" if _SECRET_KEY.search(key) else _sanitize(item, depth=depth + 1, budget=budget)
        return clean
    raise ContractError("unsupported_result_type")


class ToolResultEnvelopeV1(FrozenWire):
    @classmethod
    def from_result(
        cls, payload, *, channel, profile, before_model, media_type="text/plain", max_bytes=MAX_RESULT_BYTES
    ):
        identity(profile)
        integer(max_bytes, "max_bytes", 1, MAX_RESULT_BYTES)
        if channel not in CHANNELS:
            raise ContractError("unsupported_channel")
        if type(before_model) is not bool:
            raise ContractError("invalid_interception_flag")
        result = dict(
            schema_version=1,
            profile=profile,
            channel=channel,
            outcome="unavailable",
            reason_code="interception_unavailable",
            completeness="missing",
            payload=None,
        )
        if not before_model:
            return cls.freeze(result)
        try:
            if media_type not in ("text/plain", "application/json"):
                raise ContractError("unsupported_media")
            if channel == "stream":
                sequence(payload, 1024)
                if any(not isinstance(chunk, str) for chunk in payload):
                    raise ContractError("invalid_stream")
                # Bound the complete record before concatenation; never release unvalidated chunks.
                if sum(len(chunk.encode()) for chunk in payload) > max_bytes:
                    raise ContractError("result_too_large")
                payload = "".join(payload)
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="strict")
            if channel != "structured" and not isinstance(payload, str):
                raise ContractError("invalid_text_result")
            if len(canonical_json(payload)) > max_bytes:
                raise ContractError("result_too_large")
            clean = _sanitize(payload)
            if len(canonical_json(clean)) > max_bytes:
                raise ContractError("result_too_large")
            redacted = clean != payload
            result.update(
                outcome="redacted" if redacted else "allow",
                reason_code="known_secret_removed" if redacted else "validated",
                completeness="partial" if redacted else "full",
                payload=clean,
            )
        except (ContractError, BrokerError, UnicodeError, ValueError, TypeError, RecursionError):
            result.update(outcome="rejected", reason_code="invalid_or_unsafe_result")
        return cls.freeze(result)

    @classmethod
    def from_dict(cls, data):
        closed(data, ("schema_version", "profile", "channel", "outcome", "reason_code", "completeness", "payload"))
        version(data)
        identity(data["profile"])
        identity(data["reason_code"])
        if data["channel"] not in CHANNELS:
            raise ContractError("unsupported_channel")
        if data["outcome"] in ("unavailable", "rejected"):
            if data["payload"] is not None or data["completeness"] != "missing":
                raise ContractError("unsafe_rejected_payload")
        elif data["outcome"] in ("allow", "redacted"):
            expected = "full" if data["outcome"] == "allow" else "partial"
            if data["completeness"] != expected or _sanitize(data["payload"]) != data["payload"]:
                raise ContractError("unsafe_envelope")
        else:
            raise ContractError("invalid_result_outcome")
        if len(canonical_json(data)) > MAX_RESULT_BYTES + 1024:
            raise ContractError("result_too_large")
        return cls.freeze(data)


def reuse_tool_result(payload, *, model, sinks=(), **profile):
    envelope = ToolResultEnvelopeV1.from_result(payload, **profile)
    safe = envelope.to_dict()
    for sink in sinks:
        sink(envelope.to_dict())
    if safe["outcome"] not in ("allow", "redacted"):
        return envelope, None
    # Data remains an explicitly labelled untrusted envelope, never an instruction/grant.
    return envelope, model(envelope.to_dict())


class SemanticExecutionEvidenceV2(FrozenWire):
    @classmethod
    def from_dict(cls, data):
        closed(
            data,
            (
                "schema_version",
                "repository_id",
                "task_id",
                "candidate_sha",
                "context_digest",
                "criterion_id",
                "rule_id",
                "rule_revision",
                "command",
                "selector",
                "result",
                "tool_result_digest",
                "report_digest",
            ),
        )
        version(data, 2)
        for key in ("repository_id", "task_id", "criterion_id", "rule_id", "rule_revision", "selector"):
            identity(data[key])
        sha(data["candidate_sha"])
        for key in ("context_digest", "tool_result_digest", "report_digest"):
            digest(data[key])
        if data["result"] not in ("pass", "fail", "blocked", "not_evaluated"):
            raise ContractError("invalid_semantic_result")
        command = sequence(data["command"], 32)
        if not command:
            raise ContractError("missing_command")
        for arg in command:
            safe_text(arg, "command", 512)
        return cls.freeze(data)

    def bind_result(self, envelope):
        envelope = ToolResultEnvelopeV1.from_dict(envelope.to_dict())
        if self.to_dict()["tool_result_digest"] != envelope.record_digest:
            raise ContractError("result_binding_mismatch")
        if self.to_dict()["result"] == "pass" and envelope.to_dict()["outcome"] != "allow":
            raise ContractError("incomplete_semantic_evidence")
