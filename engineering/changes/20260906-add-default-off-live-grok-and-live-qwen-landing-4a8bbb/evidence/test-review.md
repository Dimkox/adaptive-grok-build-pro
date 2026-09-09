# Test review — 20260906-add-default-off-live-grok-and-live-qwen-landing-4a8bbb

**Verdict: PASS**

Route `4a8bbb4fa8a6`. Re-review after the AC-001 SHA literal assertion. Inspected `factory/tests/test_landing_live_executors.py` (`test_host_requirements_match_current_python_and_httpx` now asserts hex `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223` on `requirements.python_sha256` **and** equality with `CURRENT_PYTHON_SHA256`), blob-store `clock=` in `factory/tests/test_landing_runtime.py`, host constants in `landing_live_executors.py`, `landing_runtime.py` AST, `DEPLOY_MEMBERS` (20), and `change-spec.yaml` AC-001..AC-007 / FORBID-001/002. Product code was not modified in this review. Prior `factory-postgres-exit` / `grok_verify --mode pr` PASS (834s, changed=46) is accepted as already-run verification evidence for that tree; this re-review is characterization-only.

## AC-001 (closed)

Host pin table is now a test literal, not a self-equality:

- Python executable `/usr/bin/python3.12`
- Version prefix `3.12.3`
- SHA-256 `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223`
- `requires-python` `>=3.11` and `httpx==0.28.1` (dataclass + `pyproject.toml`)

Tests do **not** hash CI `/usr/bin/python3.12` at runtime.

## Remaining criteria

| Criterion | Result |
| --- | --- |
| AC-002 missing/blank keys fail closed without HTTP | Pass. Empty environ mapping and whitespace constructor key → `credential_unavailable`. |
| AC-003 MockTransport Grok grok-4 / Qwen qwen-plus | Pass. Path `/chat/completions`, Bearer prefix, model asserted; stdout is `draft()` JSON. |
| AC-004 compose seals 20-member artifact, `live_url` null | Pass. Both compose helpers inject MockTransport and fixed clock; `artifact_ready`; `member_names == sorted(DEPLOY_MEMBERS)`. |
| AC-005 HTTP 500 / transport / malformed | Pass. `executor_http` / `executor_transport` / `executor_result`. |
| AC-006 pyproject pins | Pass. |
| AC-007 `landing_runtime.py` AST | Pass. No `httpx` or `landing_live_executors` import. |
| FORBID-001 no real Grok/Qwen sockets in tests | Pass. No `run()` with `transport=None`. |
| FORBID-002 no `.env`; no non-null `live_url` | Pass. |
| INV-001 constructor-injected, default-off | Pass. |
| INV-002 httpx outside landing dogfood core | Pass. |
| Blob clock in `test_landing_runtime.py` | Pass. `PrivateLandingBlobStore(..., clock=lambda: FIXED_TIME)`. |

## Notes (non-blocking)

- Production `OpenAICompatibleLandingExecutor` still defaults `transport=None` (real Client). The test suite never calls `run` on that path.
- Blank environ `{GROK_API_KEY_ENV: "  "}` is covered by strip via empty mapping plus constructor whitespace, not a dedicated mapping case.
