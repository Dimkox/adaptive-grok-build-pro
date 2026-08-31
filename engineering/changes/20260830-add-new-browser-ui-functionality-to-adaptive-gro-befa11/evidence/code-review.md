# Code review — investor-ready local product MVP

## Verdict

**PASS**

No Critical or Important correctness, security, maintainability, packaging, API/client, or investor-truthfulness issue remains in the reviewed local-demo scope.

## Inspected identity and diff state

- Route: `befa117340b9`; selected role: `code_reviewer`; approved base: `2cf89e40e5c3f33cddf87eecd7956ecf4a201df3`.
- Git HEAD at review: `2cf89e40e5c3f33cddf87eecd7956ecf4a201df3`; the implementation was an uncommitted worktree delta from that approved base.
- Inspected pre-report tree fingerprint: `18938996520573fdc032ded1401f340e363f71bd0789f4a28c7cc624f572fbfb`. Replacing this report is the only change made by the reviewer after that fingerprint was captured.
- Inspected 33 changed product/evidence paths reported by `changed_files`, including the router and verification extensions, complete demo service/HTTP/UI/fixture tree, launcher, OpenAPI contract, installer/package/version/docs integration, tests, and route evidence.
- Local package at review: `dist/adaptive-grok-build-pro-v2.1.0.zip`, SHA-256 `5969f951e416f2fb93b3d453267a91efded59ce109058b79b8ebf765ee89cec6`, matching its adjacent checksum file.

## Prior Important findings and remediation

### Resolved — demo initialization invoked Git subprocesses

The pre-remediation application constructed route metadata through `git_default_base()` and `tree_fingerprint()`, contradicting the documented no-Git/no-shell demo boundary. The implementation now uses explicit fixed, non-authoritative `DEMO_ROUTE_METADATA` solely as the deterministic route seed; the normal `build_route` defaults remain unchanged for non-demo callers. Neither `demo.py` nor the HTTP handler imports or invokes the Git helpers.

The regression test patches `subprocess.run` before both `DemoApplication` and `create_server` construction, then separately guards request handling and runtime state. Both paths pass, so the earlier test blind spot is closed.

### Resolved — alternate scenario falsely claimed low risk

The bundled alternate is now a real documentation-review prompt. The server computes its route with the same repository router and publishes both the route projection and a label derived from the computed intent/risk/write owner. Direct re-execution produced `intent=review`, `risk=medium`, `domains=[api]`, `write_agent=None`; the visible label is `Use contrasting review route · medium risk · no write owner`.

The neutral pre-load UI, dynamic client assignment, investor guide, and regression assertions agree with those values and contain no fabricated low-risk claim.

## Security, correctness, and truthfulness assessment

- The server binds only `127.0.0.1`, serves a literal asset allowlist, rejects hostile Host/Origin, emits no CORS permission, requires the demo header for preview POST, bounds body and prompt sizes, rejects duplicate/unknown JSON fields and unsupported methods, and returns stable safe errors with security/no-store headers.
- Browser-controlled text reaches only in-memory router/spec preview logic. It cannot select a filesystem path, command, URL, repository root, Git ref, credential, destination, approval, release, or deployment action.
- Dynamic UI content is rendered through `textContent`; there are no inline/remote scripts, unsafe HTML sinks, browser persistence, service worker, or external resource URL.
- Sample verification is strictly validated and labelled `bundled_sample`; entered prompts receive `computed_preview` and verification `not_run`. The UI and docs explicitly deny merge authority, live Trust CI verdicts, approval, publication, and deployment.
- Architecture and governance use canonical read-only loaders with bounded partial-degradation responses. The normal router remains backward compatible because its new overrides are optional and preserve the existing default behavior.
- Installer and archive inventories include the launcher, engine, assets, fixtures, contract, and guide without adding a root package marker, JavaScript dependency tree, database, provider adapter, background service, or GitHub Actions workflow.

## Verification reproduced by this reviewer

- `python3 -m unittest tests.test_demo tests.test_demo_http tests.test_installer tests.test_manifest_package tests.test_structure -q`: **67 tests passed**.
- The focused remediated demo/API portion within that run: **20 tests passed**, including both prior-finding regressions.
- `git diff --check 2cf89e40e5c3f33cddf87eecd7956ecf4a201df3`: passed.
- Direct alternate-route comparison and archive/checksum comparison: passed.

## Severity-classified residual findings

### Critical

None.

### Important

None.

### Minor

1. The UI assurance is portable structural/HTTP integration rather than a real browser screenshot/E2E run. This matches the approved test plan, but a future Playwright smoke test would improve visual-regression confidence.
2. The OpenAPI document freezes the path/method/request boundary but does not fully schema every success response. This is adequate for the bundled same-repository client; add response-schema conformance before supporting independent API consumers.
3. `HTTPServer` is intentionally single-process and local-only. If the surface ever becomes remote or long-lived, adopt connection/read timeouts and a hardened production server before exposure.

## Completion boundary

This PASS supports the local investor-demo product scope only. It is not merge, release, deployment, production mutation, signed approval, or App-owned exact-SHA Trust CI evidence.
