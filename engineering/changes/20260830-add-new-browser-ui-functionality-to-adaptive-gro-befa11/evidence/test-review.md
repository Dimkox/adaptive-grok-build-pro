# Test review — post-remediation investor-ready local product MVP

## Verdict

**PASS**

The two Important findings from the prior review wave are resolved and protected by focused regression tests. No Critical or Important test gap remains in the bounded local-demo scope.

## Inspected identity and tree

- Route: `befa117340b9`; route-selected role: `test_reviewer`.
- Approved comparison base and Git HEAD at review: `2cf89e40e5c3f33cddf87eecd7956ecf4a201df3`.
- Inspected combined pre-report tree fingerprint: `586d1ce5f974575d27e78f778d6f43339e0dbca31956f37c18b92f2351612eb3`.
- That fingerprint included the complete remediated tracked/untracked product tree, the fresh PASS `code-review.md`, and the prior `test-review.md`. Replacing this report is this reviewer's only tree change after fingerprint capture.
- Active package: `engineering/changes/20260830-add-new-browser-ui-functionality-to-adaptive-gro-befa11`.
- Release artifact inspected: `dist/adaptive-grok-build-pro-v2.1.0.zip`, SHA-256 `5969f951e416f2fb93b3d453267a91efded59ce109058b79b8ebf765ee89cec6`.

## Mandatory remediation checks

### 1. Initialization performs no subprocess or Git operation — resolved

`DemoApplication` now uses explicit deterministic, non-authoritative `DEMO_ROUTE_METADATA`; it no longer derives Git base/fingerprint during construction. `demo.py` no longer imports `git_default_base` or `tree_fingerprint`.

`test_application_and_server_initialization_do_not_run_subprocesses` patches `subprocess.run` **before** both `DemoApplication(...)` and `create_server(...)` execute. Both constructions and their bundled snapshots complete while any subprocess call would raise an assertion. This closes the hole in the earlier request-only test, whose patch began after server initialization.

The existing request-path test still separately proves that snapshot and preview HTTP traffic runs no subprocess and leaves `.grok-stack/runtime` byte/mtime state unchanged.

### 2. Alternate scenario is computed and truthfully labelled — resolved

The fixture now uses `Review the project documentation for clarity and broken links`. `build_sample_snapshot` computes that prompt through the real router using the same deterministic demo metadata and publishes an allowlisted `alternate_route` projection plus a label derived from the computed intent, risk, and write owner.

`test_alternate_scenario_claims_match_its_computed_route` independently invokes `build_route` and proves equality for intent/risk/domains/write owner. Current canonical result is `review`, `medium`, `[api]`, and no write owner; the label is exactly `Use contrasting review route · medium risk · no write owner`.

The browser takes `alternate_action_label` from the snapshot rather than embedding a risk claim. Static UI tests reject the stale `low-risk` wording. `docs/INVESTOR_DEMO.md` describes the same computed medium-risk result and explicitly rejects a fabricated low-risk claim. The rebuilt archive contains the corrected fixture, computation, UI, and guide.

## Fresh test evidence

### Focused remediation and demo/API suite

`python3 -m unittest tests.test_demo tests.test_demo_http -v`

- **20 tests passed**, 0.920 seconds, `OK`.
- Includes both new regressions plus route/spec direct equivalence, provenance, bundled-report validation, partial degradation, safe DOM, accessibility/responsive states, Host/Origin/media/schema/size/traversal/method rejection, headers, no-runtime-mutation, launcher, and OpenAPI inventory.

### Expanded impacted-scope suite

`python3 -m unittest tests.test_demo tests.test_demo_http tests.test_installer.InstallerTests.test_payload_is_sorted_safe_duplicate_free_and_profile_explicit tests.test_installer.InstallerTests.test_materialize_new_publishes_verified_payload_once tests.test_manifest_package.ManifestTests.test_local_demo_engine_assets_contract_and_guide_are_packaged tests.test_manifest_package.PackageTests.test_investor_demo_local_release_artifact_is_complete_and_checksum_bound tests.test_structure.StructureTests.test_core_product_files_exist tests.test_structure.StructureTests.test_version_identity_matches_readme tests.test_structure.StructureTests.test_local_demo_is_documented_as_read_only_sample_evidence -v`

- **27 tests passed**, 2.145 seconds, `OK`.
- Confirms installer payload/materialization, package inventory, version/docs identity, and checksum-bound release artifact in addition to all demo/API regressions.

### Static and artifact checks

- `ruff check .grok-stack/adaptive_grok/demo.py .grok-stack/adaptive_grok/demo_http.py scripts/grok_demo.py tests/test_demo.py tests/test_demo_http.py` — PASS, `All checks passed!`.
- `git diff --check` — PASS.
- `(cd dist && sha256sum -c adaptive-grok-build-pro-v2.1.0.zip.sha256)` — PASS.
- Direct ZIP inspection found `DEMO_ROUTE_METADATA`, computed alternate-label logic, the corrected alternate prompt, and corrected investor-guide wording in the packaged files.
- A fresh full `python3 scripts/grok_verify.py --mode pr` wave ran on the remediated product tree: every technical check passed; its final source-stability check alone failed because independent review evidence files were concurrently replaced. That run is useful technical evidence but is not treated as a valid final receipt. The parent delivery owner will freeze/commit the review reports and rerun verification on the stable final tree.

## Acceptance and forbidden-outcome assessment

- One-command loopback launch, closed HTTP surface, real pure route/spec preview, canonical architecture/governance projections, and truthful provenance remain covered.
- Preview verification remains `not_run`; bundled sample evidence is never represented as merge authority.
- Initialization and request traffic expose no Git/shell/verifier/provider/deploy operation.
- Dynamic UI values use text-only DOM rendering, and the alternate investor narrative is now derived from canonical computation.
- Installer and archive include the complete corrected product/demo surface with matching checksum.

## Severity-classified gaps

### Critical

None.

### Important

None.

### Minor residual risk

1. UI evidence remains portable structural/HTTP integration rather than a real browser-runner visual E2E. The approved test plan makes browser screenshots optional; semantic DOM, focus, offline/stale, mobile, reduced-motion, and forced-color behavior are asserted.
2. Some rare HTTP branches do not have individual cases, including short/missing `Content-Length`, missing static asset, injected internal preview failure, invalid port, and HEAD/TRACE behavior. The representative rejection classes and closed allowlist are covered.
3. OpenAPI tests verify the closed method/path inventory and request contract, not comprehensive runtime response-schema conformance. This is non-blocking for the single bundled UI consumer.
4. The no-mutation test snapshots runtime state rather than every repository file. The corrected initialization/request regressions plus module inspection show no write primitive or outbound client in the demo path; a generalized side-effect harness would further strengthen future service evolution.

## Completion assessment

The current remediated tree has sufficient test evidence for a PASS test review of the local investor-ready MVP. This verdict is not merge, release, deployment, production, or App-owned exact-SHA Trust CI authority; final completion still requires the delivery owner to freeze the evidence tree and create fresh fingerprint-bound verification/review receipts.
