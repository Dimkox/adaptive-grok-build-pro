# Contract and integration analysis — current landing source repair

**Route:** `eb3f80383d44`
**Control-plane basis:** `33206fa06ae4b5bfb390cb68bbf233800d2902ab`, tree `6e24f82570bcb78ae90b92ee3e67d7fa7fbb4b28`
**Required landing identity:** commit `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`

This is read-only integration analysis. It authorizes no provider call, target mutation, package replacement, push, or release.

## Finding and bounded repair

The current landing commit is the direct child of the factory's pinned `176efcaab931c2482781ff163c621b10aa05dee9`. It extracted homepage styles from an inline `<style>` into the same-origin protected file `/index.css` and changed the protected `.htaccess` CSP to `style-src 'self'`.

The factory now fails in three ordered places:

1. `LandingApplicationService.submit()` rejects the current SHA/tree as HTTP `409`, code `source_identity`, because it imports stale renderer constants.
2. Updating only those constants reaches `source_surface_facts()`, which currently requires exactly one inline style and therefore rejects the current homepage as `source_active_content`.
3. Updating the surface validator alone would allow candidate creation, but `DEPLOY_MEMBERS` still has 19 paths. The resulting artifact would omit the homepage's required protected `index.css`.

The repair must move all three bindings atomically. Keep the generator write set exactly `{"index.html", "content.css"}`. `index.css` is source-owned: validate it, preserve its Git object/mode, include it in the artifact, and never expose it as a generator write path.

The exact protected source facts are:

| Path | Git object | SHA-256 | Mode |
|---|---|---|---|
| `index.css` | `4117a5f263d3500af4d397d3eac07f0d7b89b167` | `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589` | `100644` |
| `index.html` | `3b12521033445e402a4617e84b14b24a6d8caa27` | `e58d85ad82ca9461ab505fa83e3b64a3c119c2eb07ef5491c453febd8bc1b274` | `100644` |
| `content.css` | `c03a156503ea58dec9dfe20da2fb3cce39662297` | `15e52cfa1e6aefe121e6d3f5b25395d5445954d3bad8989070d46cbb4d676f8d` | `100644` |
| `.htaccess` | `9bb58858afeb92d928eabada698dae3e46009cc5` | `a0f8355855837f72ae95a0e6ca60bd3ca3da64eb2d813cffbaffa0cf2b819a62` | `100644` |

## Exact implementation seams

| File | Required change | Invariant |
|---|---|---|
| `factory/src/adaptive_factory/landing_renderer.py` | Set `TARGET_BASE_SHA` and `TARGET_BASE_TREE` to the required commit/tree. Replace the inline-style surface fact with an exact protected `/index.css` stylesheet fact; reject inline styles, duplicate/foreign stylesheet links, and retain the single JSON-LD/no-form/no-tracker checks. Bump `RENDERER_VERSION` because the accepted source surface changed. | Source and rendered facts bind the exact `/index.css` tag while ignoring only the renderer-owned optional `/content.css` link. `LANDING_WRITE_PATHS`, explicit `git add`, detached clone, protected-tree comparison, and no-local/no-hardlink controls remain unchanged. |
| `factory/src/adaptive_factory/landing_artifact.py` | Add exactly `index.css` to `DEPLOY_MEMBERS`. | Inventory becomes the sorted 20 paths below. The member is regular/non-executable, has `provenance: source`, and has identical source/candidate object IDs. No `dist/`, target tests, or target documentation enters the archive. |
| `factory/contracts/openapi/landing-dogfood.v1.json` | Change `ExactBaseSha`/`ExactBaseTree` header constants and bump `info.version` from `1.0.0` to `1.0.1`. | Paths, operation IDs, media types, request/response schemas, status sets, and `/v1` remain unchanged. The patch metadata makes the pin rotation visible. |

No production edit is required in `factory/src/adaptive_factory/landing_service.py`: it imports the renderer constants and already rejects any non-current tuple before blob-store, job-store, provider, or artifact-builder work. No production edit is required in `factory/src/adaptive_factory/api.py`, `landing_contracts.py`, or any `factory/contracts/jsonschema/landing-*.json`: the v1 records already carry arbitrary valid SHA/tree identities, `LandingInputV1.input_digest` binds both, and `SiteArtifactV1.member_count` is a bounded integer rather than a fixed 19.

The corrected deployment allowlist is exactly:

```text
.htaccess
california-privacy.html
content.css
cookies.html
favicon.png
google4175cca555a80a32.html
index.css
index.html
km/index.html
ko/index.html
lv/index.html
nl/index.html
og-image-automatic.jpg
privacy.html
roadmap.html
robots.txt
sitemap.xml
terms.html
yandex_15bd00519dc47ca1.html
zh-cn/index.html
```

## Stale-pin response and replay semantics

After the repair, a submission carrying either old SHA, old tree, or a mixed old/new tuple must receive the existing closed response:

```json
{"error":"conflict","code":"source_identity","detail":"landing source identity mismatch"}
```

with HTTP `409`. It must create no `LandingInputV1`, quarantine blob, job record, provider request, candidate, or artifact. The present API buffers the already bounded request body before calling the service, but the service rejects the tuple before all durable/application processing; this repair need not change that request-flow shape.

The pin is part of the idempotent request identity, not server-side migration metadata:

- Replaying an old-pin submission remains `409 source_identity`, even if that job ID previously existed. Do not return the historical `202` projection under a now-stale source authority.
- A current-pin retry with the same tenant/repository/job ID and identical bytes returns the already stored current-pin result without another provider call.
- Reusing a job ID that is still associated with an old-pin record for a current-pin submission yields the existing `409 idempotency_conflict`; the client must use a new idempotency key/job ID for the new source generation. Existing GET/result/cancel operations remain keyed by tenant/repository/job and do not rewrite the historical record.
- Because SHA/tree participate in `LandingInputV1.input_digest`, the current-pin request and every downstream attempt/evaluation/artifact binding receive new digests. No old digest or artifact may be rebound to the new source.
- Sealing the same new candidate remains a no-replace CAS replay and returns the same ZIP/sidecar identity. Adding `index.css` makes the corrected artifact a distinct deterministic 20-member object that can coexist with historical 19-member artifacts.

## Compatibility posture

This is a fail-closed pin rotation with additive artifact completeness, not a new API major version. JSON wire shapes and all six schema version values remain `1`; endpoint consumers that already send configured exact-source headers need only adopt the new advertised tuple. Accepting both tuples, silently translating the old tuple, or serving an old artifact for a new-pin request would defeat the exact-source boundary and is prohibited.

Historical repository release `v2.0.14`, its product ZIP/sidecar, its L5 artifact identities, and its Trust CI evidence remain immutable historical facts. The repair produces new source/candidate/manifest/ZIP/sidecar/artifact identities and requires a future distinct product/release identity if delivered; it must not edit or overwrite published bytes.

No provider/publisher compatibility issue is introduced: their contract inputs already bind `LandingInputV1`, profile, candidate, and artifact digests. Defaults stay unavailable and this repair performs no target-side action.

## Exact regression coverage

Required focused test edits are:

- `factory/tests/test_landing_renderer.py`: make `sealed_target()` match the external-style source (`/index.css`, no inline `<style>`, protected file present, matching CSP); retain exact two-file delta assertions; assert `index.css` mode/object is unchanged and the candidate contains exactly one protected `/index.css` plus the renderer-owned `/content.css`. Add fail-closed cases for missing/duplicate/changed protected link, inline style, and an unrecognized stylesheet.
- `factory/tests/test_landing_artifact.py`: change the exact member count to 20; assert `index.css` occurs once, its archive bytes match the pinned source, its provenance is `source`, and its source/candidate object IDs match. Assert every same-origin stylesheet referenced by candidate `index.html` is present in the archive. Retain deterministic replay, no-replace/orphan recovery, special-file rejection, and published-package freeze checks.
- `factory/tests/test_landing_api.py`: update the bound fake artifact count to 20. Add a stale-pin test covering old SHA/tree and mixed tuples, exact `409 source_identity`, no blob/store/provider/artifact side effect, current-pin success, exact replay, and changed-pin/job-ID conflict behavior.
- `factory/tests/test_landing_contracts.py`: update canonical input facts and assertions to the new tuple; assert OpenAPI `info.version == "1.0.1"`, both new constants, unchanged operations/status sets, and unchanged schema versions.
- `factory/tests/test_landing_intake.py` and `factory/tests/test_landing_provider.py`: update only canonical `BASE_SHA`/`BASE_TREE` fixture literals so input/provider digest and replay coverage is bound to the current source.

Critical existing test methods to preserve are:

- `LandingRendererTests.test_exact_target_workspace_is_private_detached_independent_and_two_file_bounded`
- `LandingRendererTests.test_renderer_escapes_spec_and_preserves_source_indexing_jsonld_and_csp_facts`
- `LandingArtifactTests.test_same_candidate_seals_reproducibly_with_exact_deploy_inventory`
- `LandingArtifactTests.test_manifest_binds_both_repositories_and_every_member_provenance`
- `LandingArtifactTests.test_output_pair_is_no_replace_and_product_package_is_unchanged`
- `LandingApiTests.test_auth_repository_tenant_and_idempotency_are_bound`
- `LandingApiTests.test_provider_exception_persists_terminal_state_before_idempotent_replay`
- `LandingContractTests.test_input_binds_the_authoritative_repository_sha_and_tree`
- `LandingContractTests.test_six_json_schemas_and_additive_openapi_are_closed_version_one`

The focused verification set is the six modules above. This analysis did not execute them. Full PR verification and route-selected independent reviews belong after the single `ai_implementer` finishes the product tree.
