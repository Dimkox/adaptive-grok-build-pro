"""Execution coverage for the bounded Qwen Omni SSE decoder (factory/src/adaptive_factory/landing_sse.py).

The decoder is the only place where provider bytes become landing text, so these tests pin the
size ceilings, the frame ordering it refuses, and the fact that reasoning/audio/tool payloads are
discarded rather than folded into the retained draft.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace
import unittest

from adaptive_factory.landing_provider import (
    LandingProviderError,
    MAX_PROVIDER_OUTPUT_BYTES,
)
from adaptive_factory.landing_sse import QwenOmniStreamDecoder

MODEL_ID = "qwen3.5-omni-plus-2026-03-15"
LINE_LIMIT = 524_288


def profile(max_response_bytes=1_048_576, max_output_tokens=4_096):
    # The decoder reads exactly these three fields; a stub keeps the ceilings testable.
    return SimpleNamespace(
        max_response_bytes=max_response_bytes,
        max_output_tokens=max_output_tokens,
        model_id=MODEL_ID,
    )


def frame(*, content=None, finish=None, usage=None, choices=None, identity="chatcmpl-1",
            omit_identity=False):
    if choices is None:
        choices = [{
            "index": 0,
            "delta": {"role": "assistant", "content": content} if content is not None else {},
            "finish_reason": finish,
        }]
    document = {} if omit_identity else {
        "id": identity,
        "object": "chat.completion.chunk",
        "model": MODEL_ID,
        "choices": choices,
    }
    if usage is not None:
        document["usage"] = usage
    return b"data: " + bytes(str(__import__("json").dumps(document, separators=(",", ":"))), "utf-8")


def payload(event: bytes) -> bytes:
    """_event() receives already-joined data lines, i.e. without the SSE field prefix."""
    return event[len(b"data: "):] if event.startswith(b"data: ") else event


def stop_event():
    return frame(finish="stop", content=None)


def usage_event(prompt=11, completion=7, total=18):
    return frame(choices=[], usage={
        "prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total,
    })


def feed_all(decoder, frames):
    for item in frames:
        decoder.feed(item + b"\n\n")


class QwenOmniStreamDecoderTests(unittest.TestCase):
    def test_lone_surrogate_is_rejected_but_valid_unicode_is_preserved(self):
        decoder = QwenOmniStreamDecoder(profile())
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_content"):
            decoder.feed(frame(content="\ud800") + b"\n\n")
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, (frame(content="Здравствуйте ✓"), stop_event(), usage_event(), b"data: [DONE]"))
        self.assertEqual("Здравствуйте ✓".encode(), decoder.finish().stdout)

    def test_happy_path_returns_draft_digest_and_usage(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        raw = b"".join(
            item + b"\n\n"
            for item in (frame(content="Build "), frame(content="a landing"), stop_event(), usage_event())
        )
        decoder.feed(raw)
        decoder.feed(b"data: [DONE]\n\n")
        result = decoder.finish()
        self.assertEqual(b"Build a landing", result.stdout)
        self.assertEqual(hashlib.sha256(raw + b"data: [DONE]\n\n").hexdigest(), result.response_digest)
        self.assertEqual(11, result.usage_input_units)
        self.assertEqual(7, result.usage_output_units)
        self.assertEqual(0, result.elapsed_ms)

    def test_multiline_data_block_is_joined_into_one_event(self) -> None:
        # A blank line closes the event; successive data lines are joined with a single newline
        # byte, so one JSON document may be spread over several lines.
        decoder = QwenOmniStreamDecoder(profile())
        first = b'data: {"id":"a",'
        second = (b'data: "object":"chat.completion.chunk","model":"' + MODEL_ID.encode()
                  + b'","choices":[{"index":0,"delta":{"content":"kept"},"finish_reason":null}]}')
        decoder.feed(first + b"\n" + second + b"\n\n")
        self.assertEqual("a", decoder._identity)
        self.assertEqual(b"kept", bytes(decoder._content))
        self.assertEqual([], decoder._data)

    def test_reasoning_metadata_does_not_change_omni_completion_accounting(self):
        usage = {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18,
                 "completion_tokens_details": {"reasoning_tokens": 5}}
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, (frame(content="kept"), stop_event(),
                           frame(choices=[], usage=usage), b"data: [DONE]"))
        result = decoder.finish()
        self.assertEqual((11, 7), (result.usage_input_units, result.usage_output_units))
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, (frame(content="kept"), stop_event()))
        with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
            decoder.feed(frame(choices=[], usage={**usage, "total_tokens": 23}) + b"\n\n")

    def test_comment_lines_are_ignored(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        decoder.feed(b": keep-alive\n\n")
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_incomplete"):
            decoder.finish()

    def test_non_data_field_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_field"):
            decoder.feed(b"event: message\n\n")

    def test_total_response_ceiling_is_enforced(self) -> None:
        decoder = QwenOmniStreamDecoder(profile(max_response_bytes=2_048))
        with self.assertRaisesRegex(LandingProviderError, "executor_response_size"):
            for _ in range(8):
                decoder.feed(b"x" * 512)

    def test_unterminated_oversized_line_is_rejected_before_a_newline_arrives(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_line_size"):
            decoder.feed(b"data: " + b"x" * (LINE_LIMIT + 10))

    def test_oversized_single_line_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_line_size"):
            decoder.feed(b"data: " + b"x" * (LINE_LIMIT + 1) + b"\n")

    def test_event_body_ceiling_is_rejected(self) -> None:
        # A single oversized line is caught as a line-size violation; the event ceiling only
        # applies to a multi-line data block whose parts are individually admissible.
        decoder = QwenOmniStreamDecoder(profile())
        part = b"data: " + b"y" * 200_000
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_event_size"):
            for _ in range(4):
                decoder._line(part)

    def test_event_count_ceiling_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        event = frame(content="a")
        for _ in range(16_384):
            decoder._event(payload(event))
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_event_limit"):
            decoder._event(payload(event))

    def test_content_ceiling_is_rejected(self) -> None:
        # Text is bounded while it accumulates, not only at the end: a stream that keeps sending
        # past MAX_PROVIDER_OUTPUT_BYTES fails closed instead of holding the whole draft.
        decoder = QwenOmniStreamDecoder(profile())
        remainder = MAX_PROVIDER_OUTPUT_BYTES % 10_000
        decoder._event(payload(frame(content="a" * remainder)))
        for _ in range(MAX_PROVIDER_OUTPUT_BYTES // 10_000):
            decoder._event(payload(frame(content="a" * 10_000)))
        self.assertEqual(MAX_PROVIDER_OUTPUT_BYTES, len(decoder._content))
        with self.assertRaisesRegex(LandingProviderError, "executor_result"):
            decoder._event(payload(frame(content="one byte over")))

    def test_done_before_stop_is_incomplete(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        decoder.feed(frame(content="text") + b"\n\n")
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_incomplete"):
            decoder.feed(b"data: [DONE]\n\n")

    def test_usage_after_done_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="text"), stop_event(), usage_event()])
        decoder.feed(b"data: [DONE]\n\n")
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_after_done"):
            decoder.feed(frame(content="late") + b"\n\n")

    def test_usage_before_stop_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        decoder.feed(frame(content="text") + b"\n\n")
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_usage_order"):
            decoder._event(payload(usage_event()))

    def test_usage_totals_must_be_consistent(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="text"), stop_event()])
        with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
            decoder._event(payload(usage_event(prompt=5, completion=5, total=9)))

    def test_usage_completion_above_profile_ceiling_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile(max_output_tokens=8))
        feed_all(decoder, [frame(content="text"), stop_event()])
        with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
            decoder._event(payload(usage_event(prompt=1, completion=9, total=10)))

    def test_usage_must_be_an_object(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="text"), stop_event()])
        with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
            decoder._event(payload(frame(choices=[], usage="12")))

    def test_missing_usage_on_empty_choices_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="text"), stop_event()])
        with self.assertRaisesRegex(LandingProviderError, "executor_usage"):
            decoder._event(payload(frame(choices=[])))

    def test_duplicate_usage_event_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="text"), stop_event(), usage_event()])
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_usage_order"):
            decoder._event(payload(usage_event()))

    def test_identity_must_be_stable_and_complete(self) -> None:
        for label, event in (
            ("missing id", b'data: {"object":"chat.completion.chunk","model":"' + MODEL_ID.encode()
             + b'","choices":[]}\n\n'),
            ("wrong object", frame(content="a", identity=None) + b"\n\n"),
        ):
            with self.subTest(case=label):
                decoder = QwenOmniStreamDecoder(profile())
                with self.assertRaisesRegex(LandingProviderError, "executor_sse_identity"):
                    decoder.feed(event)
        decoder = QwenOmniStreamDecoder(profile())
        decoder.feed(frame(content="a") + b"\n\n")
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_identity"):
            decoder.feed(frame(content="b", identity="chatcmpl-2") + b"\n\n")

    def test_model_mismatch_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        event = frame(content="a").replace(MODEL_ID.encode(), b"other-model")
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_identity"):
            decoder.feed(event + b"\n\n")

    def test_usage_cannot_rideshare_with_a_choice(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="text"), stop_event()])
        smuggled = frame(usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_choice_order"):
            decoder._event(payload(smuggled))

    def test_multiple_choices_are_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_choice"):
            decoder._event(payload(frame(choices=[{"index": 0, "delta": {}, "finish_reason": None},
                                          {"index": 1, "delta": {}, "finish_reason": None}])))

    def test_side_channels_in_delta_are_rejected(self) -> None:
        for label, delta in (
            ("tool_calls", {"tool_calls": [{"id": "t"}]}),
            ("function_call", {"function_call": {"name": "x"}}),
            ("audio", {"audio": {"data": "AAA"}}),
            ("refusal", {"refusal": "no"}),
            ("role", {"role": "system"}),
            ("index", None),
        ):
            with self.subTest(channel=label):
                decoder = QwenOmniStreamDecoder(profile())
                choice = {"index": 0, "delta": delta or {}, "finish_reason": None}
                if label == "index":
                    choice = {"index": 7, "delta": {}, "finish_reason": None}
                with self.assertRaisesRegex(LandingProviderError, "executor_sse_delta"):
                    decoder._event(payload(frame(choices=[choice])))

    def test_non_string_content_is_rejected(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_content"):
            decoder._event(payload(frame(choices=[
                {"index": 0, "delta": {"content": {"text": "x"}}, "finish_reason": None}])))

    def test_reasoning_content_is_discarded_not_joined(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        decoder._event(payload(frame(choices=[
            {"index": 0, "delta": {"content": "kept", "reasoning_content": "secret chain"},
             "finish_reason": None}])))
        self.assertEqual(b"kept", bytes(decoder._content))
        self.assertNotIn(b"secret", bytes(decoder._content))

    def test_finish_flushes_a_line_left_without_a_trailing_newline(self) -> None:
        # A provider that closes the socket mid-frame must still have its last line parsed: the
        # final usage event and [DONE] can arrive without a terminating newline.
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="tail flush"), stop_event()])
        decoder.feed(usage_event() + b"\n\n")
        decoder.feed(b"data: [DONE]")
        self.assertTrue(decoder._pending)
        result = decoder.finish()
        self.assertEqual(b"tail flush", result.stdout)
        self.assertEqual([], list(decoder._pending))

    def test_finish_flushes_an_open_data_block(self) -> None:
        # Data lines with no closing blank line at stream end are still dispatched as one event.
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="open block"), stop_event(), usage_event()])
        decoder.feed(b"data: [DONE]")
        decoder._pending.clear()
        decoder._data.append(b"[DONE]")
        decoder.finish()
        self.assertTrue(decoder._done)

    def test_finish_requires_done_flag_and_non_blank_text(self) -> None:
        decoder = QwenOmniStreamDecoder(profile())
        feed_all(decoder, [frame(content="text"), stop_event(), usage_event()])
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_incomplete"):
            decoder.finish()

        blank = QwenOmniStreamDecoder(profile())
        feed_all(blank, [frame(content="   "), stop_event(), usage_event()])
        blank.feed(b"data: [DONE]\n\n")
        with self.assertRaisesRegex(LandingProviderError, "executor_sse_incomplete"):
            blank.finish()

    def test_crlf_and_split_frames_reassemble(self) -> None:
        stream = b"".join(item + b"\r\n\r\n" for item in
                          (frame(content="split "), frame(content="stream"), stop_event(), usage_event()))
        stream += b"data: [DONE]\r\n\r\n"
        for size in (1, 7, 13, 97):
            with self.subTest(chunk=size):
                chunked = QwenOmniStreamDecoder(profile())
                for start in range(0, len(stream), size):
                    chunked.feed(stream[start:start + size])
                self.assertEqual(b"split stream", chunked.finish().stdout)


if __name__ == "__main__":
    unittest.main()
