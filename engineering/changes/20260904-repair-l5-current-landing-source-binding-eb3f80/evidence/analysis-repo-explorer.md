# Repository analysis: current L5 landing source binding

## Scope and exact baselines

Read-only analysis for route `eb3f80383d44`. The control repository was inspected at `33206fa06ae4b5bfb390cb68bbf233800d2902ab` (tree `6e24f82570bcb78ae90b92ee3e67d7fa7fbb4b28`, equal to `origin/main`). The local landing source `/home/pall/grok-projects/ai-dark-factory-landing` is clean at the requested `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.

The current landing revision is one direct, additively relevant commit after the control plane's stale pin:

```text
699010380f4f90a0193a9c22090c35e6aded7d2c 176efcaab931c2482781ff163c621b10aa05dee9 refactor: extract homepage styles
```

Its source delta is limited to `.htaccess`, `README.md`, `dist/SHA256SUMS.txt`, `dist/therealaidarkfactory.online.zip`, `index.html`, `tests/test_landing.py`, and new `index.css`. Important current blobs are `.htaccess` `9bb58858afeb92d928eabada698dae3e46009cc5`, `content.css` `c03a156503ea58dec9dfe20da2fb3cce39662297`, `index.css` `4117a5f263d3500af4d397d3eac07f0d7b89b167`, and `index.html` `3b12521033445e402a4617e84b14b24a6d8caa27`; all are regular mode `100644`.

## Reproduced failure chain

1. The public API/service and renderer are bound to the obsolete source. `factory/src/adaptive_factory/landing_renderer.py:24-28` still defines SHA `176efcaa...` and tree `f2bdcecc...`; `factory/src/adaptive_factory/landing_service.py:161-162` consequently rejects current headers with HTTP 409 `source_identity`. Direct use of the clean current clone reaches `ExactGitLandingWorkspace._source_guard()` at `landing_renderer.py:429-442` and fails before creating a workspace. Focused reproduction returned `LandingRenderError source_identity`.
2. Merely changing those two constants is insufficient. Current `index.html:38` uses the same-origin protected stylesheet `<link rel="stylesheet" href="/index.css">` and has no inline `<style>`. `source_surface_facts()` at `landing_renderer.py:101-138` requires exactly one inline style, so a focused parse of the exact current file returned `LandingRenderError source_active_content`.
3. Once the source-surface rule accepts the new layout, candidate generation should still change exactly `index.html` and `content.css`. The full-tree equality/protected-object checks at `landing_renderer.py:592-608` already make `index.css` immutable in the candidate. It must not be added to `LANDING_WRITE_PATHS`.
4. Artifact sealing would then silently omit the required protected style asset. `factory/src/adaptive_factory/landing_artifact.py:35-60` has 19 `DEPLOY_MEMBERS` and lacks `index.css`; the exact current homepage references `/index.css`. A focused inventory comparison produced `missing_from_DEPLOY_MEMBERS ['index.css']`. The landing repository's own deployment ZIP has 22 members; the only members outside the control list are intentionally excluded `ASSETS.md`, intentionally excluded `SERVER-SETUP.md`, and required `index.css`. Thus the corrected control artifact inventory is exactly 20 members.
5. The externally visible versioned binding remains stale in `factory/contracts/openapi/landing-dogfood.v1.json:83-84`, with matching stale literal assertions in contract tests.

The landing commit also changes CSP from a hash-authorized inline style to `style-src 'self'`; `.htaccess` is already a source-provenance deploy member and is protected by the same tree checks. No target-side bytes need to be copied or changed.

## Minimal secure implementation map

- `factory/src/adaptive_factory/landing_renderer.py`
  - Replace only `TARGET_BASE_SHA`/`TARGET_BASE_TREE` with `699010380f4f90a0193a9c22090c35e6aded7d2c` / `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.
  - Adapt `LandingSourceSurfaceFacts` and `source_surface_facts()` to the pinned external-style surface: reject inline `<style>`, require exactly one protected `/index.css` stylesheet, permit only the renderer-owned optional `/content.css` stylesheet, and retain the one-JSON-LD/no-form/no-tracker checks. Bind the exact protected stylesheet tag (or its digest) in the facts equality so render output cannot drift it.
  - Keep `LANDING_WRITE_PATHS = {"index.html", "content.css"}`, the explicit `git add`, and all clone/tree/source guards unchanged.
- `factory/src/adaptive_factory/landing_artifact.py`
  - Add exactly `index.css` to `DEPLOY_MEMBERS`. It will naturally be read from the exact source/candidate tree, validated as a regular non-executable single-link file, emitted deterministically, and recorded with `provenance: source`. Keep `ASSETS.md` and `SERVER-SETUP.md` excluded and do not alter existing artifact files.
- `factory/contracts/openapi/landing-dogfood.v1.json`
  - Replace the two exact-base constants. Because this changes an observable accepted binding while retaining `/v1`, a patch metadata bump from `info.version` `1.0.0` to `1.0.1` is the smallest explicit contract version signal.
- `factory/tests/test_landing_renderer.py`
  - Make the hermetic sealed fixture match the external-style shape (`/index.css`, no inline style, source `index.css` file); assert `index.css` object/mode is unchanged and the generated page retains it while adding `/content.css`. Preserve the exact two-file delta assertion.
- `factory/tests/test_landing_artifact.py`
  - Change the expected count from 19 to 20; assert `index.css` is in ZIP/member records with source provenance and unchanged source/candidate object IDs. Add/retain a page-stylesheet-to-archive subset assertion analogous to the landing repository's regression at `tests/test_landing.py:93-105`.
- `factory/tests/test_landing_contracts.py`, `factory/tests/test_landing_intake.py`, and `factory/tests/test_landing_provider.py`
  - Update landing-target fixture literals to the new SHA/tree. In `test_landing_contracts.py`, update the OpenAPI constant assertions and assert the patch contract version if it is bumped.
- `factory/tests/test_landing_api.py`
  - Its request path imports the renderer constants, but the fake artifact still reports `member_count: 19` at line 71; update this semantically to 20 and retain the current source-identity/409 coverage.

Current/historical documentation containing the obsolete exact pin is: `docs/superpowers/specs/2026-09-04-l5-multimodal-landing-dogfood-design.md`, `docs/superpowers/plans/2026-09-04-l5-multimodal-landing-dogfood.md`, and the original L5 package's `brief.md`, `requirements.md`, `architecture.md`, and `change-spec.yaml`. Do not perform a blind global replacement in the already-completed original change record; record the old-to-new supersession and current invariants in this repair package, and update only a document that is intentionally maintained as current authority. `README.md`, `START_HERE.md`, and `PROJECT_STATE.json` contain no stale exact pin.

## Focused verification recommendation

Start with a regression that fails on the exact three-stage chain above, then run only the affected modules before the route-level verifier:

```bash
PYTHONPATH=.:factory/src python3 -m unittest \
  factory.tests.test_landing_renderer \
  factory.tests.test_landing_artifact \
  factory.tests.test_landing_contracts \
  factory.tests.test_landing_api \
  factory.tests.test_landing_intake \
  factory.tests.test_landing_provider
```

Critical assertions are `LandingRendererTests.test_exact_target_workspace_is_private_detached_independent_and_two_file_bounded`, `LandingRendererTests.test_renderer_escapes_spec_and_preserves_source_indexing_jsonld_and_csp_facts`, `LandingArtifactTests.test_same_candidate_seals_reproducibly_with_exact_deploy_inventory`, `LandingArtifactTests.test_manifest_binds_both_repositories_and_every_member_provenance`, `LandingArtifactTests.test_source_symlink_hardlink_special_and_executable_inputs_are_rejected`, `LandingContractTests.test_input_binds_the_authoritative_repository_sha_and_tree`, and `LandingContractTests.test_six_json_schemas_and_additive_openapi_are_closed_version_one`.

## Commands/evidence

Read-only commands used included `git rev-parse HEAD HEAD^{tree}`, `git status --short --branch`, `git merge-base`, `git log --format='%H %P %s'`, `git diff --name-status`, `git ls-tree -r`, scoped `rg`, source reads, and ZIP member reads. Focused Python probes called only `_source_guard()`, `source_surface_facts()`, and compared HTML stylesheet references with `DEPLOY_MEMBERS`; no suite, provider, renderer workspace, target mutation, network operation, or external write was performed.
