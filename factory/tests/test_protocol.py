import json
import unittest

from adaptive_factory.protocol import CanonicalEvent, EventStreamParser, ProtocolError, ProtocolLimits


TASK = "task-001"
RUN = "run-001"
PACKET = "a" * 64


def event(sequence, event_type, payload):
    return {
        "protocol_version": "adaptive-factory.execution/v1",
        "task_id": TASK,
        "run_id": RUN,
        "packet_digest": PACKET,
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload,
    }


def line(value):
    return json.dumps(value, separators=(",", ":")).encode() + b"\n"


def parser(**limit_overrides):
    return EventStreamParser(
        task_id=TASK,
        run_id=RUN,
        packet_digest=PACKET,
        declared_capabilities=("notes", "structured_output", "usage"),
        limits=ProtocolLimits(**limit_overrides),
    )


class ProtocolTests(unittest.TestCase):
    def test_complete_stream_returns_only_canonical_events(self):
        stream = parser()
        values = [
            event(1, "adapter.ready", {"capabilities": ["notes", "structured_output", "usage"], "provider_id": "codex"}),
            event(2, "run.started", {"stage": "invoke"}),
            event(3, "note.proposed", {"note_type": "conclusion", "body": "bounded", "evidence": ["factory/src/a.py"]}),
            event(4, "usage.reported", {"provider_call_id": "call-1", "price_table_digest": "b" * 64, "input_tokens": 10, "output_tokens": 4, "reasoning_tokens": 2, "cost_usd_micros": 30, "output_bytes": 20}),
            event(5, "run.completed", {"summary": "fixture complete"}),
        ]
        for value in values:
            stream.feed(line(value))
        result = stream.finish()
        self.assertEqual(tuple(item.event_type for item in result), ("adapter.ready", "run.started", "note.proposed", "usage.reported", "run.completed"))
        self.assertEqual(result[2].payload["body"], "bounded")

    def test_duplicate_keys_nonfinite_and_invalid_utf8_fail(self):
        duplicate = b'{"protocol_version":"adaptive-factory.execution/v1","task_id":"task-001","task_id":"other"}\n'
        nonfinite = line(event(1, "run.completed", {"summary": float("nan")}))
        invalid_utf8 = b"\xff\n"
        for raw, code in ((duplicate, "duplicate_key"), (nonfinite, "nonfinite_number"), (invalid_utf8, "invalid_utf8")):
            with self.subTest(code=code), self.assertRaisesRegex(ProtocolError, code):
                parser().feed(raw)

    def test_identity_sequence_terminal_and_capability_violations_fail(self):
        cases = []
        wrong = event(1, "run.completed", {"summary": "x"})
        wrong["run_id"] = "other"
        cases.append(([wrong], "identity_mismatch"))
        cases.append(([event(2, "run.completed", {"summary": "x"})], "invalid_sequence"))
        cases.append(([event(1, "artifact.proposed", {"artifact_class": "report", "path": "a", "sha256": "b" * 64, "size_bytes": 1, "media_type": "text/plain"})], "undeclared_capability"))
        cases.append(([event(1, "run.completed", {"summary": "x"}), event(2, "note.proposed", {"note_type": "finding", "body": "x", "evidence": []})], "after_terminal"))
        for values, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ProtocolError, code):
                stream = parser()
                for value in values:
                    stream.feed(line(value))

    def test_reasoning_or_raw_output_keys_never_cross_boundary(self):
        for key in ("reasoning", "scratchpad", "chain_of_thought", "analysis", "raw_prompt", "stdout", "stderr", "native_stream"):
            with self.subTest(key=key), self.assertRaisesRegex(ProtocolError, "forbidden_content"):
                parser().feed(line(event(1, "run.completed", {"summary": "safe", key: "secret"})))

    def test_forbidden_note_categories_cannot_become_durable_metadata(self):
        for note_type in (
            "analysis", "Reasoning", "scratch-pad", " raw prompt ",
            "model_analysis", "private-reasoning", "raw_prompt_dump",
            "private_thoughts", "hidden_cot", "raw_response",
            "internal_deliberation", "late", "x",
        ):
            with self.subTest(note_type=note_type), self.assertRaisesRegex(
                ProtocolError, "forbidden_content"
            ):
                parser().feed(line(event(
                    1, "note.proposed",
                    {"note_type": note_type, "body": "safe", "evidence": []},
                )))
        for note_type in ("finding", "conclusion", "decision.record"):
            stream = parser()
            stream.feed(line(event(
                1, "note.proposed",
                {"note_type": note_type, "body": "safe", "evidence": []},
            )))

    def test_every_payload_field_is_closed_and_scalar_typed(self):
        cases = (
            ("run.completed", {"summary": {"value": "not text"}}),
            ("run.failed", {"failure_class": "protocol", "diagnostic": ["not", "text"]}),
            ("run.needs_human", {"reason": "operator", "diagnostic": {"value": "not text"}}),
            ("note.proposed", {"note_type": "finding", "body": "safe", "evidence": [1]}),
            (
                "artifact.proposed",
                {
                    "artifact_class": "report", "path": "report.json", "sha256": "b" * 64,
                    "size_bytes": 1.5, "media_type": "application/json",
                },
            ),
        )
        capabilities = ("artifacts", "notes", "structured_output", "usage")
        for event_type, payload in cases:
            with self.subTest(event_type=event_type), self.assertRaisesRegex(
                ProtocolError, "payload_fields"
            ):
                EventStreamParser(TASK, RUN, PACKET, capabilities).feed(
                    line(event(1, event_type, payload))
                )

    def test_event_type_is_a_known_scalar_before_membership_or_payload_lookup(self):
        for event_type in ({}, []):
            with self.subTest(event_type=event_type), self.assertRaisesRegex(
                ProtocolError, "unknown_event"
            ):
                EventStreamParser(TASK, RUN, PACKET, ("structured_output",)).feed(
                    line(event(1, event_type, {"summary": "done"}))
                )
            with self.subTest(direct=event_type), self.assertRaisesRegex(
                ProtocolError, "unknown_event"
            ):
                CanonicalEvent.from_payload(
                    task_id=TASK, run_id=RUN, packet_digest=PACKET, sequence=1,
                    event_type=event_type, payload={"summary": "done"},
                )

    def test_line_stream_event_depth_and_node_limits_fail_before_retention(self):
        cases = [
            (ProtocolLimits(max_line_bytes=64), line(event(1, "run.completed", {"summary": "x" * 100})), "line_too_large"),
            (ProtocolLimits(max_stream_bytes=64), line(event(1, "run.completed", {"summary": "x" * 100})), "stream_too_large"),
            (ProtocolLimits(max_depth=2), line(event(1, "run.completed", {"summary": {"a": {"b": "x"}}})), "structure_too_deep"),
            (ProtocolLimits(max_nodes=4), line(event(1, "run.completed", {"summary": "x"})), "structure_too_large"),
        ]
        for limits, raw, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ProtocolError, code):
                EventStreamParser(TASK, RUN, PACKET, ("structured_output",), limits).feed(raw)
        stream = parser(max_events=1)
        stream.feed(line(event(1, "run.started", {"stage": "invoke"})))
        with self.assertRaisesRegex(ProtocolError, "event_limit"):
            stream.feed(line(event(2, "run.completed", {"summary": "x"})))

    def test_finish_requires_exactly_one_terminal_and_no_partial_line(self):
        stream = parser()
        stream.feed(line(event(1, "run.started", {"stage": "invoke"})))
        with self.assertRaisesRegex(ProtocolError, "missing_terminal"):
            stream.finish()
        partial = parser()
        partial.feed(line(event(1, "run.completed", {"summary": "x"}))[:-1])
        with self.assertRaisesRegex(ProtocolError, "partial_line"):
            partial.finish()


if __name__ == "__main__":
    unittest.main()
