# Test plan

Use offline httpx fixtures based on sanitized live metadata; no API key or real network in automated tests. Cover captured separate-reasoning counters, no-reasoning/legacy success, invalid/missing details, bool/negative/overflow, output cap, Qwen nonstreaming/SSE preservation and retained evidence/profile identity. Run focused tests, then python3 scripts/grok_verify.py --mode pr on a frozen tree, then independent reviews.
