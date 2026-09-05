# AI/security architecture ruling: protected external homepage stylesheet

## Ruling and exact evidence

The current landing may be accepted with its external, same-origin `/index.css`, but only as reviewed source bytes cryptographically bound to the exact target identity. A path named `index.css` is not trusted by itself, and neither provider output nor `StaticLandingSpecV1` receives authority to select, replace, or synthesize a stylesheet or script.

The accepted source identity is repository `github.com/Dimkox/ai-dark-factory-landing`, commit `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`. At that tree:

- `index.html` has blob `3b12521033445e402a4617e84b14b24a6d8caa27` and SHA-256 `e58d85ad82ca9461ab505fa83e3b64a3c119c2eb07ef5491c453febd8bc1b274`;
- `index.css` is regular mode `100644`, blob `4117a5f263d3500af4d397d3eac07f0d7b89b167`, 18,088 bytes, and SHA-256 `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589`;
- the homepage has exactly one stylesheet link, `<link rel="stylesheet" href="/index.css">`, no inline `<style>`, and exactly one source JSON-LD script;
- the accepted `index.css` contains no `@import`, `url(...)`, `javascript:`, `expression(...)`, or `-moz-binding`. The protected `.htaccess` permits same-origin styles with `style-src 'self'` and keeps the exact JSON-LD script hash.

This is an explicit source-review decision, not a generalized claim that CSS is passive. CSS can initiate fetches, so a later target SHA/tree must be reviewed and rebound; it must not inherit this decision merely because the path is still `/index.css`.

## Closed trust boundary

There are three distinct inputs:

1. Uploaded text/audio/image/PDF/DOCX and provider output are untrusted data. The provider returns only the closed `StaticLandingSpecV1`; its text remains length-bounded and HTML-escaped. No spec field carries raw HTML, CSS, script, stylesheet URL, or arbitrary resource URL.
2. The exact target tree above is reviewed source. Its HTML, CSP, and `index.css` are accepted only after repository ID, commit, tree, regular-file mode, and Git object identity match.
3. The renderer is trusted deterministic code. It may replace the bounded `<main id="content">` region and append deterministic rules to `content.css`; it may add exactly one fixed tag for `/content.css`. It has no network or target-write authority.

Do not send `index.css` to the provider and do not interpret target HTML/CSS as prompt instructions. Keep `LANDING_WRITE_PATHS` exactly `{"index.html", "content.css"}`. In particular, adding `index.css` to the write allowlist would collapse the source/provider boundary and is forbidden.

## Minimal fail-closed surface parser

Replace the obsolete “exactly one inline style” fact with a protected stylesheet fact. The smallest coherent shape is a single bounded HTML surface-inventory helper used twice: source mode expects zero renderer stylesheet links; candidate mode expects one. `LandingSourceSurfaceFacts` should bind the raw `/index.css` start-tag digest alongside the existing robots, canonical, hreflang, and JSON-LD digests. The renderer then compares source and candidate facts while deliberately excluding only the fixed `/content.css` addition.

For both source and candidate, fail closed unless all of these hold:

- UTF-8 decoding, current size limit, LF-only/no-NUL input, and parser completion succeed.
- There is no `<base>`, `<style>`, `style=` attribute, or `on*` event-handler attribute. Event handlers are script authority even when no `<script>` element is added.
- Every style-bearing `<link>` is inventoried independent of attribute order/case. Reject duplicate attributes and `rel=alternate stylesheet`, `as=style`, or any other style-loading form. Do not rely only on the current case-sensitive regular expression.
- Source mode contains exactly one `rel=stylesheet` link with href exactly `/index.css` and zero `/content.css` links. Candidate mode contains exactly one of each. Query strings, fragments, percent-encoded variants, backslashes, scheme-relative URLs, absolute URLs, and any third stylesheet path fail.
- The raw `/index.css` tag digest in the candidate equals the source fact. The `/content.css` tag is the renderer-owned exact literal inserted once before `</head>`; provider text cannot influence it.
- There is exactly one script element, its only effective type is `application/ld+json`, it has no `src`, and its full-block digest equals the source fact. Any additional script, executable script type, `src`, malformed/duplicate script attribute, or change to the source JSON-LD fails.
- Existing no-form/no-tracker checks remain. Robots, canonical, and seven unique alternates remain source-bound.

A small standard-library `HTMLParser` inventory, retaining each raw start tag via `get_starttag_text()`, is sufficient; no sanitizer or new parsing framework is warranted. Because the input is an exact reviewed tree and the renderer only splices escaped markup into one known boundary, fail-closed inventory plus raw protected-tag/script hashes is the appropriate control. Parsing ambiguity or an unexpected tag/attribute yields a stable error rather than normalization.

## CSS and artifact invariants

The no-import/no-remote-resource claim has two independent proofs:

- Protected `index.css` is the exact reviewed blob above and cannot change between source and candidate. Its accepted bytes contain no import or URL-bearing construct. A future source pin must repeat this check rather than relaxing it.
- Source `content.css` is also exact-tree input, and generated additions come only from `_render_css`; provider fields are not interpolated as CSS. Validate source and final `content.css` case-insensitively and fail on any `@import`, any `url(` (the current accepted files need none), `javascript:`, `expression(`, or `-moz-binding`. Rejecting every `url(` is the narrowest unambiguous MVP rule; a future need for local CSS assets should be a versioned contract change.

Artifact behavior must make provenance independently observable:

- add `index.css` to `DEPLOY_MEMBERS`, producing exactly 20 deploy members, but never to `LANDING_WRITE_PATHS`;
- retain the exact-source clone/materialization, explicit two-path `git add`, full source/candidate tree-shape comparison, and protected-object equality in `ExactGitLandingWorkspace._validate_candidate`;
- require the manifest record for `index.css` to have `provenance: source`, `source_object_id == candidate_object_id == 4117a5f263d3500af4d397d3eac07f0d7b89b167`, and SHA-256 `91ae1c46ae5cc825d72e9ebde91e93901d0d8413d55f27f322613a593b8b1589` for this pin;
- keep `.htaccess` source-provenance and unchanged so the candidate cannot weaken `style-src 'self'` or script policy;
- keep the candidate delta exactly `content.css,index.html`; any `index.css` object/mode drift fails before packaging.

The existing exact SHA/tree source guard and protected-tree comparison already provide the byte-preservation mechanism. A new mutable `source_index_css` field is unnecessary if the packager re-materializes the exact tree and verifies the manifest object IDs/digest as above.

## Minimum regression set

1. The external-style fixture (no inline style, one `/index.css`) renders successfully; candidate HTML contains exactly `/index.css` plus `/content.css`, preserves the raw `/index.css` tag and JSON-LD hashes, and changes only `index.html`/`content.css`.
2. Table-driven parser cases reject an inline style, `style=`, event handler, `<base>`, extra/executable/src script, remote or scheme-relative stylesheet, third local stylesheet, duplicate `/index.css`, duplicate `/content.css`, preload-as-style, and stylesheet query/fragment variants.
3. Source or final `content.css` containing `@import` or any `url(` fails. The accepted exact `index.css` is characterized as free of imports/URLs and bound to the blob/SHA-256 above.
4. A forged provider spec containing markup remains rejected by the closed contract or escaped as text and cannot affect the active-surface inventory.
5. Candidate-tree mutation of `index.css` fails with protected-tree drift. The ZIP contains `index.css`; its manifest entry is source-provenance with equal source/candidate object IDs, and every root-relative homepage stylesheet is present in the archive.

No live provider call, target mutation, network action, or broad suite is needed for this repair analysis. General-purpose HTML sanitization, arbitrary author-provided CSS, remote font/image support, and a new CSS framework are outside this bounded fix.
