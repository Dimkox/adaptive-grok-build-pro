# Architecture analysis — exact landing source compatibility

## Exact evidence and failure boundary

This is read-only architecture evidence for route `eb3f80383d44`. The control
repository was inspected at exact HEAD
`33206fa06ae4b5bfb390cb68bbf233800d2902ab`, tree
`6e24f82570bcb78ae90b92ee3e67d7fa7fbb4b28`. The local target repository is
clean at requested commit
`699010380f4f90a0193a9c22090c35e6aded7d2c`, tree
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`.

The target commit moved the homepage's inline CSS into a root stylesheet:

- `6990103:index.html:38` now contains exactly
  `<link rel="stylesheet" href="/index.css">` and contains no inline
  `<style>` block;
- `index.css` is a regular `100644` blob
  `4117a5f263d3500af4d397d3eac07f0d7b89b167`, 18,088 bytes, with SHA-256
  `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589`;
- the same commit updates the protected `.htaccess` to `style-src 'self'`, so
  the external stylesheet and the renderer-owned `/content.css` remain
  compatible with the source CSP.

The existing control code encodes the prior source twice. First,
`factory/src/adaptive_factory/landing_renderer.py:24-28` pins
`176efcaab931c2482781ff163c621b10aa05dee9` / tree
`f2bdcecc6dbe9ecc82007610d398ca12bd75e07f`. Second,
`source_surface_facts()` at lines 125-139 requires one inline style. A pure
call against the requested exact `index.html` reproduced
`LandingRenderError source_active_content`. Merely rotating the pin therefore
does not restore rendering.

There is a second independent failure after parser repair:
`factory/src/adaptive_factory/landing_artifact.py:35-60` declares 19 deploy
members and omits `index.css`. A candidate page would reference `/index.css`,
but the deterministic ZIP would not contain the corresponding relative member
`index.css`. Parser-only repair would therefore create an incomplete deploy
artifact.

## Smallest coherent design

The repair should rotate one exact source epoch and add one protected deploy
member. It must not generalize source selection, accept arbitrary stylesheets,
copy the target's whole tree, or grant the generator another path.

### 1. Rotate the exact source as one atomic identity

Set `TARGET_BASE_SHA` to
`699010380f4f90a0193a9c22090c35e6aded7d2c` and `TARGET_BASE_TREE` to
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`. Preserve the current repository
ID, `main` branch identity check, detached no-local/no-hardlink clone, private
workspace, source guard, and exact commit/tree comparison. Do not selectively
transplant only `index.html` or `index.css`: the exact source epoch also binds
the matching CSP change and every other protected source blob.

Runtime constants, OpenAPI literals, and tests must move together. There must
be no interval or compatibility branch in which SHA and tree can be paired
from different epochs.

### 2. Model `/index.css` as protected source, not generated output

Replace the obsolete inline-style surface fact with a digest of the exact
protected `/index.css` link tag. The bounded HTML check should:

1. require exactly one `/index.css` stylesheet link;
2. reject every inline `<style>` block;
3. on source HTML allow no renderer stylesheet, and on candidate HTML require
   exactly one `/content.css` link;
4. reject duplicate or any other stylesheet URL; and
5. retain the existing exact robots, canonical, hreflang, single JSON-LD,
   no-form, and no-tracker checks.

The source and candidate protected facts compare equal while the separately
validated candidate-only `/content.css` link is the sole permitted addition.
This avoids treating the generated link as source drift without opening an
arbitrary-link exception. The exact `index.css` bytes should also pass the same
bounded UTF-8/no-remote-dependency policy used for CSS (`@import`, remote
`url(...)`, and `javascript:` fail closed), but they need not be added to any
public record: `source_sha`, `source_tree`, and the complete source/candidate
Git inventories already bind the blob.

`LANDING_WRITE_PATHS` remains exactly
`frozenset({"index.html", "content.css"})`. Keep both explicit `git add`
calls restricted to those names, require the Git diff to equal those two
paths, require source and candidate tree shapes/modes to match, and require
every other blob identity—including `index.css` and `.htaccess`—to be equal.
The independent evaluator must re-assert the same two-path delta and closed
stylesheet topology. Do not concatenate `index.css` into `content.css`; doing
so would erase source provenance and weaken rollback/debugging.

### 3. Extend only the closed deploy allowlist

Add relative member `index.css` (never absolute `/index.css`) to
`DEPLOY_MEMBERS`. The sorted allowlist then contains exactly 20 members.
Continue excluding target `dist/`, tests, reports, plans, `ASSETS.md`, and
`SERVER-SETUP.md`; the target repository's own ZIP is not the artifact input.

Existing packager mechanics already give the new member the required
properties when it is added to the allowlist:

- the source guard requires a regular, non-symlink, single-link,
  non-executable file (`landing_artifact.py:168-203`);
- full-tree validation requires its source/candidate mode and object ID to be
  identical (`landing_artifact.py:463-490`);
- the manifest records path, fixed archive mode, size, SHA-256, source object
  ID, candidate object ID, and `provenance: "source"`
  (`landing_artifact.py:362-406`); and
- fixed ordering, timestamps, modes, compression, and canonical manifest
  bytes continue to determine the content-addressed ZIP and sidecar
  (`landing_artifact.py:751-775`).

For the requested source epoch, the `index.css` manifest entry must therefore
carry source and candidate object ID
`4117a5f263d3500af4d397d3eac07f0d7b89b167` and the SHA-256 above. The
manifest `changed_paths` remains exactly `['content.css', 'index.html']`;
`archive.member_count`, `SiteArtifactV1.member_count`, and returned member
names become 20. No JSON-schema extension is needed because
`landing-site-artifact.v1` already represents a bounded positive member count
and binds the manifest digest.

### 4. Make the source-epoch cutover explicit in the API contract

Update `factory/contracts/openapi/landing-dogfood.v1.json:83-84` to the new
exact SHA/tree and increment `info.version` from `1.0.0` to `1.0.1`. Keep the
`/v1` paths and closed record schemas: field meanings and response shapes do
not change. This is nevertheless an intentional acceptance cutover—requests
carrying the old exact tuple must receive the existing HTTP 409
`source_identity`, not be silently mapped or dual-accepted. The document
version and release/change evidence make that pin rotation explicit.

Already-created `LandingInputV1`, `LandingAttemptV1`, and `SiteArtifactV1`
records remain parseable and self-describing because their v1 schemas accept
any structurally valid SHA/tree and bind their own digests. Only new intake is
restricted to the current configured epoch.

## Finite acceptance criteria

1. New intake accepts only repository ID plus exact tuple
   `699010380f4f90a0193a9c22090c35e6aded7d2c` /
   `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`; the prior tuple and mixed tuples
   fail with `source_identity`, and OpenAPI exposes the same constants.
2. A hermetic source fixture with `/index.css`, zero inline styles, and the
   matching CSP renders successfully. The candidate has exactly one
   `/index.css` and one `/content.css` link, one JSON-LD block, and no unknown
   style or active-content surface.
3. Candidate Git diff is still exactly `content.css,index.html`.
   `index.css` and `.htaccess` retain their exact source mode/object IDs;
   deletion, replacement, mode drift, symlink/special/executable substitution,
   duplicate/remote stylesheet links, or adding `index.css` to changed paths
   fails closed.
4. The ZIP contains exactly the sorted 20-member allowlist. `index.css` occurs
   once, is byte-identical to the pinned source, has `provenance: source`, and
   its manifest source/candidate object IDs are equal. A page-to-archive check
   proves every root-relative stylesheet reference has a corresponding ZIP
   member; prohibited target files stay absent.
5. Two independent seals of the same exact candidate produce byte-identical
   ZIP, sidecar, manifest, names, and digests. A changed source/spec/renderer or
   protected stylesheet produces a different identity or fails closed; it
   never overwrites an existing content-addressed pair.
6. Focused renderer, evaluator/coordinator, artifact, contract, intake,
   provider, and API tests pass without a provider call, target-worktree
   mutation, publisher call, network access, or live URL. The final exact
   control tree then receives the route-selected verifier and independent
   reviews; this report is not merge authority.

The minimum regression edits are the external-style hermetic fixture and
protected-object assertions in `factory/tests/test_landing_renderer.py`, the
20-member/source-provenance and page-to-archive assertions in
`factory/tests/test_landing_artifact.py`, new pin/OpenAPI assertions in
`factory/tests/test_landing_contracts.py`, current pin fixture values in
`test_landing_intake.py` and `test_landing_provider.py`, and the fake artifact
count in `test_landing_api.py`. No new service, dependency, schema, migration,
provider, publisher, or target adapter is justified.

## Compatibility, forward recovery, and rollback

- **Historical artifacts:** do not edit or rebuild
  `packages/adaptive-grok-build-pro-v2.0.14.zip` (current SHA-256
  `b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`)
  or its sidecar, and do not modify the landing repository's tracked `dist/`
  pair. Any later product package uses a new version; any repaired landing ZIP
  receives a new content-addressed name alongside prior local evidence.
- **Backward behavior:** the v1 data models remain compatible, while stale
  source-header callers intentionally stop at 409. Dual pin acceptance is not
  backward compatibility here; it would make the exact target authority
  ambiguous and permit generation against a source whose layout no longer
  represents the selected epoch.
- **Rollback before any authorized deployment:** revert the repair commit or
  disable the injected landing composition. With the current target clone, old
  code then fails closed at source identity; no live site or target bytes are
  changed and no data migration needs reversal.
- **Forward recovery:** if the target advances again, route a new bounded pin
  rotation that re-derives commit/tree, protected stylesheet topology, and
  deploy inventory. Never follow a branch implicitly. If a future separately
  authorized deployment has occurred, production rollback must select a prior
  immutable site artifact by its manifest/digest under a new resource-bound
  grant; this source-only repair grants no such action.
