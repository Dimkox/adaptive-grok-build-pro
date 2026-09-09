# Requirements — Add default-off live Grok and live Qwen landing executors plus explicit Python/system requirements for the current host configuration; no live API calls in tests; no landing-repo mutation.

## Closed host Python / system record (this operator host)

These values are the frozen product record. Tests assert the record and `factory/pyproject.toml`; they do not hash a CI runner's `/usr/bin/python3.12`.

| Field | Value |
| --- | --- |
| Python executable | `/usr/bin/python3.12` |
| Python version prefix | `3.12.3` |
| Python SHA-256 | `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223` |
| Implementation / machine observed here | CPython, Linux x86_64, glibc 2.39; `/usr/bin/python3` → `/usr/bin/python3.12` |
| Factory `requires-python` | `>=3.11` |
| Factory `httpx` | `0.28.1` (already pinned; not bumped) |
| Other factory runtime pins (unchanged) | `fastapi==0.128.2`, `uvicorn==0.48.0`, `psycopg[binary]==3.3.4` |
| Grok | `https://api.x.ai/v1` model `grok-4`, env name `FACTORY_LANDING_GROK_API_KEY` |
| Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` model `qwen-plus`, env name `FACTORY_LANDING_QWEN_API_KEY` |

## Acceptance criteria

- [x] Given the frozen host record, when tests read `CURRENT_LANDING_HOST_REQUIREMENTS` and `factory/pyproject.toml`, then Python 3.12.3 at `/usr/bin/python3.12`, SHA-256 `a92f0f95…96223`, `requires-python >=3.11`, and `httpx==0.28.1` match.
- [x] Given missing or blank Grok/Qwen API keys, when an executor is constructed, then it fails closed with `credential_unavailable` and no HTTP client request is made.
- [x] Given mocked Grok and Qwen chat completions, when `run` is called, then assistant JSON is returned as executor stdout for models `grok-4` and `qwen-plus`.
- [x] Given HTTP 500, transport error, or malformed body, when `run` is called, then the executor fails closed.
- [x] Given `compose_landing_live_grok` / `compose_landing_live_qwen` with MockTransport, when an authenticated text submit runs, then the job is `artifact_ready` with the 20-member artifact and `live_url` null.
- [x] Given `landing_runtime.py`, when its AST is inspected, then it does not import `httpx` or `landing_live_executors`.

## Failure and edge cases

- Missing/blank API key: fail before client
- Non-HTTPS base URL: `base_url`
- HTTP non-200: `executor_http`
- `httpx.HTTPError`: `executor_transport`
- Missing assistant content / oversize stdout: `executor_result`
- Invalid stdin: `executor_request`
- PDF/audio still `needs_human` before executor
- Observed SHA `80d6215` still `source_binding_unimplemented`

## Non-functional requirements

- Security: caller injects the key; no `.env` read; tests use fake literals `test-grok` / `test-qwen`
- Reliability: one POST per successful `run`; no retry loop; timeout from the execution request
- Performance: mocked request only in tests; no new workers
- Observability: existing job `state`; `live_url` remains JSON-null
