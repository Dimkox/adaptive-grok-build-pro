# Documentation and contract impact — current L5 landing source

Route: `eb3f80383d44`
Control repository base inspected: `33206fa06ae4b5bfb390cb68bbf233800d2902ab`
Control repository tree: `6e24f82570bcb78ae90b92ee3e67d7fa7fbb4b28`
Landing repository inspected read-only at:
`699010380f4f90a0193a9c22090c35e6aded7d2c`, tree
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`

## Ruling

This is an unreleased source-compatibility repair after published `v2.0.14`,
not a rewrite of that release. Current maintained contracts and handoff
documentation must bind the factory to landing commit `6990103...` and its
20-member selected deploy inventory. The completed route `9f67efd2575c`, its
approved design/plan/change package, the `2.0.14` changelog entry, tag, release
artifact, and exact Trust CI evidence remain historical and immutable.

The smallest compatible implementation keeps the generator write allowlist
exactly `index.html` plus `content.css`. New `index.css` is a source-owned,
read-only, protected member: it is validated and packaged but never generated
or staged as a candidate change.

## Exact upstream delta and root cause

`6990103...` is the direct one-commit child of the published L5 pin
`176efcaab931c2482781ff163c621b10aa05dee9`, tree
`f2bdcecc6dbe9ecc82007610d398ca12bd75e07f`. The commit changes only
`.htaccess`, `README.md`, `dist/SHA256SUMS.txt`, the upstream deployment ZIP,
`index.html`, `tests/test_landing.py`, and new `index.css`.

The compatibility break has three connected facts:

1. Factory constants and the OpenAPI exact-base headers still accept only the
   parent SHA/tree.
2. Current `index.html` has no inline `<style>`; it has exactly
   `<link rel="stylesheet" href="/index.css">`. The existing source-surface
   contract requires one inline style and therefore rejects the current source.
3. The current factory deploy inventory has 19 members and omits `index.css`,
   so accepting the new source without changing the inventory would create an
   unstyled artifact.

Relevant current source identities are:

| Path | Git blob | SHA-256 | Mode |
| --- | --- | --- | --- |
| `index.html` | `3b12521033445e402a4617e84b14b24a6d8caa27` | `e58d85ad82ca9461ab505fa83e3b64a3c119c2eb07ef5491c453febd8bc1b274` | `100644` |
| `index.css` | `4117a5f263d3500af4d397d3eac07f0d7b89b167` | `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589` | `100644` |
| `content.css` | `c03a156503ea58dec9dfe20da2fb3cce39662297` | `15e52cfa1e6aefe121e6d3f5b25395d5445954d3bad8989070d46cbb4d676f8d` | `100644` |
| `.htaccess` | `9bb58858afeb92d928eabada698dae3e46009cc5` | `a0f8355855837f72ae95a0e6ca60bd3ca3da64eb2d813cffbaffa0cf2b819a62` | `100644` |

The new `.htaccess` intentionally changes CSP from a hash-authorized inline
style to `style-src 'self'`. It is already a protected source-provenance deploy
member. The upstream `dist/therealaidarkfactory.online.zip` has SHA-256
`ef53ba4c7287e961b7d44398830819d5c9963987329168d2b3f04b66e7117af0`
and 22 members. It is evidence about the landing repository, not an input to
the factory artifact: `ASSETS.md` and `SERVER-SETUP.md` remain intentionally
excluded, so the corrected factory selection is exactly 20 members.

## Machine-readable bindings that must change

| Authority | Minimal change | Compatibility rule |
| --- | --- | --- |
| `factory/src/adaptive_factory/landing_renderer.py` | Replace `TARGET_BASE_SHA`/`TARGET_BASE_TREE` with `6990103...` / `f7dbbd8...`; recognize the exact protected `/index.css` source link and absence of inline style; keep optional renderer-owned `/content.css`. | `LANDING_WRITE_PATHS` remains exactly `{index.html, content.css}`. The protected stylesheet tag/bytes must participate in source-fact or renderer identity so it cannot drift unnoticed. Bump the renderer identity because accepted source semantics changed. |
| `factory/src/adaptive_factory/landing_artifact.py` | Add only `index.css` to `DEPLOY_MEMBERS`, yielding 20 selected members. | Manifest entry is `provenance: source`, with identical source/candidate object ID and mode. Do not add upstream docs or nested `dist/` artifacts. |
| `factory/contracts/openapi/landing-dogfood.v1.json` | Change `ExactBaseSha` and `ExactBaseTree` constants to the current values and bump `info.version` from `1.0.0` to `1.0.1`. | Keep `/v1` operations and payload schemas unchanged. Requests carrying the old pin must continue to fail closed with `409 source_identity`; the patch contract revision makes the accepted-binding change explicit rather than silent. |
| Artifact manifest/result data | Derive `member_count: 20`; include the sorted `index.css` record and its source provenance/hash. | Existing `SiteArtifactV1` fields and schema version remain valid. A new artifact receives new source/candidate/manifest/ZIP/sidecar digests; no old record is rebound. |
| Current repair `change-spec.yaml` | Replace `UNKNOWN`/empty arrays with exact objective, criteria, invariants, forbidden outcomes, OpenAPI path, evidence, and zero-effect observations. | Typed criteria must bind new SHA/tree, protected `index.css`, unchanged two-file writes, 20-member determinism, old-source rejection, no provider/target call, and immutable published release bytes. |
| `PROJECT_STATE.json` | Add a distinct current/unreleased repair record for route `eb3f80383d44`, branch/base, new landing SHA/tree, current phase/evidence, and next action. | Do not mutate the nested `published_release`, prior release, PR #24 delivery, or artifact-child identities to imply this repair was in `v2.0.14`. Keep publication and current work as separate axes. |

No JSON Schema shape change is required. In particular,
`landing-site-artifact.v1.schema.json` already permits a derived member count
and generic exact SHA/tree values. Creating a `v2` API or schema would expand
scope without changing wire semantics.

## Durable documentation that must change

1. Complete only the new repair package's `brief.md`, `requirements.md`,
   `architecture.md`, `test-plan.md`, `tasks.md`, `release.md`, and
   `rollback.md`. Record old -> new source supersession, the three-stage root
   cause above, the exact two-file write invariant, protected `index.css`, the
   20-member artifact, focused regression evidence, forward-fix rollback, and
   zero external effects. Move `state.json` only through `grok_change.py`.
2. Update root `README.md` with a short **unreleased repair** statement and
   make its active-change link point to this package. Keep the existing
   statement that published `v2.0.14` produced a 19-member artifact; that is a
   historical fact, not a current inventory claim.
3. Update `factory/README.md`: its phrase "local unpublished `2.0.14` source
   candidate" is now stale. It must distinguish published `v2.0.14` from this
   unreleased current-source repair and name the protected external stylesheet
   plus unchanged writer scope.
4. Update `START_HERE.md` and the current-work portion of
   `PROJECT_STATE.json` so a fresh agent sees route `eb3f80383d44`, exact
   landing SHA/tree, no external effect, and the next local action. Preserve
   their tag-bound publication snapshot verbatim as historical identity.
5. Add a terse `Unreleased` repair entry to `CHANGELOG.md` if the branch is
   proposed as a product-source PR. Do not edit the `2.0.14` release section;
   its 19-member claim describes the published bytes correctly.

The bounded repair does not change M0-M9 status, migrations, topology, runtime
provider availability, publisher capability, indexing, hosting, or production
authority. Therefore `DARK_FACTORY_ROADMAP.md`, architecture nodes/edges,
`packages/README.md`, `VERSION`, and the old L5 design/plan/change package do
not need content edits for this repair.

## Required focused evidence reflected by the docs

- Current exact source is accepted; the previous or any mismatched SHA/tree is
  rejected before workspace creation.
- Source HTML accepts no inline style, retains exactly the protected
  `/index.css` link, and the rendered candidate adds/retains `/content.css`
  without weakening canonical, robots, hreflang, JSON-LD, CSP, or static-only
  restrictions.
- `index.css` cannot enter the write set and any blob/mode change is reported
  as protected-tree drift.
- Repeated packaging yields identical 20-member ZIP, manifest, and sidecar;
  `index.css` is present with source provenance and unchanged object IDs.
- Contract tests bind OpenAPI `1.0.1` to the exact current source. API fixture
  member counts change from 19 to 20; all other v1 operations/states remain.
- Existing `packages/adaptive-grok-build-pro-v2.0.14.zip` and sidecar hashes,
  old change evidence, landing clone, and target remain unchanged; provider and
  publisher external-call counters remain zero.

## Published `v2.0.14` identities that remain immutable

| Identity | Frozen value |
| --- | --- |
| Annotated tag object | `aeb627f136b6523e586b68de234f917f67a60759` |
| Tag/merge target | `1751b5855e46782b9a1bfceb6e1ab0102cba03b0` |
| Release tree | `618df086920c92179aa0e22a8c8d4ad30ebd9230` |
| Checked PR #24 head | `66a7fe5c4a59b3ea7e1350b34e0a547faf5a9f57` |
| Product ZIP | `packages/adaptive-grok-build-pro-v2.0.14.zip`, SHA-256 `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`, Git blob `9315208cfd1dfd18805b86e33c349231ac0639e0` |
| Sidecar | file SHA-256 `1a961c35b8f12fa02579ec7888c889f0ae7ca8656b158eb731681ef8357caf3c`, Git blob `b64357df1e9feea3c1ef0d56efb481088ca0bab3`; content continues to name ZIP SHA `b03c64e...` |
| App trust evidence | `adaptive-trust-ci/verified@06ecf1c875bc`, check run `101099224099`, attestation `9defb556-f703-4a13-b20a-8b88aa6781b4`, signer `0519cf1d47436f2e` |
| Reviewed source/policy evidence | product `5f47508f3c0d52b71a3c866969cc28b6476a9d99` / tree `0ae72773d73a294b88a398cec9926f6fca2f5555`; policy `58c9caed5d2c8f9febba297430a0782438505d82` / tree `975bf7a21784bf91279a684bdeb5f5394fb715a1` |

The original L5 package and design documents must continue to name source
`176efc...`/`f2bdce...`, because that is what the published implementation was
built and reviewed against. The new package records supersession; a global
search-and-replace would falsify provenance. Any future release requires a new
version/artifact identity and separately authorized release workflow; this
repair must not overwrite or restack `v2.0.14`.

## Analysis boundary

Inspection used local Git objects, tracked contracts, documentation, and ZIP
member metadata only. No full test suite, provider process, renderer workspace,
network access, target mutation, package rebuild, or external write occurred.
