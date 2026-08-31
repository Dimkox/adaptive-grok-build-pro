# Repository analysis — investor-ready local browser demo

Route: `befa117340b9`  
Inspected branch/head: `mvp/investor-ready` at `d4cc01fe8d6ec82cce93106191774fc32e8dbb46`

## Existing read-only product APIs the demo can call

| Dashboard stage | Stable repository API | Safe use in the HTTP request path | Notes |
| --- | --- | --- | --- |
| Routing | `.grok-stack/adaptive_grok/router.py::build_route(root, prompt, session_id) -> Route`, then `Route.to_dict()` | Yes | Reads repository/config and computes a tree fingerprint; unlike `scripts/grok_route.py`, it does not persist an active route. Bound prompt length in the demo before calling it. Existing regression surface: `tests/test_repo_router.py`. |
| Typed intent | `.grok-stack/adaptive_grok/spec.py::{generate_spec, load_spec, validate_spec, summarize_spec, criterion_coverage, canonical_spec_digest}` | Yes, with in-memory/bundled data | `generate_spec()` deliberately creates a draft v2 spec with `UNKNOWN` metric/target and no criteria. For a green investor story, feed a complete bundled v2 sample to `validate_spec()` and use `summarize_spec()`; label generated output as draft rather than implying gate approval. Existing tests: `tests/test_change_spec.py`. |
| Architecture | `.grok-stack/adaptive_grok/architecture.py::{load_architecture, validate_architecture, architecture_digests, contract_inventory, contract_inventory_digest}` | Yes | These are bounded, no-follow repository reads and pure projections. Do not use diagram generation in a request. Existing tests: `tests/test_architecture_model.py`, `tests/test_architecture_fitness.py`. |
| Governance | `.grok-stack/adaptive_grok/governance.py::{load_governance, governance_summary}` with an aware UTC `datetime` | Yes | Loads the frozen canonical governance schemas/registries, revalidates evidence and returns active/candidate rules, debt, findings and digests without mutation. Do not call `project` or any lifecycle transition. Existing tests: `tests/test_governance.py`, `tests/test_governance_fitness.py`. |
| Verification display | `verification.CheckResult.to_dict()` and the report shape returned by `verification.verify()` | Only the data shape is safe | There is no public pure `summarize_verification(report)` API. `verify(record=False)` still launches Git/tests/linters and PR mode may create `.coverage`; `record=True` also writes a receipt. The web request must not call it. Add a small pure public summarizer over a bundled bounded sample report (or display a bundled report directly), and keep actual `grok_verify` a separate developer/release command. Existing regression surface: `tests/test_verification_doctor.py` and `tests/test_change_receipts.py`. |

The server should import the engine exactly as existing scripts do: resolve the repository root, prepend `<root>/.grok-stack` to `sys.path`, and import `adaptive_grok.*`. It must call Python functions directly, not shell out to `scripts/grok_*.py`; several CLIs intentionally persist routes, specs, receipts, or projections.

## Smallest coherent source boundary

No browser application exists today; the root has neither `package.json` nor a Python packaging marker. The least disruptive boundary is a stdlib Python/vanilla HTML-CSS-JS demo, for example:

- `scripts/grok_demo.py` — one-command localhost entrypoint;
- `.grok-stack/adaptive_grok/demo.py` — bounded read-only aggregation and pure verification-summary adapter;
- `.grok-stack/adaptive_grok/demo_assets/index.html`, `app.css`, `app.js`, and bounded sample JSON;
- `engineering/contracts/openapi/investor-demo.v1.json` — only local read endpoints and one bounded in-memory analysis endpoint;
- `tests/test_demo.py` — focused HTTP/pipeline/accessibility contract tests.

Keeping code/assets below `.grok-stack` reuses the current managed installer root. Adding a root `package.json` is not a neutral frontend choice: `repo.detect_repo()` would permanently classify this repository as frontend/polyglot and the root verifier would start invoking npm scripts. Adding root `pyproject.toml`, `requirements.txt`, or `setup.py` is explicitly forbidden by `tests/test_structure.py::test_root_has_no_packaging_marker` and README policy.

Recommended local HTTP boundary:

- default bind `127.0.0.1`, random/explicit unprivileged port; never `0.0.0.0`;
- allowlisted routes and methods, bounded prompt/body, strict JSON keys, no caller-supplied filesystem path/session command;
- Host/Origin checks, CSP and other basic security headers, `Cache-Control: no-store` for JSON;
- no subprocess, network client, connector, runtime receipt write, file upload, browser persistence, or external asset/CDN/font dependency;
- semantic HTML, keyboard navigation/focus, contrast, reduced-motion behavior, and responsive normal/loading/empty/error/offline states.

## Architecture, installer, and package constraints

1. `architecture/system.yaml` currently assigns `.grok-stack/adaptive_grok` to `NODE-LOCAL-ROUTE-POLICY` and `scripts/tests` to `NODE-LOCAL-VERIFIER`. New engine code under that existing path is owned, but the HTTP surface, OpenAPI contract and browser trust boundary still need explicit M2 nodes/contracts/edges, rule updates, and five regenerated diagrams. Required files: `architecture/system.yaml`, `architecture/rules.yaml`, `architecture/generated/{context,container,data-flow,deployment,trust-boundary}.mmd`, `tests/test_architecture_model.py`, and `tests/test_architecture_fitness.py`. Model only browser -> localhost demo and demo -> read-only local authorities; no Trust CI, GitHub, provider, production, or publication edge.
2. Release ZIP packaging is broad: `.grok-stack/adaptive_grok/manifest.py::included_files()` automatically includes new non-secret demo sources/assets/contracts, and `scripts/package_stack.py` produces the deterministic ZIP. Add explicit assertions to `tests/test_manifest_package.py` for demo assets/contract and continued runtime/secret/GitHub-Actions exclusion.
3. Target installation is narrow: `scripts/install_into.py` copies `MANAGED_DIRS=(.grok,.agents,.grok-stack)` plus explicit `MANAGED_FILES`. Assets/engine under `.grok-stack` already flow into a new target, but `scripts/grok_demo.py` and `engineering/contracts/openapi/investor-demo.v1.json` will not unless added to `MANAGED_FILES`; mirror the script in `.grok-stack/config/managed.json`. Update `tests/test_installer.py` to prove a packaged new-target install can run the demo while still not creating target-owned `architecture/system.yaml`, `architecture/rules.yaml`, `architecture/adoption.json`, or governance registries.
4. All `.grok-stack/**`, `scripts/grok_*.py`, installer/package scripts, README/version files and `tests/test_*.py` are protected/control-plane paths in `.grok-stack/config/policy.json`. The single selected `frontend_implementer` needs the exact route-bound protected-write mechanism; do not bypass it or split write ownership.

## Exact test and documentation integration

- Create `tests/test_demo.py`: real route -> complete bundled v2 spec validation/summary -> architecture validation/digests -> governance summary -> pure verification summary; bounded invalid input; 404/405; localhost config; security headers; no subprocess/network/filesystem mutation; stable deterministic JSON.
- Modify `tests/test_installer.py`, `tests/test_manifest_package.py`, and `tests/test_structure.py` for installed/archived/required demo surfaces and preservation of root marker/GitHub Actions bans.
- Modify `tests/test_architecture_model.py` and `tests/test_architecture_fitness.py` for the new local-only trust boundary and forbidden external/Trust-CI edges.
- Re-run the existing source-of-truth suites `tests/test_repo_router.py`, `tests/test_change_spec.py`, `tests/test_architecture_model.py`, `tests/test_architecture_fitness.py`, `tests/test_governance.py`, `tests/test_governance_fitness.py`, and `tests/test_verification_doctor.py` alongside `tests/test_demo.py`.
- Browser evidence is currently unconfigured: frontend profile has no required checks and there is no Playwright/Cypress/npm project. Retain stdlib unit/integration tests, then add a bounded browser/manual viewport and keyboard smoke record (desktop + mobile, loading/error/empty) without introducing a root Node marker solely for the demo.
- Update `README.md` current-state/complete graph and add a concise demo guide (recommended `docs/investor-demo.md`). If a release identity or ZIP is later requested, `VERSION`, README H1/current state, and `CHANGELOG.md` must move together before packaging; this route itself authorizes no publication.

## Blocking/current-state risks

- The active typed change spec is still a generated placeholder: zero acceptance criteria/invariants/forbidden outcomes/contracts/observability and `UNKNOWN` metric/target. It cannot pass the PR gate until the scope/design gate populates it.
- Route `base_commit` is `1c062998...`, but that commit is not an ancestor of actual head `d4cc01f...` (138 commits are in the raw range). Final verification would compare against the wrong base and may fail architecture/governance binding or treat the full M1-M3 stack as this UI diff. Re-route/rebind to the approved branch base before implementation evidence.
- Three other untracked change packages are present. Preserve them and keep them out of demo sample/package assertions; they are user/workflow state, not product input.
- A static green verification card must be visibly labelled bundled demo evidence. It must not be presented as the App-owned exact-SHA Trust CI verdict or as current merge/release authority.
