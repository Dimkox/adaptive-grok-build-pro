import json
import unittest

from adaptive_factory.contracts import ContractError


def broker(**limits):
    from adaptive_factory.result_broker import ResultBroker

    return ResultBroker(policy_version="result-sanitizer/1", **limits)


def identity(**changes):
    value = {
        "repository_id": "repo/example",
        "task_id": "11111111-1111-4111-8111-111111111111",
        "run_id": "22222222-2222-4222-8222-222222222222",
        "fence": 7,
        "packet_digest": "3" * 64,
        "attempt_id": "44444444-4444-4444-8444-444444444444",
        "source_operation": "tool.call/read",
        "source_digest": "5" * 64,
    }
    value.update(changes)
    return value


class ResultBrokerTests(unittest.TestCase):
    def test_closed_contract_outcomes_and_semantic_parity(self):
        from adaptive_factory.result_contracts import ResultEnvelopeV2

        envelope = broker().sanitize_candidate(
            identity=identity(),
            channel="native_tool_result", content_type="application/json",
            chunks=(b'{"answer":"safe"}',),
        )
        self.assertEqual(envelope.outcome, "allow")
        self.assertEqual(ResultEnvelopeV2.from_dict(envelope.to_dict()), envelope)
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
                ResultEnvelopeV2.from_dict(mutation)

        secret_vectors = (
            "Authorization: Basic dXNlcjpwYXNz",
            "X_AUTHORIZATION=Basic dXNlcjpwYXNz",
            "Bearer abc.def",
            "api_key=not-safe",
            "my_password_value=foo",
            "client_secret_rotated=foo",
            "-----BEGIN PRIVATE KEY-----",
        )
        for field in ("content_type", "reason_code", "policy_version"):
            for secret in secret_vectors:
                with self.subTest(field=field, secret=secret), self.assertRaises(ContractError):
                    ResultEnvelopeV2.from_dict({**envelope.to_dict(), field: secret})

        bare_basic = {**envelope.to_dict(), "reason_code": "Basic dXNlcjpwYXNz"}
        self.assertEqual(ResultEnvelopeV2.from_dict(bare_basic).reason_code, bare_basic["reason_code"])
        for field, accepted in (
            ("content_type", "safe text"),
            ("reason_code", "my_password_value"),
            ("policy_version", "client_secret_rotated"),
            ("reason_code", "safe\x7ftext"),
            ("reason_code", "safe\u0085text"),
            ("policy_version", "-----begin private key-----"),
        ):
            self.assertEqual(
                getattr(ResultEnvelopeV2.from_dict({**envelope.to_dict(), field: accepted}), field),
                accepted,
            )
        with self.assertRaises(ContractError):
            ResultEnvelopeV2.from_dict({**envelope.to_dict(), "content_type": "safe\ntext"})

    def test_runtime_channels_are_unavailable_and_stream_is_not_consumed(self):
        from adaptive_factory.result_contracts import RESULT_CHANNELS

        for channel in RESULT_CHANNELS - {"unknown"}:
            consumed = []

            def stream():
                consumed.append(channel)
                yield b"unsafe"

            envelope = broker().inspect(
                identity=identity(),
                channel=channel, content_type="text/plain", chunks=stream(),
            )
            self.assertEqual(
                (envelope.outcome, envelope.reason_code, consumed),
                ("unavailable", "runtime_wiring_missing", []),
            )

    def test_limits_malformed_input_and_recursive_redaction_fail_closed(self):
        cases = (
            (dict(max_bytes=4), "text/plain", (b"12345",), "result_too_large"),
            (dict(max_records=1), "application/json", (b'["a","b"]',), "record_limit"),
            (dict(max_depth=2), "application/json", (b'{"a":{"b":1}}',), "depth_limit"),
            ({}, "text/plain", (b"\xff",), "invalid_encoding"),
            ({}, "text/plain", (b"safe\x00text",), "malformed_payload"),
            ({}, "text/plain", (b"safe\rtext",), "malformed_payload"),
            ({}, "text/plain", ("e\u0301".encode(),), "malformed_payload"),
            ({}, "application/json", (b'"\\ud800"',), "sanitizer_failure"),
            ({}, "application/json", ('{"value":"e\u0301"}'.encode(),), "sanitizer_failure"),
            ({}, "application/json", (b"{",), "malformed_payload"),
            ({}, "application/octet-stream", (b"safe",), "unsupported_content_type"),
        )
        for limits, content_type, chunks, reason in cases:
            with self.subTest(reason=reason):
                envelope = broker(**limits).sanitize_candidate(
                    identity=identity(),
                    channel="native_tool_result", content_type=content_type, chunks=chunks,
                )
                self.assertEqual((envelope.outcome, envelope.reason_code), ("rejected", reason))
                self.assertIsNone(envelope.sanitized_payload)

        multiline = broker().sanitize_candidate(
            identity=identity(),
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
                identity=identity(),
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
                envelope = broker().sanitize_candidate(identity=identity(), **case)
                wire = json.dumps(envelope.to_dict(), sort_keys=True)
                self.assertEqual((envelope.outcome, envelope.reason_code), ("rejected", reason))
                self.assertNotIn("private", wire)

    def test_digest_is_deterministic_and_envelope_is_immutable(self):
        first = broker().sanitize_candidate(
            identity=identity(),
            channel="synthetic_child_report", content_type="application/json",
            chunks=(b'{"b":2,"a":1}',),
        )
        second = broker().sanitize_candidate(
            identity=identity(),
            channel="synthetic_child_report", content_type="application/json",
            chunks=(b'{"a":1,"b":2}',),
        )
        changed = broker().sanitize_candidate(
            identity=identity(source_digest="6" * 64),
            channel="native_tool_result", content_type="application/json",
            chunks=(b'{"a":1,"b":2}',),
        )
        self.assertEqual(first, second)
        self.assertEqual(first.record_digest, second.record_digest)
        self.assertNotEqual(first.record_digest, changed.record_digest)
        exported = first.to_dict()
        exported["sanitized_payload"] = "changed"
        self.assertEqual(first, second)

    def test_identity_is_required_closed_and_digest_bound(self):
        from adaptive_factory.result_contracts import ResultEnvelopeV2

        envelope = broker().sanitize_candidate(
            identity=identity(), channel="native_tool_result",
            content_type="text/plain", chunks=(b"safe",),
        )
        self.assertEqual(envelope.repository_id, "repo/example")
        for key, value in (
            ("packet_digest", "bad"),
            ("source_digest", "0" * 63),
            ("fence", 0),
            ("task_id", "not-a-uuid"),
            ("source_operation", "bad operation"),
        ):
            candidate = envelope.to_dict()
            candidate[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                ResultEnvelopeV2.from_dict(candidate)


if __name__ == "__main__":
    unittest.main()
