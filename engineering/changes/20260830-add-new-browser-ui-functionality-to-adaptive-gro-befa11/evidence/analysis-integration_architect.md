# Integration architecture analysis — local investor demo

Route: `befa117340b9`

Inspected head: `d4cc01fe8d6ec82cce93106191774fc32e8dbb46` (`mvp/investor-ready`)

Scope: read-only local HTTP demo; no external write or live Trust CI operation.

## Contract freeze: local HTTP API v1

The demo API is a same-origin, loopback-only, versioned read interface. Freeze the initial surface at the following operations; do not expose a generic file, command, repository-root, session, profile, or verification endpoint.

| Method/path | Consumer | Source of truth | Success | Failure contract |
| --- | --- | --- | --- | --- |
| `GET /` | Browser navigation | bundled fixed HTML | `200 text/html` | fixed allowlist only |
| `GET /assets/{name}` | browser modules/styles | bundled fixed assets | `200` with fixed MIME | `404` for every non-allowlisted name |
| `GET /api/v1/health` | startup/readiness UI | bounded demo service | `200` ready/degraded, `503` unavailable | typed error envelope |
| `GET /api/v1/snapshot` | initial dashboard | bundled scenario + live read-only projections | `200` | `503 snapshot_unavailable` |
| `POST /api/v1/preview` | prompt form | actual router plus draft spec adapter | `200` | `400`, `403`, `413`, `415`, `422` typed envelope |

`POST /api/v1/preview` accepts precisely this UTF-8 JSON object, with `Content-Type: application/json`, `X-Adaptive-Demo: 1`, no unknown keys, maximum body 16 KiB, and a `prompt` of 1–4000 non-control characters:

```json
{
  "schema_version": 1,
  "prompt": "Add a responsive browser dashboard for local verification evidence"
}
```

All JSON responses must contain `schema_version: 1`, opaque `request_id`, RFC3339 UTC `generated_at`, `external_writes: false`, bounded provenance for each panel, and no absolute paths, environment values, raw command output, repository fingerprint, remote, credentials, keys, stack traces, or private reasoning. Use one stable error shape:

```json
{
  "schema_version": 1,
  "request_id": "opaque-id",
  "error": {"code": "invalid_prompt", "message": "Prompt must contain 1 to 4000 characters.", "retryable": false}
}
```

Reserve these codes: `invalid_json` (400), `forbidden_request` (403), `not_found` (404), `method_not_allowed` (405), `payload_too_large` (413), `unsupported_media_type` (415), `invalid_prompt` (422), `snapshot_unavailable` (503), and `internal_error` (500). `Allow` is required on 405. Unsupported `/api/v2/*` is a 404, not an alias to v1. Add the frozen document as `engineering/contracts/openapi/adaptive-demo.v1.json`, register it as an architecture contract at version `1` with compatibility `exact`; an incompatible evolution is a parallel version, never a changed v1 meaning.

## Engine-to-consumer map

| Dashboard concern | Safe pure/read-only use | Browser-facing projection | Explicitly excluded |
| --- | --- | --- | --- |
| Route | `router.build_route(root, prompt, session_id).to_dict()` | intent, risk, complexity, domains, workflow/agent/evidence lists and gate names | `scripts/grok_route.py`, `set_active_route`, active-route persistence; server chooses a fixed non-sensitive session ID |
| Typed spec | `spec.load_spec`, `validate_spec(..., gate=False)`, `summarize_spec`, `criterion_coverage`, `canonical_spec_digest` on fixed sample; `generate_spec(route)` for preview | labelled `complete` sample or `draft / design required` preview, summary/counts/digest/findings | `grok_spec generate`, `spec_fingerprint` (runs Git), caller-selected sample paths |
| Architecture | `load_architecture`, `validate_architecture`, `architecture_digests`, `contract_inventory` and digest | validation status, counts and canonical digests only | diagram write/check workflow, Git diff/fitness, caller-selected paths |
| Governance | `load_governance`, `governance_summary(snapshot, now=fixed/injected aware UTC)` | status, digest, bounded rule/debt/findings counts | lifecycle/project/handoff operations, raw registries and Markdown views presented as authority |
| Verification | a newly extracted, pure parser/projection over a fixed bounded sample report | sample checks, pass/fail/skip counts, freshness, criterion coverage and binding status | `verification.verify()` in any mode, `grok_verify`, `write_receipt`, process execution or current merge verdict |

The adapter imports these functions after adding `<root>/.grok-stack` to `sys.path`, as current CLIs do. It must call functions directly; browser input must never become a shell argument, filesystem path, URL, import target, Git ref, environment value, or log payload. `verification.verify(record=False)` is still unsuitable because it executes tools and may create `.coverage`; extract/introduce only a pure summary over an explicitly sample-labelled fixture.

## Boundary and security controls

```text
untrusted browser
  -> same-origin HTTP on 127.0.0.1 only
  -> HTTP adapter (bounds, headers, static allowlist, error mapping)
  -> read-only demo service
  -> fixed sample fixtures + repository router/spec/architecture/governance readers
```

- Bind only `127.0.0.1`; permit `--port 0` for tests and an explicit unprivileged port for users. Do not add a non-loopback bind option in v1.
- Reject an unexpected `Host` (except the server's exact loopback host/port) and cross-origin `Origin`; emit no CORS header. The custom POST header is an additional CSRF/cross-origin guard, not authentication.
- Use a single bounded stdlib server. Enforce header/body limits before JSON parsing; reject malformed UTF-8, duplicate/unknown JSON keys and control characters.
- Static URL routing is literal and query-independent. Reject dot segments (including encoded), backslashes, NULs, directories and unrecognized assets; do not path-join request input.
- Send `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and `Cache-Control: no-store` (at least for API responses). No remote assets, fonts, network client, service worker, browser persistence or file upload.
- The renderer uses `textContent`/attribute allowlists only—never `innerHTML`, `insertAdjacentHTML`, `eval`, inline event handlers or dynamically constructed markup. Preserve last-good data only in memory and label it stale after a failed request.
- Treat bundled verification data as `sample evidence`, never as current `verified`, merge eligible, or the App-owned exact-SHA Trust CI check. A preview response has `verification.status: not_run`.

## Packaging and installation integration

1. Put engine, fixed fixtures, and static assets below `.grok-stack/`: it is already a managed installer directory and `manifest.included_files()` packages regular, non-secret files there while excluding runtime state. Do not add root `package.json`, `pyproject.toml`, `requirements.txt`, or a frontend build output: the root intentionally has no packaging marker and repository routing/verifier behavior depends on that.
2. Add the launch entrypoint (`scripts/grok_demo.py`) to `scripts/install_into.py::MANAGED_FILES`; `.grok-stack` contents are copied automatically. Register the OpenAPI contract in `MANAGED_FILES` too, otherwise a materialized target contains empty contract directories but lacks the declared local API contract.
3. Packaging remains deterministic through `scripts/package_stack.py`; add assertions that the archive includes the launch script, local assets/fixtures, and OpenAPI v1, while still excluding `.grok-stack/runtime/*` (apart from `.gitkeep`), secrets, archives/checksums, and `.github/workflows/`.
4. A freshly materialized target intentionally lacks target-owned architecture authority and governance registries. The demo therefore must either operate in a documented `not_configured`/sample-only mode there, or its command must say the live architecture/governance sections require an adopted consumer repository. It must not copy this repository's `architecture/{system,rules,adoption}.json` or canonical governance files to make the dashboard appear live.
5. Add `scripts/grok_demo.py`, its local OpenAPI contract, user command, exact URL, shutdown/troubleshooting, offline guarantee, and sample-data/Trust-CI disclaimer to README. Preserve README's complete current-state stack graph. No release/package publication is in scope.

## Architecture, compatibility, and rollout

The existing architecture assigns `.grok-stack/adaptive_grok` to `NODE-LOCAL-ROUTE-POLICY`; the HTTP trust boundary is new and must be described rather than implicitly folded into the existing node. Add separate local browser and local demo-server nodes plus an `openapi` contract and edges from browser to server (same-origin loopback HTTP) and server to fixed repository inputs (read-only/no-network). Add rules that prohibit demo-server edges to GitHub, Trust CI, Docker, provider execution, deployment, runtime credentials, receipt writes, and external networking. Regenerate/check all five architecture diagrams.

V1 has no authentication because it is loopback-only and read-only. It is still a public local API from the browser's perspective, so closed schemas, Host/Origin validation, strict method/path routing, source-labeled provenance, and fail-closed error handling are mandatory. Any later remote exposure, live verification, history, authentication, or write action is a new security design/versioned API decision—not an extension of this demo.

Rollout is additive and locally reversible: ship behind an explicit `grok_demo.py` command; normal hooks/CLIs do not start it. Roll back by not launching/removing the new additive files in a forward-fix PR. A server failure stops only the demo; it must not alter routes, receipts, governance, verification, Git state, or Trust CI.

## Focused contract and end-to-end evidence

| Priority | Test | Expected assertion |
| --- | --- | --- |
| P0 | Adapter equivalence | fixed sample snapshot and preview projections equal direct router/spec/architecture/governance calls after normalizing injected time/request ID; preview verification is `not_run` |
| P0 | HTTP contract | ephemeral `127.0.0.1:0` server verifies every v1 operation, content type, closed response/request schema, 404/405/`Allow`, 413/415/422 and v2 rejection |
| P0 | Request/asset safety | reject oversized/invalid JSON, unknown fields, hostile prompt, bad Host/Origin, encoded traversal, backslashes, NULs, directory/query asset tricks; no CORS and all required security headers |
| P0 | No-write/no-exec | snapshot file identities/tree fingerprint around GET and POST are unchanged; patched subprocess, `set_active_route`, route/state writers, receipt writers and network clients fail if called |
| P0 | Fail-closed data | corrupt/malformed sample spec or evidence causes a bounded non-green/unavailable response; altered architecture/governance fixture returns its real validation finding, never zeros/green |
| P0 | Packaging/installer | deterministic ZIP contains demo payload; materialized target contains the runnable command and assets/contract, excludes runtime/secrets/GitHub Actions and target-owned authority |
| P1 | Browser critical path | load → select/submit scenario → inspect all panels → induce a safe validation error → retry; keyboard/focus/live-region checks at 320, 768, 1024 and 1440 px, with reduced motion and no horizontal scroll |
| P1 | Static accessibility/XSS | DOM IDs/labels/landmarks and focus styles exist; JS has no HTML/eval sinks or remote URL; dynamic hostile text is rendered as text |

The repository has no configured Node/browser runner. Keep portable automated coverage as stdlib unit/HTTP tests, and record optional installed-browser screenshots/keyboard evidence separately. Do not claim those HTTP tests are browser E2E and do not introduce a root Node marker solely to obtain Playwright/Cypress.

## Gate conditions before implementation

1. Populate the typed change spec: it currently contains no criteria, invariants, forbidden outcomes, contracts, observability, or real success metric, so it cannot support a release/PR gate.
2. Obtain the route's required `scope_and_design_approval` for this local-only standard-library design and its no-portable-browser-runner limitation.
3. Rebind/reroute the recorded base before final verification: route base `1c062998...` is not the inspected branch baseline/head `d4cc01fe...`; otherwise PR comparison evidence can include unrelated work.
