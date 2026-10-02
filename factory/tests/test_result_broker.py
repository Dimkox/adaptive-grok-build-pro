import json
import unittest
from unittest.mock import patch

from adaptive_factory.contracts import ContractError


def broker(**limits):
    from adaptive_factory.result_broker import ResultBroker

    return ResultBroker(policy_version="result-sanitizer/1", **limits)


class ResultBrokerTests(unittest.TestCase):
    def test_structured_sensitive_keys_do_not_export_values(self):
        for key in ("Authorization", "X-Authorization", "password", "api_key",
                    "client-secret", "refresh_token", "private_key", "credentials"):
            with self.subTest(key=key):
                payload = json.dumps({"nested": [{key: {"value": "structured-canary"}}]}).encode()
                envelope = broker().sanitize_candidate(
                    channel="native_tool_result", content_type="application/json", chunks=[payload],
                )
                self.assertEqual(envelope.outcome, "redacted")
                self.assertNotIn("structured-canary", json.dumps(envelope.to_dict()))

    def test_duplicate_json_keys_are_rejected_before_last_value_wins(self):
        for payload in (b'{"a":1,"a":2}', b'{"nested":{"a":1,"a":2}}',
                        b'{"a":1,"\\u0061":2}'):
            with self.subTest(payload=payload):
                value = broker().sanitize_candidate(
                    channel="native_tool_result", content_type="application/json", chunks=[payload],
                )
                self.assertEqual((value.outcome, value.reason_code),
                                 ("rejected", "duplicate_json_key"))
                self.assertIsNone(value.sanitized_payload)

    def test_policy_limits_and_metadata_reject_invalid_configuration(self):
        from adaptive_factory.result_broker import ResultBroker

        for limit in ("max_bytes", "max_records", "max_depth", "max_chunks"):
            for value in (True, False, 1.5, float("nan"), float("inf"), 0, -1, 2**63):
                with self.subTest(limit=limit, value=value), self.assertRaises(ValueError):
                    broker(**{limit: value})
        for version in (None, 1, [], "", "x" * 129, "bad\x00policy",
                        "pass" + "word=policy-canary", "e\u0301"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                ResultBroker(policy_version=version)

    def test_empty_chunks_have_a_finite_iteration_ceiling(self):
        consumed = []

        def chunks():
            for index in range(6):
                consumed.append(index)
                yield b""
            raise AssertionError("stream must stop before this sentinel")

        value = broker(max_chunks=4).sanitize_candidate(
            channel="native_tool_result", content_type="text/plain", chunks=chunks(),
        )
        self.assertEqual((value.outcome, value.reason_code), ("rejected", "chunk_limit"))
        self.assertEqual(consumed, [0, 1, 2, 3, 4])

    def test_byte_and_chunk_boundaries_do_not_truncate_or_consume_tail(self):
        for chunks, outcome, reason in (
            ([b"12", b"34"], "allow", "accepted"),
            ([b"12", b"345"], "rejected", "result_too_large"),
            ([b"12", b"34", b""], "rejected", "chunk_limit"),
        ):
            with self.subTest(chunks=chunks):
                value = broker(max_bytes=4, max_chunks=2).sanitize_candidate(
                    channel="native_tool_result", content_type="text/plain", chunks=chunks,
                )
                self.assertEqual((value.outcome, value.reason_code), (outcome, reason))
                self.assertEqual(value.sanitized_payload, "1234" if outcome == "allow" else None)

    def test_nonfinite_json_and_redacted_key_collisions_fail_closed(self):
        for payload, reason in (
            (b'{"value":NaN}', "malformed_payload"),
            (b'{"value":Infinity}', "malformed_payload"),
            (b'{"value":1e999}', "malformed_payload"),
            (b'{"Authorization":"canary-a","password":"canary-b"}', "sanitizer_failure"),
        ):
            with self.subTest(payload=payload):
                value = broker().sanitize_candidate(
                    channel="native_tool_result", content_type="application/json", chunks=[payload],
                )
                self.assertEqual((value.outcome, value.reason_code), ("rejected", reason))
                self.assertNotIn("canary", json.dumps(value.to_dict()))

    def test_oversized_chunk_is_rejected_before_buffer_copy(self):
        class GuardedBuffer(bytearray):
            def extend(self, chunk):
                if len(chunk) > 4:
                    raise AssertionError("oversized chunk copied")
                super().extend(chunk)

        with patch("adaptive_factory.result_broker.bytearray", GuardedBuffer, create=True):
            value = broker(max_bytes=4).sanitize_candidate(
                channel="native_tool_result", content_type="text/plain", chunks=[b"12345"],
            )
        self.assertEqual((value.outcome, value.reason_code), ("rejected", "result_too_large"))

    def test_typed_envelope_failures_and_unknown_channel_parity(self):
        from adaptive_factory.result_contracts import ResultEnvelopeV1

        wire = broker().sanitize_candidate(
            channel="native_tool_result", content_type="text/plain", chunks=[b"safe"],
        ).to_dict()
        for field in ("channel", "outcome", "completeness", "content_type",
                      "policy_version", "reason_code", "sanitized_payload_digest"):
            with self.subTest(field=field), self.assertRaises(ContractError):
                ResultEnvelopeV1.from_dict({**wire, field: []})
        for field in ("content_type", "policy_version", "reason_code"):
            with self.subTest(field=field), self.assertRaises(ContractError):
                ResultEnvelopeV1.from_dict({**wire, field: "\ud800"})
        with self.assertRaises(ContractError):
            ResultEnvelopeV1.from_dict({**wire, "channel": "unknown"})
        from adaptive_factory.contracts import canonical_digest
        for payload in ('{"Authorization":"contract-canary"}',
                        '{"nested":{"password":{"value":"contract-canary"}}}',
                        '{"a":1,"a":2}', '{"value":NaN}', '{"value":"\\ud800"}',
                        '{"\\ud800":"safe"}'):
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                ResultEnvelopeV1.from_dict({
                    **wire, "content_type": "application/json", "sanitized_payload": payload,
                    "sanitized_payload_digest": canonical_digest(payload),
                })

    def test_closed_contract_outcomes_and_semantic_parity(self):
        from adaptive_factory.result_contracts import ResultEnvelopeV1

        envelope = broker().sanitize_candidate(
            channel="native_tool_result", content_type="application/json",
            chunks=(b'{"answer":"safe"}',),
        )
        self.assertEqual(envelope.outcome, "allow")
        self.assertEqual(ResultEnvelopeV1.from_dict(envelope.to_dict()), envelope)
        for mutation in (
            {**envelope.to_dict(), "extra": True},
            {**envelope.to_dict(), "outcome": "passed"},
            {**envelope.to_dict(), "sanitized_payload_digest": "0" * 64},
            {**envelope.to_dict(), "completeness": "missing"},
            {**envelope.to_dict(), "outcome": "rejected"},
            {**envelope.to_dict(), "outcome": "rejected", "completeness": "complete",
             "sanitized_payload": None,
             "sanitized_payload_digest": __import__("hashlib").sha256(b"null").hexdigest()},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                ResultEnvelopeV1.from_dict(mutation)

    def test_runtime_channels_are_unavailable_and_stream_is_not_consumed(self):
        from adaptive_factory.result_contracts import RESULT_CHANNELS

        for channel in RESULT_CHANNELS:
            consumed = []

            def stream():
                consumed.append(channel)
                yield b"unsafe"

            envelope = broker().inspect(
                channel=channel, content_type="text/plain", chunks=stream(),
            )
            self.assertEqual(
                (envelope.outcome, envelope.reason_code, consumed),
                ("unavailable", "runtime_wiring_missing", []),
            )

    def test_unknown_sanitization_and_unrecognized_inspection_reject_without_consuming(self):
        for method, channel in (("sanitize_candidate", "unknown"),
                                ("inspect", "unrecognized-private-channel")):
            with self.subTest(method=method, channel=channel):
                consumed = []

                def stream():
                    consumed.append(True)
                    yield b"private-result-canary"

                envelope = getattr(broker(), method)(
                    channel=channel, content_type="text/plain", chunks=stream(),
                )
                self.assertEqual(
                    (envelope.outcome, envelope.reason_code, envelope.sanitized_payload, consumed),
                    ("rejected", "invalid_channel", None, []),
                )
                self.assertNotIn("private", json.dumps(envelope.to_dict()))

    def test_limits_malformed_input_and_recursive_redaction_fail_closed(self):
        cases = (
            (dict(max_bytes=4), "text/plain", (b"12345",), "result_too_large"),
            (dict(max_records=1), "application/json", (b'["a","b"]',), "record_limit"),
            (dict(max_depth=2), "application/json", (b'{"a":{"b":1}}',), "depth_limit"),
            ({}, "text/plain", (b"\xff",), "invalid_encoding"),
            ({}, "text/plain", (b"safe\x00text",), "malformed_payload"),
            ({}, "text/plain", ("e\u0301".encode(),), "malformed_payload"),
            ({}, "application/json", (b'"\\ud800"',), "sanitizer_failure"),
            ({}, "application/json", ('{"value":"e\u0301"}'.encode(),), "sanitizer_failure"),
            ({}, "application/json", (b"{",), "malformed_payload"),
            ({}, "application/octet-stream", (b"safe",), "unsupported_content_type"),
        )
        for limits, content_type, chunks, reason in cases:
            with self.subTest(reason=reason):
                envelope = broker(**limits).sanitize_candidate(
                    channel="native_tool_result", content_type=content_type, chunks=chunks,
                )
                self.assertEqual((envelope.outcome, envelope.reason_code), ("rejected", reason))
                self.assertIsNone(envelope.sanitized_payload)

        multiline = broker().sanitize_candidate(
            channel="native_tool_result", content_type="text/plain",
            chunks=(b"line-one\n\tline-two",),
        )
        self.assertEqual((multiline.outcome, multiline.sanitized_payload),
                         ("allow", "line-one\n\tline-two"))

        for payload in (
            (b'{"nested":{"value":"pass', b'word=synthetic-canary"}}'),
            (b'{"pass' + b'word=synthetic-canary":"value"}',),
        ):
            envelope = broker().sanitize_candidate(
                channel="native_tool_result", content_type="application/json", chunks=payload,
            )
            wire = json.dumps(envelope.to_dict(), sort_keys=True)
            self.assertEqual(envelope.outcome, "redacted")
            self.assertNotIn("synthetic-canary", wire)
            self.assertNotIn("pass" + "word=", wire)

    def test_stream_and_metadata_failures_are_bounded(self):
        class BrokenStream:
            def __iter__(self):
                yield b"safe-prefix"
                raise TimeoutError("private stream diagnostic")

        cases = (
            dict(channel="unknown-private-channel", content_type="text/plain",
                 chunks=(b"safe",), reason="invalid_channel"),
            dict(channel="native_tool_result", content_type="pass" + "word=private-value",
                 chunks=(b"safe",), reason="invalid_content_type"),
            dict(channel="native_tool_result", content_type="text/plain",
                 chunks=BrokenStream(), reason="result_stream_failure"),
        )
        for case in cases:
            reason = case.pop("reason")
            with self.subTest(reason=reason):
                envelope = broker().sanitize_candidate(**case)
                wire = json.dumps(envelope.to_dict(), sort_keys=True)
                self.assertEqual((envelope.outcome, envelope.reason_code), ("rejected", reason))
                self.assertNotIn("private", wire)

    def test_digest_is_deterministic_and_envelope_is_immutable(self):
        first = broker().sanitize_candidate(
            channel="synthetic_child_report", content_type="application/json",
            chunks=(b'{"b":2,"a":1}',),
        )
        second = broker().sanitize_candidate(
            channel="synthetic_child_report", content_type="application/json",
            chunks=(b'{"a":1,"b":2}',),
        )
        changed = broker().sanitize_candidate(
            channel="native_tool_result", content_type="application/json",
            chunks=(b'{"a":1,"b":2}',),
        )
        self.assertEqual(first, second)
        self.assertEqual(first.record_digest, second.record_digest)
        self.assertNotEqual(first.record_digest, changed.record_digest)
        exported = first.to_dict()
        exported["sanitized_payload"] = "changed"
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
