# Code review — 20260906-add-default-off-live-grok-and-live-qwen-landing-4a8bbb

**Reviewer:** code_reviewer (route 4a8bbb / local active-route may differ)  
**Checkout:** `/home/pall/grok-projects/adaptive-grok-build-pro-l5-live`  
**Branch:** `feat/factory-live-auto-landing`  
**Base:** `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`  
**Status: PASS**

## Scope inspected

Actual product diff vs `origin/main` plus uncommitted files:

- `factory/src/adaptive_factory/landing_live_executors.py` (new HTTP adapters)
- `factory/src/adaptive_factory/landing_runtime.py` (`compose_landing_live`, no httpx)
- `factory/tests/test_landing_live_executors.py`
- `factory/tests/test_landing_runtime.py` (blob-store clock + renderer SHA/tree pin)
- `architecture/system.yaml` (`NODE-FACTORY-LANDING-LIVE-EXECUTORS`, `NODE-FACTORY-LANDING-MODEL-PROVIDER`)
- `factory/README.md` host requirements table
- `factory/.env.example` placeholders only
- `factory/src/adaptive_factory/server.py` composition path (surrounding, not wired to live executors)

No merge, push, live API, or `.env` read was performed.

## Findings

None that fail acceptance.

## Contract check

| Requirement | Result |
| --- | --- |
| Default-off Grok/Qwen executors; constructor-injected API keys | PASS. `grok_landing_executor` / `qwen_landing_executor` require non-blank `api_key`. `api_key_from_environ` fails `credential_unavailable` on missing/blank. Blank constructor key is rejected before `httpx.Client`. |
| MockTransport in tests; no real sockets | PASS. Tests inject `httpx.MockTransport` or a `ConnectError` transport. No default `Client()` without transport in tests. |
| `live_url` null | PASS. Compose tests assert `created.job.result_view()["live_url"]` is `None`. |
| FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY: no httpx in `landing_runtime.py` | PASS. Module imports coordinator/renderer/service only. AST test forbids `httpx` and `landing_live_executors`. New HTTP module is **not** on the FIT source_prefixes list. Lazy import is `from .landing_runtime import compose_landing_live` inside the HTTP module (one-way). |
| Host record Python 3.12.3 `/usr/bin/python3.12` SHA `a92f0f95…96223`, httpx 0.28.1, requires-python `>=3.11` | PASS. Constants, README table, and tests vs `pyproject.toml` match. Tests do not hash a runner binary. |
| Shipped server must not construct these executors | PASS. `create_factory_app` still builds `UnavailableLandingProvider` when landing is enabled. `server.py` does not import `landing_live_executors` or the Grok/Qwen env names. |
| Architecture nodes | PASS. Live adapters own `landing_live_executors.py` with `network: declared_egress`. Dogfood node remains `network: none`. HTTPS edge is `EDGE-FACTORY-LANDING-LIVE-MODELS` to `NODE-FACTORY-LANDING-MODEL-PROVIDER`. `secrets: []` matches constructor injection (keys not loaded by the node). |
| `.env.example` | PASS. Placeholder names only (`replace-*-key-for-local-use`). |

## Runtime notes (non-blocking)

- `OpenAICompatibleLandingExecutor.run` opens `httpx.Client` with optional transport; omitting transport in a real operator call would use the network. That is intended for default-off, constructor-injected live use, not the shipped server.
- `elapsed_ms` is a bounded stub (`min(timeout*1000, 25)`), not wall time. Existing Codex fixture pattern; not a contract fail.
- `test_landing_runtime.py` now pins renderer `TARGET_BASE_SHA`/`TARGET_BASE_TREE` and injects `PrivateLandingBlobStore(clock=...)` so sealed replay stays deterministic.

## Verdict

**PASS** — slice matches the change package and closed requirements. Independent test review still owns test-quality scoring.
