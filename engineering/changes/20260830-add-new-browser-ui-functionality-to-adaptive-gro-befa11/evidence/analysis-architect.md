# Architecture analysis — local investor demo dashboard

Route: `befa117340b9`  
Base inspected: `d4cc01fe8d6ec82cce93106191774fc32e8dbb46` (`mvp/investor-ready`)  
Role: read-only `architect`

## Recommendation

Build a read-only, standard-library demo adapter around the existing Python core, served only on loopback and rendered by dependency-free HTML/CSS/ES modules. The single launch command should be:

```bash
python3 scripts/grok_demo.py --open
```

The server must never call the state-writing CLIs, `verify(..., record=True)`, GitHub, Trust CI, a provider, or a shell with browser input. It may call only the existing read/compute functions for route classification, typed-spec summaries, architecture summaries, governance summaries, and a newly extracted pure verification-report summarizer.

This is the smallest coherent design because it demonstrates the real product layers while keeping the browser surface incapable of changing repository state or claiming merge authority.

## Options considered

1. **Recommended: Python standard-library HTTP adapter + static ES modules.** No runtime/build dependency, one command, direct reuse of repository Python functions, easy standard-library integration tests. The trade-off is no portable true-browser E2E runner in the repository.
2. Static HTML with all sample results precomputed. Lowest risk, but it would be a slide, not a product demo: changing the prompt would not exercise routing/spec logic and architecture/governance facts could drift.
3. FastAPI/React/Vite application. Better frontend tooling and typed clients, but adds two dependency systems, a build pipeline, a new packaging boundary, and supply-chain/installer work disproportionate to a local investor demo.

## Existing logic that is safe to reuse

| Dashboard panel | Existing source | Allowed use |
| --- | --- | --- |
| Route | `adaptive_grok.router.build_route()` | Compute a route from a bounded prompt; do not call `set_active_route()` |
| Typed intent | `generate_spec()`, `summarize_spec()`, `criterion_coverage()` | Generate a clearly labelled draft for an entered prompt, or summarize the bundled complete sample spec |
| Architecture | `load_architecture()`, `architecture_digests()`, `contract_inventory()` | Read the canonical repository model and expose only allowlisted counts/digests |
| Governance | `load_governance()`, `governance_summary()` | Read canonical registries at a server-supplied UTC time and expose only summary fields |
| Verification | existing `CheckResult`/report shape | Extract a pure `summarize_verification_report(report)` and apply it to a bounded bundled report; never run the full verifier from an HTTP request |

`scripts/grok_route.py` is not reusable as an API because its normal task path writes `.grok-stack/runtime/active-route.json`. `scripts/grok_verify.py` is also not an API because it runs processes and records a receipt by default. The dashboard must import pure functions, not invoke CLIs through subprocesses.

## Component and file boundaries

```text
browser (untrusted prompt, no credentials)
  -> same-origin loopback HTTP
demo_http.py (protocol, bounds, security headers, error mapping)
  -> demo.py (read-only application service and response projection)
  -> router/spec/architecture/governance/verification pure logic
  -> canonical repository files + bundled demo fixtures (read-only)
```

Recommended file ownership:

- `.grok-stack/adaptive_grok/demo.py`: pure `build_sample_snapshot(root, now)` and `build_prompt_preview(root, prompt, now)` orchestration; strict allowlisted projections only.
- `.grok-stack/adaptive_grok/demo_http.py`: `HTTPServer`/`BaseHTTPRequestHandler`, route dispatch, byte limits, Host/Origin checks, content types, security headers, and stable errors. Keep it free of product decisions.
- `.grok-stack/demo/index.html`: semantic application shell.
- `.grok-stack/demo/assets/app.css`: responsive visual system with reduced-motion and high-contrast/focus treatment.
- `.grok-stack/demo/assets/api.js`: same-origin fetch, timeout, typed error normalization.
- `.grok-stack/demo/assets/render.js`: DOM rendering through `textContent`/attribute allowlists only.
- `.grok-stack/demo/assets/app.js`: state machine for load, preview, stale/offline, retry, and focus management.
- `.grok-stack/demo/sample/task.json`, `change-spec.json`, `verification-report.json`: bounded non-secret fixtures. The fixture report must state that it is sample evidence, not a live verdict.
- `scripts/grok_demo.py`: argument parsing, root discovery, bind/start, optional `webbrowser.open()`; no application logic.
- `engineering/contracts/openapi/adaptive-demo.v1.json`: frozen version-1 local API.
- `tests/test_demo.py`: pure service, fixture, projection, and no-mutation tests.
- `tests/test_demo_http.py`: ephemeral-port HTTP integration and security tests.

Because `.grok-stack` is already a managed installer directory, assets and sample data placed there travel together. `scripts/grok_demo.py` must be added to installer/managed inventory tests. Do not add a root `pyproject.toml`, `requirements.txt`, `package.json`, or generated frontend bundle.

## Snapshot semantics and honesty

The landing snapshot should combine:

- a bundled example prompt, complete sample spec, and sample verification report;
- live read-only summaries of this checkout's architecture and governance;
- a route computed by the actual router from the sample prompt.

Every section carries `source`: `bundled_sample`, `computed_preview`, or `live_repository`. The UI must never blend these into one implied live CI result.

For a user-entered prompt, the server runs real routing and draft-spec generation. Since `generate_spec()` intentionally emits `UNKNOWN` outcome fields and no acceptance criteria, the preview must display `draft / design required`; it must not reuse the sample's green verification status. Its verification section is exactly `not_run`.

## HTTP contract v1

Only these routes exist:

| Method/path | Purpose | Result |
| --- | --- | --- |
| `GET /` and allowlisted `/assets/*` | Static dashboard | Exact bundled files; no arbitrary path joining or directory listing |
| `GET /api/v1/health` | Liveness/readiness summary | `200` with section readiness, or `503` when a base snapshot cannot be built |
| `GET /api/v1/snapshot` | Initial investor sample | Read-only sample/live composite |
| `POST /api/v1/preview` | Route/spec preview for one prompt | Read-only computed preview; `verification.status=not_run` |

Preview request, closed to unknown fields:

```json
{
  "schema_version": 1,
  "prompt": "Add a responsive browser dashboard for local verification evidence"
}
```

Require UTF-8 `application/json`, declared body length no greater than 16 KiB, prompt length `1..4000`, no control characters, and header `X-Adaptive-Demo: 1`. Do not accept file paths, repository roots, commands, URLs, profiles, session IDs, or output selectors from the browser.

Successful response projection:

```json
{
  "schema_version": 1,
  "request_id": "random opaque id",
  "generated_at": "RFC3339 UTC",
  "mode": "bundled_sample",
  "external_writes": false,
  "route": {
    "intent": "feature",
    "risk": "medium",
    "complexity": "standard",
    "domains": ["frontend"],
    "workflow_skills": ["adaptive-delivery", "feature-workflow", "frontend-change"],
    "analysis_agents": [],
    "write_agent": "frontend_implementer",
    "review_agents": ["code_reviewer", "test_reviewer"],
    "quality_profiles": ["base", "frontend"],
    "human_gates": []
  },
  "spec": {
    "source": "bundled_sample",
    "status": "complete",
    "digest": "sha256",
    "criterion_total": 4,
    "criterion_mapped": 4,
    "invariant_total": 3,
    "forbidden_total": 3
  },
  "architecture": {
    "source": "live_repository",
    "status": "pass",
    "architecture_id": "ARCH-ADAPTIVE-GROK-M2",
    "digest": "sha256",
    "node_count": 14,
    "edge_count": 14,
    "contract_count": 5,
    "trust_domain_count": 7
  },
  "governance": {
    "source": "live_repository",
    "status": "pass",
    "digest": "sha256",
    "active_rule_count": 0,
    "open_debt_count": 0,
    "finding_count": 0
  },
  "verification": {
    "source": "bundled_sample",
    "status": "pass",
    "pass": 6,
    "fail": 0,
    "skip": 1,
    "checks": []
  }
}
```

The exact counts above illustrate shape, not frozen fixture values. Responses should omit raw accepted prompt bodies, absolute paths, Git remotes, environment, raw findings, stdout/stderr, route fingerprints, Trust CI material, and runtime state.

Error response for every API failure:

```json
{
  "schema_version": 1,
  "request_id": "random opaque id",
  "error": {
    "code": "invalid_prompt",
    "message": "Prompt must contain 1 to 4000 characters.",
    "retryable": false
  }
}
```

Stable codes: `invalid_json` (400), `forbidden_request` (403), `not_found` (404), `method_not_allowed` (405), `payload_too_large` (413), `invalid_prompt` (422), `snapshot_unavailable` (503), and generic `internal_error` (500). Internal exceptions are logged only as bounded class/code, not returned with traceback or paths.

## Trust boundaries and security requirements

- Bind exactly `127.0.0.1` by default; do not support non-loopback bind in this slice. Tests use `--port 0`; normal default may be `8765`.
- This local, read-only surface does not need a bearer secret, but loopback alone is not sufficient: validate `Host` against the actual loopback host/port to resist DNS rebinding, reject cross-origin `Origin`, emit no CORS headers, require JSON plus `X-Adaptive-Demo: 1` on POST, and use same-origin `fetch`.
- Use single-process bounded request handling (plain `HTTPServer` is sufficient) so a browser cannot create an unbounded thread/process fan-out. Add a client timeout in JS and deterministic server body limits.
- Static routing is a literal URL-to-resource allowlist. Reject encoded traversal, backslashes, NULs, query-driven filenames, dot segments, and directories.
- Send `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'`, plus `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and `Cache-Control: no-store`.
- Render all dynamic values with `textContent`; never use `innerHTML`, `insertAdjacentHTML`, `eval`, remote fonts, CDN assets, template strings inserted as markup, or URL construction from response values.
- Browser input may reach `build_route()` only as a Python string. It must never become a shell argument, path, import name, environment key/value, URL, Git ref, or log line.
- The service reads only fixed canonical files needed by the imported repository logic and fixed sample resources. It must not read `.env`, runtime credentials, private keys, Trust CI runtime files, arbitrary change packages, or files named by a request.
- Add a regression test that snapshots repository/runtime file identities before and after GET/POST requests and proves there are no writes. Also patch subprocess/state writers in unit tests so any attempted command or `set_active_route`/receipt call fails.
- The architecture model must add distinct local browser and demo-server nodes, an authenticated-by-same-origin loopback HTTP edge, a read-only dependency edge into local preflight logic, and the OpenAPI contract. There must be no edge to GitHub, Trust CI database/keys, production trust, provider execution, or deployment.

## Browser experience and states

Use a single-page dashboard with semantic HTML: skip link, header/status badge, prompt form, route pipeline, four evidence cards (typed intent, architecture, governance, verification), and a compact trust-boundary statement. On wide screens use a two-column evidence grid; below roughly 760 px stack all content without horizontal scrolling.

Required states:

- **Loading:** stable skeleton/`aria-busy=true`; no layout jump.
- **Sample ready:** explicit `Sample evidence` and `Live repository model` source chips.
- **Previewing:** disable only the submit button, preserve prompt, announce progress in a polite live region.
- **Prompt validation error:** inline message linked with `aria-describedby`; focus remains on prompt.
- **Section degraded:** keep successful cards and show a retryable error inside only the failed architecture/governance card.
- **Offline/server stopped:** keep the last successful snapshot in memory, label it `Stale — local server unavailable`, show Retry, and never present it as current. If no snapshot was loaded, show a full recoverable offline state with the launch command.
- **Empty:** the text area may be empty before interaction; submission is rejected locally and server-side.
- **Reduced motion/high contrast:** obey `prefers-reduced-motion`; do not encode pass/fail by color alone.
- **Keyboard:** logical heading order, visible focus, Enter/Ctrl+Enter behavior documented, focus the result heading after success only when initiated by the user.

Do not add a service worker or persistent browser storage. Both create cache/staleness/privacy behavior that the demo does not need. In-memory last-good state is enough.

## Failure handling

- Asset or root discovery failure: fail startup with one concise message before listening.
- Architecture/governance read failure: return a successful composite with that section `unavailable` when route/spec remain usable; health readiness is degraded. Never substitute zeros.
- Invalid bundled fixture: fail startup; a knowingly inconsistent investor snapshot is worse than no demo.
- Route/spec computation failure: return `422` for typed input rejection or generic `500`; keep the previous UI snapshot.
- Client timeout/network error: enter stale/offline mode and provide Retry; no automatic retry storm.
- Port occupied: exit with a clear `--port` suggestion; do not probe/bind another network interface.

## Test strategy

### P0 automated

1. Pure service tests prove the sample snapshot is deterministic apart from injected time/request ID, sources are labelled, preview uses real `build_route()`/`generate_spec()`, and preview verification is `not_run`.
2. Fixture tests parse with strict duplicate-key/size handling, validate the sample spec through existing schema logic, and reject raw secrets/absolute paths/unknown status values in the sample verification report.
3. HTTP tests start the server on `127.0.0.1:0` and verify every method/path/status/content type, response shape, request size, closed JSON fields, UTF-8 errors, Host/Origin rejection, absent CORS, and all security headers.
4. Traversal tests cover raw/encoded `..`, doubled separators, backslashes, NUL, unknown assets, query filename tricks, and directory listing.
5. No-mutation tests fail on `set_active_route`, `update_route`, `write_receipt`, subprocess execution from request input, or any changed file under `.grok-stack/runtime`; GET and POST leave the repository fingerprint unchanged.
6. Projection/XSS tests submit strings such as `<img onerror=...>` and assert the JSON preserves data while the renderer has no HTML sink. A static test should reject `innerHTML`, `insertAdjacentHTML`, `eval`, remote `http(s)` asset URLs, and inline script/style.
7. Architecture fitness/contract tests validate the new OpenAPI file, declared nodes/edges, diagrams, installer payload, and absence of Trust CI/external-write edges.

### P1 frontend evidence

- Python structural tests ensure every JS-referenced DOM ID exists, form labels/live regions are wired, viewport and language are present, and the stylesheet includes reduced-motion/focus rules.
- If an already-installed browser runner is available, use it only as an optional evidence command; do not add Playwright/npm as a product dependency. Capture 360 px and 1440 px screenshots, keyboard submission, API error, and stopped-server stale state.
- The zero-dependency requirement means a portable true-browser E2E test cannot be guaranteed. This limitation must be stated rather than claiming HTTP tests are browser E2E.

Focused test commands should remain standard-library based, followed once by the route-required full verifier:

```bash
python3 -m unittest tests.test_demo tests.test_demo_http -v
python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness tests.test_installer tests.test_structure -v
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py diagram --check --json
python3 scripts/grok_verify.py --mode pr
```

## Acceptance criteria for the implementer

1. One documented command starts a responsive dashboard on loopback with no dependency installation or build step.
2. Initial sample and entered prompt exercise actual route/spec logic; architecture/governance summaries are derived read-only from canonical repository logic; verification is explicitly sample or not-run.
3. No HTTP action mutates repository/runtime state, executes a verifier, shells out with request content, reads secrets, or performs an external request/write.
4. API v1 is closed, bounded, same-origin, versioned in OpenAPI, and covered by HTTP/security tests.
5. Loading, degraded, validation, and offline/stale states are accessible and responsive; dynamic text has no HTML execution sink.
6. Architecture/installer/docs are updated consistently; no root packaging marker or JS dependency tree is introduced.
7. Existing verification and independent code/test reviews pass on the final fingerprint.

## Design-gate note

The approved scope should explicitly choose this read-only standard-library option and accept the stated no-portable-browser-E2E limitation. If the requirement instead demands rich charts, persistent history, live verifier execution, remote access, authentication, or guaranteed automated browser E2E, that is a larger subsystem and needs a revised design and dependency/security decision before implementation.
