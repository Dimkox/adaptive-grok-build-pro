# Architect — default-off live Grok and Qwen landing executors plus closed host requirements

Route: `4a8bbb4fa8a6`
Change: `20260906-add-default-off-live-grok-and-live-qwen-landing-4a8bbb`
Product tree: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-live`
Authority SHA: `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`
Role: read-only design. This report is the only write from this agent.

Loaded `/adaptive-delivery` and `/feature-workflow`. This agent is in `allowed_agents`.
Siblings: `evidence/analysis-repo_explorer.md`, `evidence/analysis-task_analyst.md`, `evidence/analysis-docs_researcher.md`.

## 1. Ruling

Ship two **constructor-injected** `CodexLandingExecutor` adapters in a **new factory module that is not listed in `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY`**:

- Grok → xAI Chat Completions (`https://api.x.ai/v1/chat/completions`)
- Qwen → DashScope OpenAI-compatible Chat Completions (`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`)

Add `compose_landing_live_grok` / `compose_landing_live_qwen` wrappers that only build those executors and call existing `compose_landing_live`. Freeze the current host as closed `LandingHostRequirementsV1`. Tests use `httpx.MockTransport` only.

Keep every previously frozen L5 bound:

- shipped `server.build_app` stays `UnavailableLandingProvider`, no builder, no executor
- `live_url` stays JSON `null`
- observed landing SHA `80d621545938e24c296420d7f685f2d0b2b5785e` still fails closed
- no `.env` file read, no real TCP in tests, no landing-repo mutation, no publisher
- `httpx==0.28.1` is already a factory dependency; do not add a package

This slice is **library composition**. It is not a live model turn and not a hosted landing.

## 2. Sibling alignment and one conflict

| Sibling | Adopt |
| --- | --- |
| repo_explorer | New module **outside** the FIT exact-path list may import `httpx`. Do **not** import `httpx` from `landing_runtime.py`. Do not reuse `adapters/grok.py`. |
| task_analyst | Default-off, MockTransport-only, closed host pin table, no server auto-wire, no `.env`, no `80d6215` retarget. ACs B–E are the test bar. |
| docs_researcher | Host Python SHA matches the pilot runbook; factory `requires-python >=3.11` stays; env **names** may be documented; no live API was documented as already existing. |

**Conflict (resolved here):** repo_explorer says live HTTP must **not** be folded into `NODE-FACTORY-LANDING-DOGFOOD.repository_paths` (`runtime.network: none`). Drift (`undeclared_source`) still requires the new `.py` to be owned. **Ruling:** add a **separate** `local_component` node that owns only the new module. Do not set the dogfood node’s `runtime.network` to anything other than `none`. Do not add the new module to `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY`.

The l5-live sketch that already listed `landing_live_executors.py` on the dogfood node is **wrong**. Move that path off the dogfood node onto the new node.

## 3. What already exists (do not reopen)

| Layer | Location | Bound |
| --- | --- | --- |
| Live compose | `landing_runtime.py` `compose_landing_live` | enabled `LandingLiveBindingV1` + available `CodexLandingProfile` + injected `CodexLandingExecutor`; coordinator+packager attached |
| Unavailable default | `server.py` `build_app` | `UnavailableLandingProvider`; live compose is injected only |
| Executor protocol | `landing_normalizer.py` | `CodexLandingExecutor.run(CodexExecutionRequest) -> CodexExecutionResult`; stdout = closed draft JSON |
| Profile current-ness | `CodexLandingNormalizer._profile_is_current` | available profile still needs a real executable SHA; HTTP does **not** replace that |
| Source pin | `landing_renderer.py` | `699010380f4f90a0193a9c22090c35e6aded7d2c` / `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4` |
| Result contract | `landing-dogfood.v1.json` Result | `live_url: {type: null}` |
| Factory HTTP lib | `factory/pyproject.toml` | already `httpx==0.28.1`; `requires-python = ">=3.11"` |
| Dogfood no-httpx | `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY` | exact listed `landing_*.py` files cannot import `httpx` |
| Drift ownership | `validate_repository_drift` | every new `.py` must be owned by some node |
| Network fitness | `_network_clients` | owned `import httpx` without `HTTPTransport(uds=...)` is `https` and needs a declared `https` edge from **that owner** |

`factory/adapters/grok.py` is an offline M5 translator (`execution_eligible=False`). Not a landing executor.

## 4. In-tree sketch (align; not done)

l5-live already has uncommitted/WIP:

- `factory/src/adaptive_factory/landing_live_executors.py`
- `compose_landing_live_grok` / `compose_landing_live_qwen` in `landing_runtime.py` (lazy import — keep)
- `factory/tests/test_landing_live_executors.py`
- file claimed on **dogfood** node (move it)
- `.env.example` placeholders (names only — keep)
- `decisions.md` no-httpx split (keep the fact)

Write owner reuses the split, then applies §§5–8. Do not merge the sketch as-is.

Sketch defects to fix:

- `transport=None` currently builds a default `httpx.Client` (real TCP). Forbidden in this slice.
- No `80d6215` wrapper test.
- No boundary AST test.
- `elapsed_ms` hardcoded `25`.
- `follow_redirects` not pinned false.
- Dogfood node owns the HTTP module.

## 5. Host requirements (closed pin)

Frozen dataclass `LandingHostRequirementsV1`. Any instance whose fields do not equal the current pin fails closed (`host_requirements`). Export `CURRENT_LANDING_HOST_REQUIREMENTS` as the only valid value.

| Field | Exact current pin |
| --- | --- |
| `python_executable` | `/usr/bin/python3.12` |
| `python_version_prefix` | `3.12.3` |
| `python_sha256` | `a92f0f95e883390c7256b2e441484aac06b1002dbe1d924141a77c8d82f96223` |
| `factory_requires_python` | `>=3.11` (must equal `factory/pyproject.toml` `requires-python`) |
| `httpx_version` | `0.28.1` |
| `grok_base_url` | `https://api.x.ai/v1` |
| `grok_model_id` | `grok-4` |
| `grok_api_key_env` | `FACTORY_LANDING_GROK_API_KEY` |
| `qwen_base_url` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `qwen_model_id` | `qwen-plus` |
| `qwen_api_key_env` | `FACTORY_LANDING_QWEN_API_KEY` |

Rules:

- Do **not** change package `requires-python` to `==3.12.3`. Package range stays `>=3.11`; the host pin is operator documentation.
- Unit tests assert the **record** equals this table. Do **not** hash live `/usr/bin/python3.12` in unit tests (CI drift). Optional `verify_host_requirements()` is operator-only.
- Do **not** read `.env` or credential files. `api_key_from_environ(name, mapping)` reads only the passed mapping. Compose wrappers and `server.py` must not call it. Module import must not read `os.environ`.
- `.env.example` may list the two env **names** as placeholders.

## 6. Module, node, and fitness

### 6.1 New module (httpx allowed)

`factory/src/adaptive_factory/landing_live_executors.py`

- **Not** in `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY.source_prefixes` (exact list; not a glob).
- **Not** in `NODE-FACTORY-LANDING-DOGFOOD.repository_paths`.
- Owned by a **new** node (drift).

### 6.2 New node (no new service type)

```text
NODE-FACTORY-LANDING-LIVE-EXECUTORS
  type: local_component
  trust_domain: TD-FACTORY-CONTROL
  data_classification: DATA-FACTORY-LANDING-INPUT
  secrets: []
  public_contracts: []
  repository_paths: ["factory/src/adaptive_factory/landing_live_executors.py"]
  runtime.kind: python_process
  runtime.lifecycle: on-demand
  runtime.network: none          # default constructs no client; HTTPS only if a caller injects transport
  runtime.evidence: source_described
```

`local_component` is **not** a `new_service` trigger. Do not add secret classes. `TD-FACTORY-CONTROL` may only hold `SECRET-FACTORY-DATABASE` / `SECRET-FACTORY-TOKEN`; API keys stay constructor arguments.

### 6.3 Edges

Add **three** edges. Reuse existing `NODE-PILOT-MODEL-PROVIDER` (already `external_system` / `TD-EXTERNAL-PLATFORM`). Do not add new external nodes.

| id | from | to | protocol | auth | network_policy | timeout_ms |
| --- | --- | --- | --- | --- | --- | --- |
| `EDGE-FACTORY-LANDING-LIVE-EXECUTORS` | `NODE-FACTORY-LANDING-DOGFOOD` | `NODE-FACTORY-LANDING-LIVE-EXECUTORS` | `python_import` | `local_os` | `no_network` | 5000 |
| `EDGE-FACTORY-LANDING-GROK-MODEL` | `NODE-FACTORY-LANDING-LIVE-EXECUTORS` | `NODE-PILOT-MODEL-PROVIDER` | `https` | `external_managed` | `allowlisted_egress` | 300000 |
| `EDGE-FACTORY-LANDING-QWEN-MODEL` | `NODE-FACTORY-LANDING-LIVE-EXECUTORS` | `NODE-PILOT-MODEL-PROVIDER` | `https` | `external_managed` | `allowlisted_egress` | 300000 |

Shared closed fields: `allowed_data: [DATA-FACTORY-LANDING-INPUT]`, `direction: from_to`, `sync_or_async: synchronous`, `type: control` (python_import edge may be `dependency`), `failure_behavior.mode: fail_closed`, `max_retries: 0`, `terminal_action: reject`, `observable_signal: SIG-FACTORY-CONTROL-FAILURE`, `correlation_id: required`. HTTPS edges: `idempotency: not_required`. python_import edge: `idempotency: required`.

Leave `NODE-FACTORY-LANDING-DOGFOOD.runtime.network` as `none`.

Regenerate `architecture/generated/*.mmd`. Fitness will record `new_edge` + `new_network_client` + `new_trust_crossing` and escalate **post_risk to red**. That does not fail `fitness.status` if `_network_clients` passes. Set change-spec `risk.tier: red` and `approvals.required_scopes: [architecture, security]`. This route did **not** select `security_reviewer`; do not spawn one. Local evidence stays `verification` + `code_review` + `test_review`.

### 6.4 Dogfood files stay httpx-free

Boundary-listed files must not import `httpx` / `requests` / `urllib` / `socket`. Wrappers in `landing_runtime.py` **lazy-import** local factories only:

```text
from .landing_live_executors import grok_landing_executor  # inside compose_landing_live_grok
```

P0 AST test: every boundary-listed `.py` has no `httpx` import; `landing_live_executors.py` **does** import `httpx` and is **not** on that list.

## 7. Executor design

One `OpenAICompatibleLandingExecutor` plus two factories. No Codex CLI. No `subprocess`. No `factory.adapters.grok`.

```text
CodexLandingNormalizer
  → stdin = canonical_json({instruction, request})
OpenAICompatibleLandingExecutor.run
  → POST {base_url}/chat/completions
  → stdout = assistant content UTF-8 (strict draft JSON)
CodexLandingNormalizer._decode_result
  → StaticLandingSpecV1 (existing)
```

### 7.1 Constructor (fail closed)

- `provider_id` in `{grok, qwen}`
- `base_url` starts with `https://` and equals the host-requirements URL
- `model_id` equals the host-requirements model
- `api_key` non-empty after strip; else `credential_unavailable`
- `transport: httpx.BaseTransport` **required** — no `None` default

`grok_landing_executor(api_key=..., transport=...)` / `qwen_landing_executor(...)` fill URL/model from `CURRENT_LANDING_HOST_REQUIREMENTS`.

**No default TCP client.** Tests pass `httpx.MockTransport`. A later operator who wants real HTTPS injects `httpx.HTTPTransport()` **outside** `server.py`. This slice never constructs an unscoped client.

### 7.2 `run()`

1. Reject non-`CodexExecutionRequest` (`executor_request`).
2. Reject `image_bytes is not None` (`executor_request`). This adapter is text-draft only. PDF/audio already stop in the normalizer before `run`.
3. Parse stdin JSON object `{instruction: str, request: object}`.
4. POST:

```json
{
  "model": "<pinned model>",
  "temperature": 0,
  "response_format": {"type": "json_object"},
  "messages": [
    {"role": "system", "content": "<instruction>"},
    {"role": "user", "content": "<canonical JSON of request>"}
  ]
}
```

5. Headers: `Authorization: Bearer <api_key>`, `Content-Type: application/json`. Never put the key in exceptions, logs, results, or argv.
6. `httpx.Client(base_url=..., transport=transport, timeout=request.timeout_seconds, follow_redirects=False, verify=True)` as a context manager. One POST to `/chat/completions`. Zero retries.
7. Status != 200 → `executor_http`. `httpx.HTTPError` → `executor_transport`.
8. `choices[0].message.content` must be a non-empty `str` (not a parts list). No markdown-fence stripping; existing `strict_json_object` is the decoder. Else `executor_result`.
9. UTF-8 encode; if `len(stdout) > request.max_stdout_bytes` → `executor_result`.
10. Return `CodexExecutionResult(stdout, stderr_digest=sha256(b""), exit_code=0, elapsed_ms=<measured 0..timeout_ms>, usage_input_units, usage_output_units)`.
    - Measure elapsed; do not hardcode `25`.
    - Usage from `usage.prompt_tokens` / `usage.completion_tokens` if both are in-range ints; else `0`.
11. Ignore `request.argv`. The dummy Codex executable exists only so `_profile_is_current` can pass.

Do not change `CodexLandingProfile` fields or normalizer `adapter_id="codex-cli"` in this slice.

### 7.3 Wrappers

```text
compose_landing_live_grok(*, api_key, transport, binding, profile, source_repository, scratch_root, output_directory, blobs, store=None, clock=None)
compose_landing_live_qwen(...)
```

Lazy-import factory → `compose_landing_live(...)`. Inherit `80d6215` fail-closed, `live_disabled`, packager attachment, `live_url is None`.

Do **not** auto-compose from env. Do **not** change `server.build_app`.

## 8. Files

**Add / keep**

| Path | Why |
| --- | --- |
| `factory/src/adaptive_factory/landing_live_executors.py` | host pin + Grok/Qwen executors + mapping helper |
| `factory/tests/test_landing_live_executors.py` | MockTransport P0 |

**Touch (minimal)**

| Path | Why |
| --- | --- |
| `factory/src/adaptive_factory/landing_runtime.py` | two wrappers, lazy import only; no `httpx` |
| `architecture/system.yaml` | new node; three edges; **remove** the HTTP module from the dogfood node if the sketch added it |
| `architecture/generated/*.mmd` | regenerate |
| `factory/.env.example` | optional placeholder **names** |
| `factory/README.md` | one sentence after green tests: default-off Grok/Qwen executors; MockTransport in tests; server unavailable; `live_url` null; pin unchanged |

**Do not change**

- `FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY` source list (never add the new module)
- `TARGET_BASE_*`, `DEPLOY_MEMBERS`, `LANDING_WRITE_PATHS`, `RENDERER_VERSION`
- `CodexLandingProfile` field set, draft schema, OpenAPI Result, publisher
- `server.py` composition
- `factory/pyproject.toml` deps
- `pilot/**`, `trust-ci/**`, SQL `001`–`018`, VERSION/ZIP, landing clone
- `.env` files, keys, real network

## 9. Tests (P0)

File: `factory/tests/test_landing_live_executors.py`. Every `run` uses `httpx.MockTransport`. Handler asserts `https`, path `/chat/completions`, pinned model, `Authorization` starts with `Bearer ` — do not echo the secret.

1. Host pin equals §5. Drifted dataclass raises.
2. Missing/blank key → `credential_unavailable`; handler not called.
3. Grok MockTransport → `exit_code=0`, stdout == existing `draft()`.
4. Qwen MockTransport → same for `qwen-plus`.
5. HTTP 500 / `HTTPError` / missing content → `executor_http` / `executor_transport` / `executor_result`.
6. `image_bytes` rejected before POST.
7. `compose_landing_live_grok` + MockTransport + `sealed_target()` → `artifact_ready`, 20 members, zip exists, `live_url is None`.
8. `compose_landing_live_qwen` same.
9. Binding with observed `80d6215` / `a1c2eff3…` raises `source_binding_unimplemented`; handler call count `0`.
10. Disabled binding → `live_disabled`.
11. Boundary AST: listed dogfood sources have no `httpx` import; new module is not on that list and does import `httpx`.
12. New module / wrappers do not open a path named `.env`.
13. Default server path still never constructs these executors (`test_server.py` stays green).
14. No test constructs an executor with `transport=None` and then calls `run` (task_analyst AC-C4).

Do not hit a real URL. Do not point packager at `ai-dark-factory-landing`.

P1: existing `test_landing_live.py`, `test_landing_normalizer.py`, OpenAPI digest, architecture model (landing node path check is a **superset**, so extra files on other nodes are fine).

```bash
python3 -m unittest factory.tests.test_landing_live_executors factory.tests.test_landing_live factory.tests.test_landing_normalizer factory.tests.test_server -v
python3 scripts/grok_verify.py --mode pr
```

## 10. Data flow

Default (unchanged):

```text
server.build_app → UnavailableLandingProvider → provider_unavailable
live_url = null
zero HTTP, zero Git, zero packager
```

Injected (tests / explicit caller):

```text
compose_landing_live_grok|qwen(api_key, MockTransport)
  → compose_landing_live
      → CodexLandingNormalizer
          → OpenAICompatibleLandingExecutor  POST /chat/completions  (mocked)
      → coordinator → packager → artifact_ready, live_url=null
```

## 11. Risks

| Risk | Mitigation |
| --- | --- |
| `transport=None` opens TCP in a unit test | Constructor requires transport. AC-C4. |
| `import httpx` in `landing_runtime.py` | Lazy import of local factories only. AST test. |
| HTTP module left on dogfood node | Drift+honesty. Move to the new node. |
| New module unclaimed | `undeclared_source`. New node owns it. |
| New node without https edges | `_network_clients` fail. Add the two https edges. |
| New secret classes / `.env` read | Forbidden. Constructor key only. |
| SHA-swap to `80d6215` | Forbidden. Test 9. |
| Non-null `live_url` | Frozen OpenAPI. |
| Markdown-wrapped JSON | Fail closed via `strict_json_object`. |
| Bearer in logs | Never interpolate `api_key`. |
| Redirect to `http://` | `follow_redirects=False`. |
| Claiming a live model turn | README: default-off, mocked, server unavailable. |
| Fitness post_risk red | Expected. Do not hide. Do not add an unselected security_reviewer. |
| README K22 graph | New **architecture** node is not a README core node. Do not expand K22. |

## 12. Rollout and rollback

**Rollout**

1. Stack on l5-live `feat/factory-live-auto-landing` (ancestor `fd51dcf` / live-compose commit `22c70c3`), not a stale 2.0.12 tree.
2. Red tests first (MockTransport, host pin, `80d6215`, boundary AST).
3. Module + wrappers + new node + three edges + regenerate diagrams.
4. `python3 scripts/grok_verify.py --mode pr`, then `code_reviewer` + `test_reviewer`.
5. New PR to `main`. Wait for App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the exact head SHA.
6. Do not merge, tag, deploy, enable env keys on the server, or refresh the landing pin.

Absence of these executors at `server.build_app` **is** the flag.

**Rollback**

Revert the successor commit. No migration, no production env, no committed landing artifact.

**Forward recovery**

A later granted slice may pass a real `httpx.HTTPTransport()`, still default-off, still `live_url=null`. A reviewed `80d6215` refresh is a new `LandingLiveBindingV1` digest, not a hex swap.

## 13. Write-owner sequence

1. Read this report + siblings. Align the sketch; do not expand scope.
2. Fill change-package requirements / architecture / test-plan from §§5–9 and task_analyst ACs B–E.
3. Require `transport`; add MockTransport tests including `80d6215` and boundary AST.
4. Keep httpx out of every dogfood-boundary file.
5. New node owns the HTTP module; remove it from the dogfood node; add the three edges; regenerate diagrams.
6. Do not wire `server.py`. Do not read `.env`. Do not touch the landing repository.
7. After green focused tests, one factory README sentence: default-off mocked Grok/Qwen executors; unchanged `live_url` / source pin.

This slice adds **default-off, MockTransport-proven Grok and Qwen Chat Completions adapters** behind the existing live compose seam, with a closed Python 3.12.3 / httpx 0.28.1 host pin. It does not ship a live API call, a hosted URL, or a source-pin refresh.
