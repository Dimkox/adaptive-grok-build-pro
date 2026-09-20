# repo_explorer — Winston Wolfe Pulp Fiction landing v2

Change: `20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`  
Route: `e0c9a65c0d53`  
Mode: read-only inventory. No product files were modified except this evidence report.

## Current layout facts

- `side-projects/` currently contains **only** `seo-landing-showcase/` (six files: `index.html`, `styles.css`, `browser-contract.mjs`, `ASSETS.md`, `README.md`, `SERVER-SETUP.md`).
- **`side-projects/seo-landings/` does not exist** on disk. The generate-mode skill still names it as the default output root.
- There are **no** Winston Wolfe / Pulp Fiction / «Винстон Вульф» / «Криминальное чтиво» landing files outside this change package. The only matches are the new change-package titles and the user objective string.
- Skill package: `.agents/skills/seo-landing/` (exact inventory pinned by `SeoLandingSkillTests.test_exact_package_inventory_and_codex_metadata`). Default generate path in `SKILL.md` §1:

  `side-projects/seo-landings/<project-slug>/`

  Required siblings: `index.html`, optional `styles.css` / `script.js`, `images/`, `favicon.png`, `ASSETS.md`, `robots.txt`, `sitemap.xml`, `SERVER-SETUP.md`. Never write generated landings at the workspace root.
- Showcase is a **non-indexable Russian skill demo**, not a character landing: `noindex, nofollow`, no canonical/`og:url`, no form, no external runtime URLs, no JS on the page. `browser-contract.mjs` is a local Chrome runner, not page JS.
- Architecture node `NODE-SEO-SHOWCASE-LAB` (`architecture/system.yaml`) owns only:
  - `.agents/skills/seo-landing`
  - `side-projects/seo-landing-showcase`
- README current-state links only the skill and the showcase; it does not mention `seo-landings/` or any character landing.
- `factory/tests/test_landing_api.py` freezes the showcase as **exactly 6 files** with aggregate digest `f7b4e8b3a53efa226cd198d7ca9449db882ddbc63792af7284457251c8e17c96`.
- Skill reference files are SHA-pinned (tech-spec, server-config, video-facade, map-facade). Any edit to `.agents/skills/seo-landing/**` fails `test_seo_landing_side_project.py`.
- Change package brief/spec is still a stub: objective is the Russian request; domain is mis-tagged `api`; no production URL, keywords, language, or media facts collected.

## Recommended output path

**Create a new add-only project:**

`side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/`

Rationale:

1. Matches the skill OUTPUT contract (`side-projects/seo-landings/<project-slug>/`).
2. Does not overwrite or reinterpret the showcase fixture (prior L5/dogfood rulings treat the showcase as byte-for-byte immutable).
3. “v2” is a **new generated project**, not an in-place rewrite of a missing v1. There is no v1 tree to `fix-existing`.
4. Keep files listed in SKILL.md §1 / tech-spec OUTPUT. Until a real production origin exists, follow the showcase honesty pattern: `noindex, nofollow`, omit canonical/`og:url`/indexable sitemap claims, and document that indexing needs a later change with a verified URL.

Do **not** put the landing at repo root, under `.agents/skills/`, under `factory/`, or inside `seo-landing-showcase/`.

## Files that MUST remain untouched

| Path | Why |
| --- | --- |
| `.agents/skills/seo-landing/**` | Exact file set + SHA256 of references + MIT/UPSTREAM notices. Any write fails skill tests. |
| `side-projects/seo-landing-showcase/**` | Showcase HTML/CSS contract, browser runner, and factory aggregate digest of 6 files. L5 design also requires byte-identity. |
| `tests/test_seo_landing_side_project.py` | Pins skill inventory, generate path string, showcase noindex/no-external, runner CDP contracts. Do not retarget it at the new landing. |
| `factory/tests/test_landing_api.py` (showcase aggregate) | Fails if showcase file count/digest changes. |
| Trust CI, `trust-ci/`, `.env`, keys, GitHub Actions | Out of scope; AGENTS.md forbids. |
| Factory L5 landing Python (`factory/src/adaptive_factory/landing_*.py`) | Different product: autonomous dogfood runtime, not this static character page. `tests/test_landing_architecture_boundaries.py` is factory-only. |

README should be updated **only if** the tree ships a new tracked side-project (AGENTS.md “README before push”). That is documentation, not the landing itself.

Architecture: adding `side-projects/seo-landings/` is **not** currently listed on `NODE-SEO-SHOWCASE-LAB`. A later architecture increment may add that prefix (or a sibling node). Leaving it unlisted is consistent with “generated projects under seo-landings that did not exist yet,” but fitness/ownership reviews should confirm whether unowned new prefixes are accepted.

## Tests: will fail vs need updating vs new

### Existing tests that fail if you **mutate the skill or showcase** (do not do that)

- `tests/test_seo_landing_side_project.py`
  - Skill: exact inventory, frontmatter, `$seo-landing`, audit-only no-write clauses, SHA of four references, LICENSE digest, no Claude paths, **must contain** `side-projects/seo-landings/<project-slug>/`.
  - Showcase: exactly one `<h1>`, `noindex, nofollow`, no canonical, no `<form>`, **zero** `http(s)`/`//` runtime URLs in HTML/CSS, `:focus-visible` + `prefers-reduced-motion` in CSS, no “Lighthouse 100” / “WCAG compliant” claims, versioned `browser-contract.mjs` CDP hooks.
  - Optional Chrome: `test_local_chrome_runner_exits_cleanly_after_contract_passes` serves **only** `SHOWCASE_ROOT`.
- `factory/tests/test_landing_api.py` showcase aggregate (6 files / pinned digest).

### Existing tests that do **not** automatically validate a new `seo-landings/` tree

- `test_structure.py` only requires the `side-projects` **root entry** to exist; nested new directories are allowed.
- `test_landing_architecture_boundaries.py` inventories `factory/.../landing*.py` only.
- No test currently walks `side-projects/seo-landings/`.

### Tests that need **new** coverage (do not rewrite the showcase tests)

Add a sibling module, e.g. `tests/test_winston_wolfe_seo_landing_v2.py`, that applies skill-derived gates to the **new** project:

- One H1; semantic landmark structure; system fonts only; no SVG; no external JS/CSS/fonts on first load (`external_runtime_urls` helper can be reused).
- Every local `src`/`srcset`/`href`/`url()` resolves to a real file (tech-spec §7 gate 2).
- JSON-LD parses if present; no invented LocalBusiness/FAQ/Review claims without brief facts.
- No first-load iframe/YouTube/map; JS ≤ 15 KB, single deferred file if any.
- `ASSETS.md` + `SERVER-SETUP.md` present; favicon if referenced.
- Honest robots: without a production origin, `noindex` (showcase pattern) rather than fake `index, follow` + invented canonical.
- Optional: reuse `browser-contract.mjs` **against the new URL**, writing evidence under this change package — do not change the runner’s versioned CDP contract unless necessary.
- Do **not** claim Lighthouse 100 / WCAG AA without measured artifacts (skill + showcase tests reject those phrases on the showcase; the new page should follow the same honesty rule).

Skill-procedure tests stay as-is. They fail only if SKILL.md is edited (including removing the `seo-landings/<project-slug>` path).

## Skill constraints that the landing itself can violate (manual / new-test surface)

From `SKILL.md` + `references/tech-spec.md` (not currently executed against generated projects):

- Generate mode needs domain, keywords, language/dir/`og:locale`, business type facts, CTA, image/video provenance — **ask, do not invent**. Character fiction must not be dressed as a real LocalBusiness with fake address/phone/geo.
- Forbidden: external libraries, SVG, Google Fonts, first-load iframes, missing referenced assets, raw brief XSS, fabricated PageSpeed scores.
- STOP POINT: show HTML before validation metrics.
- Copyright: Pulp Fiction is third-party IP. `ASSETS.md` must record rights; do not ship uncleared studio stills. Text should be clearly a fan/educational one-pager unless the user supplies license.

## Residual unknowns

- No production domain, canonical URL, target keywords, language (RU vs EN), or CTA destination in the change spec.
- “Second version” has **no v1 artifact** in this repo; v2 means a new slug, not a diff against an old page.
- Whether README + `NODE-SEO-SHOWCASE-LAB` must list `side-projects/seo-landings/` in the same PR (recommended for release hygiene; not currently test-enforced).
- Whether the page may be indexable: skill wants robots/sitemap/canonical; showcase forbids them without a real origin. **Default: noindex until origin is collected.**
- Browser/Lighthouse lab availability on the agent host (showcase Chrome test skips if Node/Chrome missing).
- Legal/IP clearance for character likeness and any images.
- Route domain is `api`; this work is a static frontend side-project, not an API contract change.

## Impact surface summary

| Action | Impact |
| --- | --- |
| Add `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/**` only | Existing automated tests should stay green. Need **new** tests to enforce the skill on this page. |
| Edit showcase or skill | Immediate failures in `test_seo_landing_side_project.py` and possibly factory showcase digest. |
| Invent domain/metrics/business facts | Skill/tech-spec violation; not caught until new tests or review. |
| README mention of the new side-project | Required before proposing a release that includes the tree. |
