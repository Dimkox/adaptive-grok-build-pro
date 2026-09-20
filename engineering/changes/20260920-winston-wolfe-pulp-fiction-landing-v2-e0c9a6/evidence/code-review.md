# Code review — Winston Wolfe Pulp Fiction landing v2

- **Route:** `e0c9a65c0d53` (`code_reviewer`, read-only)
- **Change:** `20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`
- **Verdict:** **PASS** (with residual / process notes; not a ship-to-index verdict)
- **May open a PR:** **Yes**, for the isolated static side-project on `feature/winston-wolfe-landing-v2`. Local Trust CI / Lighthouse / Nu HTML were not run; those remain pre-merge/pre-host gates, not a reason to keep the tree unpublished as a PR.

Write owner spawn of `general_implementer` was blocked by a stale `frontend_implementer` lock (`write-owner-spawn-blocker.md`). Product files were written by the parent under that bounded ruling. That is process debt, not a product defect in the landing tree.

## Scope inspected

- `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/` (`index.html`, `robots.txt`, `ASSETS.md`, `SOURCES.md`, `SERVER-SETUP.md`, `README.md`, rasters + favicon)
- Change package: `change-spec.yaml`, `requirements.md`, analysis reports, `implementation-general-implementer.md`, `pulp-fiction-sources.md`, `generate_html.py`, focused tests
- Visual inspection of `images/_source/hero.jpg`, `images/_source/method.jpg`, `favicon.png`
- CSP construction in `generate_html.py` (`sha256_csp` over inline CSS and JSON-LD)

**Not independently re-hashed in this session:** a Python one-liner to recompute CSP hashes was denied by the shell circuit breaker (same-objective sensitive-action). Hashes in `index.html` match the generator constants `STYLE_HASH` / `JSON_HASH` (`sha256-B1oeI9ZELONwBigbVSeT3cCfV/c370qi5iBw5xhYEaI=` style, `sha256-zCxB3+7PgQKggXFaJBKT7ORBem3vCAa9aHEHOTFDmg4=` JSON-LD). Treat live hash drift as a test-review item if `generate_html.py` and `index.html` diverge later.

**Git diff vs `90078959`:** a `git diff` invocation was denied the same way. Inspection of the landing directory plus package evidence shows no skill, showcase, `.github/`, or `trust-ci/` files in this change’s documented write set. Reviewer did not mutate those trees.

## Checklist vs contracts

| Check | Result |
| --- | --- |
| Project path + real local assets | Pass — `index.html` and all `src`/`srcset`/`href` first-party files exist; AVIF/WebP/JPEG 320–1920 for hero and method |
| `lang="ru-RU"` `dir="ltr"` charset first, one H1 | Pass |
| `noindex, nofollow`; no canonical; no `og:url`; no sitemap; robots `Disallow: /` without Sitemap | Pass |
| No form, mailto, tel, iframe, SVG, video | Pass |
| Relative first-party images/favicon; click-through Wikipedia/IMDb only in footer | Pass (not first-load) |
| JSON-LD types | Pass — `@graph` is `Movie`, fictional `Person` (Winston Wolfe), `FAQPage`. Nested `Person` is Tarantino as director. No `LocalBusiness` / `Organization` / `WebSite` / `WebPage` / `Service` / `Offer` / `VideoObject`. Movie `@id` is Wikidata Q104123, not an invented host |
| CSP | Pass by construction — `default-src 'self'`; hashed `script-src`/`style-src`; `form-action 'none'`; `frame-src 'none'`; `object-src 'none'` |
| Actor likeness in rasters | Pass — hero is night sedan / case / coffee; method is gloves / thermos / linen / watch; favicon is geometric W. No Harvey Keitel face. `ASSETS.md` states no actor likeness and does not name the actor |
| Copy vs invented service | Pass — plot of «Ситуация с Бонни», Keitel credit, Palme/Oscar facts aligned with `pulp-fiction-sources.md`. Repeated «не услуга», no prices/phone/SLA. Method cards are film analysis, not an offer |
| Skill / showcase / Trust CI / GitHub Actions | No evidence of mutation in this package’s product write set |
| OpenAPI / events | `change-spec.yaml` contracts empty; this landing does not add an API |

## Findings

1. **Nit (non-blocking):** Architect IA used slug `winston-wolfe-v2`; implementer used `winston-wolfe-pulp-fiction-v2`. Clearer and still under `side-projects/seo-landings/`.
2. **Nit:** LCP `<img>` uses `fetchpriority="high"` and omits `loading="lazy"` (correct default eager). Requirement text said “eager”; HTML default is enough.
3. **Process:** Focused tests live under the change `evidence/` because `tests/test_winston_wolfe_seo_landing_v2.py` is a protected path. Characterization coverage is present; inventory tests of the seo-landing skill were not re-run in this review.
4. **Residual risk (accepted, documented):** Fan-page copyright/trademark in character names and film title; large binary image family; no production origin so indexing stays off. Unrun Lighthouse/Nu/host crawl are skill STOP POINTs, not fabricated scores.
5. **CSP recompute:** blocked in this session’s shell; generator and HTML currently agree by inspection.

## Forbidden outcomes (FORBID-001)

No invented production origin, no lead form, no actor likeness in rasters, no film still, no skill/showcase mutation observed, no GitHub Actions or Trust CI files in the landing write set.

## PR recommendation

**Yes — open/update the feature PR** with this static tree. Do not enable indexing, canonical, or sitemap on this commit. Merge remains subject to App-owned Trust CI on the exact PR SHA, not this review.

Do not treat this file as merge authority.
