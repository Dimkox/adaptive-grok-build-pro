# Analysis — repo_explorer

Change: `20260906-add-default-off-live-grok-and-live-qwen-landing-4a8bbb`
Product tree: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-live` (`feat/factory-live-auto-landing`, ahead of `fd51dcf`).
Question: where to add live Grok (xAI) and live Qwen `CodexLandingExecutor` implementations without violating `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY`.

## Boundary (authoritative)

`architecture/rules.yaml` `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY` (severity error) forbids these **import prefixes** in these **exact files**:

Forbidden: `adaptive_factory.adapters`, `adaptive_factory.brokers`, `adaptive_factory.migrations`, `adaptive_factory.service`, `adaptive_factory.store`, `adaptive_trust_ci`, `trust_ci`, `celery`, **`httpx`**, `psycopg`, `requests`, `rq`, **`socket`**, **`urllib`**.

Source files: `landing_artifact.py`, `landing_artifact_retention.py`, `landing_contracts.py`, `landing_coordinator.py`, `landing_evaluation.py`, `landing_intake.py`, `landing_normalizer.py`, `landing_provider.py`, `landing_renderer.py`, **`landing_runtime.py`**, `landing_service.py`, `landing_sqlite_store.py`.

The FIT list is exact paths, not a `landing_*.py` glob. A **new** module under `factory/src/adaptive_factory/` that is **not** on that list may import `httpx`.

`NODE-FACTORY-LANDING-DOGFOOD` (`architecture/system.yaml`) has `runtime.network: none` and lists the same dogfood Python files (plus schemas). Live HTTP must **not** be folded into that node’s paths or into `landing_runtime.py`. `EDGE-FACTORY-API-LANDING-DOGFOOD` is `network_policy: no_network`.

`factory/pyproject.toml` already pins `httpx==0.28.1`. Production `httpx` usage today is **only** `factory/src/adaptive_factory/cli.py` (UDS client). Tests use `httpx` in `test_server.py`. That does not license `httpx` inside the FIT-listed landing modules.

## Current injection seam

`CodexLandingExecutor` is a Protocol in `landing_normalizer.py`:

```python
class CodexLandingExecutor(Protocol):
    def run(self, request: CodexExecutionRequest) -> CodexExecutionResult: ...
```

`compose_landing_live` (`landing_runtime.py`) takes `executor: CodexLandingExecutor` and only rejects `executor is None`. It does **not** type-check the concrete class. It wires `CodexLandingNormalizer(profile, executor)` plus coordinator/packager. Default `server.build_app()` does **not** call `compose_landing_live` (comment: constructor-injected only).

Tests already inject fakes: `RecordingExecutor` in `factory/tests/test_landing_normalizer.py`, used by `test_landing_live.py`.

`adapters/grok.py` / `adapters/codex.py` are M5 native-event adapters (`execution_eligible=False` for Grok). They are **not** `CodexLandingExecutor` implementations. FIT also forbids `adaptive_factory.adapters` **from** the landing dogfood files, so `landing_runtime.py` must not import them.

## Recommended placement

| Piece | Put it here | Do not put it here |
| --- | --- | --- |
| Live HTTP `run()` for xAI Grok and Qwen | **New module(s) outside FIT prefixes**, e.g. `factory/src/adaptive_factory/live_landing_executors.py` (one file, two classes) or `live_grok_executor.py` + `live_qwen_executor.py` | `landing_runtime.py`, `landing_normalizer.py`, any other FIT-listed `landing_*.py` |
| Optional wiring (default-off) | `server.py` / CLI / operator script: construct executor **then** pass into `compose_landing_live(...)` | Import `httpx`/`urllib`/`socket` from `landing_runtime.py` |
| Protocol / compose signature | Keep `CodexLandingExecutor` + `compose_landing_live(..., executor=...)` unchanged | New protocol in the dogfood node |
| Tests | Fake/recording executor; no live API; no landing-repo mutation (existing `test_landing_live.py` pattern) | Network in unit tests |

Concrete types should implement `def run(self, request: CodexExecutionRequest) -> CodexExecutionResult` using factory’s existing `httpx==0.28.1` **inside the new module only**. `landing_runtime.compose_landing_live` stays a pure composer: it never constructs or imports the HTTP clients.

If architecture snapshots must mention outbound calls, add a **separate** node/edge with an explicit network policy; do not set `NODE-FACTORY-LANDING-DOGFOOD.runtime.network` to anything other than `none`.

## Impact surface

- Touch: new executor module(s); optional `server.py` injection behind default-off flags; tests mirroring `RecordingExecutor`; possibly `factory/README.md` / system YAML for a new node.
- Do not touch FIT-listed landing files except if `compose_landing_live` later needs a named factory function that still only **receives** an executor (no `httpx` import).
- Do not reuse `GrokAdapter` as the landing executor.
- Do not add `httpx` to `landing_runtime.py` even though the package already depends on it.

No implementation in this pass.
