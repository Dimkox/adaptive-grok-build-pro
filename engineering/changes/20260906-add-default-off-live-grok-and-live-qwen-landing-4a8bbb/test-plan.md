# Test plan — Add default-off live Grok and live Qwen landing executors plus explicit Python/system requirements for the current host configuration; no live API calls in tests; no landing-repo mutation.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Host record equals current pins; pyproject `httpx==0.28.1` | `factory/tests/test_landing_live_executors.py` |
| P0 | Blank/missing API key → `credential_unavailable` | same |
| P0 | Grok/Qwen MockTransport `run` returns draft JSON | same |
| P0 | Injected compose seals 20-member artifact; `live_url` null | same |
| P0 | `landing_runtime.py` does not import `httpx` | same |
| P1 | HTTP 500 / transport error / malformed body fail closed | same |
| P1 | Existing RecordingExecutor live path stays green | `factory/tests/test_landing_live.py` |

## Automated checks

- Unit: `factory/tests/test_landing_live_executors.py`
- Integration: none (no live PostgreSQL / real provider)
- Contract: OpenAPI landing result `live_url` unchanged
- E2E: none
- Static analysis: architecture fitness + FIT landing dogfood boundary

## Manual checks

- None for this slice. Real provider turns remain grant-gated.
