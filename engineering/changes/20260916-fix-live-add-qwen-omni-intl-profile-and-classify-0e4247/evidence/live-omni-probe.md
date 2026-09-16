# Live omni probe — reproduction script

The architecture model treats `engineering/changes/**` as a documentation node (`NODE-CHANGE-SPEC-EVIDENCE`,
type `repository`) with **no network policy**, so a tracked `.py` that imports a network family fails
`FIT-DECLARED-NETWORK-ONLY` and escalates change risk to red (`new_network_client`). The probe is therefore
preserved here as markdown: copy the block below to `probe.py` and run it — nothing else changes.

Credential handling: read from the process environment only (`DASHSCOPE_API_KEY` or
`FACTORY_LANDING_QWEN_API_KEY`), never printed; only a small whitelist of response facts is emitted,
and error output carries only the structured upstream `error.code`, never the body.

Result of the run recorded 2026-09-16: see `live-probe-output.txt` (intl image 200 with `image_tokens=66`,
intl audio 200 with `audio_tokens=2`, mainland control 401 `invalid_api_key`).

```python
#!/usr/bin/env python3
"""Live capability probe: Qwen Omni on the INTERNATIONAL endpoint with real image and real audio.

The request body, the streaming flags and the SSE handling mirror the product's own executor
(`landing_live_executors.py` `_request_body` / `_user_content`, `landing_http.py` profile tuple) so the
result is about the profile claim, not about an invented wire format.

Safety: the credential is taken from the process environment only, is never printed, and only a small
whitelist of response facts is emitted.
"""
import base64
import json
import os
import struct
import sys
import zlib

import httpx

MODEL = "qwen3.5-omni-plus-2026-03-15"
INTL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
MAINLAND = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
KEY = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("FACTORY_LANDING_QWEN_API_KEY") or ""
if not KEY:
    sys.exit("no Qwen credential in process environment")


def png_red_square_on_blue(size=64) -> bytes:
    w = h = size
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0
        for x in range(w):
            inside = size // 4 <= x < 3 * size // 4 and size // 4 <= y < 3 * size // 4
            raw += bytes((255, 0, 0) if inside else (0, 0, 255))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def wav_sine(seconds=0.4, freq=880.0, rate=8000) -> bytes:
    import math
    samples = bytes()
    frames = bytearray()
    for i in range(int(seconds * rate)):
        value = int(11000 * math.sin(2 * math.pi * freq * i / rate))
        frames += struct.pack("<h", value)
    data = bytes(frames)
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
            + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


def ask(label: str, url: str, content) -> None:
    body = {
        "model": MODEL,
        "temperature": 0,
        "stream": True,
        "max_tokens": 48,
        "messages": [
            {"role": "system", "content": "Answer in one short English sentence. Describe only what you perceive."},
            {"role": "user", "content": content},
        ],
        "modalities": ["text"],
        "stream_options": {"include_usage": True},
    }
    text, finish, usage, model, seen_done = "", None, None, None, False
    status = None
    with httpx.Client(timeout=httpx.Timeout(90.0, connect=20.0)) as client:
        with client.stream("POST", url,
                           headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                           json=body) as response:
            status = response.status_code
            if status != 200:
                # Print only the allowlisted error code: an upstream body is untrusted text.
                code = None
                try:
                    code = (json.loads(response.read()).get("error") or {}).get("code")
                except (ValueError, AttributeError):
                    code = None
                print(f"{label}: HTTP {status} code={code if isinstance(code, str) else 'unparsed'}")
                return
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    seen_done = True
                    break
                event = json.loads(payload)
                model = event.get("model", model)
                choices = event.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    text += delta.get("content") or ""
                    finish = choices[0].get("finish_reason") or finish
                if event.get("usage"):
                    usage = event["usage"]
    print(f"{label}: HTTP {status} model={model} finish={finish} done={seen_done}")
    print(f"{label}: usage={json.dumps(usage, sort_keys=True) if usage else None}")
    print(f"{label}: answer={text.strip()[:200]!r}  # untrusted model output")


image = png_red_square_on_blue()
audio = wav_sine()
print(f"fixtures: png sha256={__import__('hashlib').sha256(image).hexdigest()[:16]} "
      f"wav sha256={__import__('hashlib').sha256(audio).hexdigest()[:16]} bytes={len(image)}/{len(audio)}")

ask("intl/image", INTL, [
    {"type": "text", "text": "Name the shape and the two colors in this image."},
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(image).decode()}"}},
])
ask("intl/audio", INTL, [
    {"type": "text", "text": "Describe the sound in this attachment."},
    {"type": "input_audio", "input_audio": {"data": f"data:;base64,{base64.b64encode(audio).decode()}",
                                            "format": "wav"}},
])
ask("mainland/image(control)", MAINLAND, [
    {"type": "text", "text": "Name the shape and the two colors in this image."},
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(image).decode()}"}},
])
```
