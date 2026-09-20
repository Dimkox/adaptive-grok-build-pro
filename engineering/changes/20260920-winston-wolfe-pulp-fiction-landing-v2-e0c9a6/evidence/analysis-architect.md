# Architecture analysis — Winston Wolfe Pulp Fiction landing v2

Route: `e0c9a65c0d53`
Change: `20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`
Write owner: `general_implementer`
Inspected skill: `.agents/skills/seo-landing/references/tech-spec.md` v1.11
Showcase precedent: `side-projects/seo-landing-showcase/`

## Recommendation

Ship a **new isolated static generate-mode landing** at
`side-projects/seo-landings/winston-wolfe-v2/`. There is **no v1 tree** in this
repository; `v2` is the project slug, not a patch of an existing page. Do not
create a sibling `winston-wolfe/` or `winston-wolfe-v1/`.

Treat this as an optional side-project artifact, not product runtime. Follow
tech-spec v1.11 except where the **no production origin** constraint collides
with absolute-URL / crawlability rules. Those collisions already have a
reviewed precedent in the showcase (PR #19): `noindex, nofollow`, no
canonical, no `og:url`, relative first-party assets, no sitemap. Record each
exception in `SERVER-SETUP.md` as a showcase-class pre-production boundary,
not as an SEO win.

The route classifier `domains=api` and quality profile `contracts` do **not**
authorize a new HTTP API, OpenAPI document, event schema, or factory contract.
`change-spec.yaml` contracts stay empty. No Trust CI, GitHub Actions, L5,
published package, VERSION, or product-runtime file is in scope.

Preserve byte-for-byte:

- `.agents/skills/seo-landing/**` (exact inventory + reference SHA-256 tests)
- `side-projects/seo-landing-showcase/**`
- `trust-ci/`, `.github/`, `factory/`, `delivery/`, `packages/`, migrations

## Bounded rulings (conflicts)

| Collision | Ruling |
| --- | --- |
| Tech-spec absolute resource URLs vs no origin | Relative local URLs for every first-party asset. Never invent a host. |
| Tech-spec `index, follow` + canonical vs no origin | `<meta name="robots" content="noindex, nofollow">`. Omit canonical and `og:url`. |
| Tech-spec `sitemap.xml` + `Sitemap:` line vs no origin | Omit `sitemap.xml`. `robots.txt` is `User-agent: *` / `Disallow: /` with **no** Sitemap line. |
| Tech-spec Lighthouse SEO ≥ 90 vs noindex | SEO category is an **expected lab fail** (`is-crawlable`). Do not lift `noindex` to chase the score. Performance / accessibility / best-practices still target ≥ 90 when Lighthouse actually runs. |
| Tech-spec `@id` absolute on WebSite/WebPage vs no origin | Omit `WebSite`, `WebPage`, `Organization`, `LocalBusiness`, `BreadcrumbList`. Optional `Movie`/`Person` may use public Wikidata/Wikipedia/IMDb identifiers only. |
| Skill STOP POINT vs repo delivery | Implementer may write files and run local contracts. Do **not** report LCP/PageSpeed numbers until the HTML is user-visible and the gate has actually run. Unrun gates are `BLOCKER`, never estimates. |
| Form / CTA | No backend → **no form**, not even a stub that posts to the current page. In-page anchors only. |
| Video / maps | Omit. No facade, no iframe, no `VideoObject`. |
| Actor likeness | Original generated still-lifes only. No Harvey Keitel (or any actor) face, body, or recognizable portrait. Actor **credit in text** is a film fact and is allowed. |
| SVG / webfonts / JS libraries | Forbidden. System font stack only. Prefer **zero JS**. |

## Information architecture

Single responsive document, `lang="ru-RU"` `dir="ltr"`, one H1, landmarks.
Sticky CSS header + skip link (header/nav is repeated chrome). No hreflang.

Suggested copy length: `<title>` ≤ 60 characters, description ≤ 160.

Working title: `Винстон Вульф — Волк из «Криминального чтива»`
Working description: unofficial Russian fan page about the 1994 film character;
not a real fixer service; not affiliated with the rights holders.

### Sections (in order)

1. **Skip link** — `Перейти к содержанию` → `#content`.
2. **Header** — text mark `THE WOLF` / `Вульф`; in-page nav: Персонаж, Метод, Факты, О странице.
3. **Hero** (`#top`, LCP) — eyebrow `Фан-страница · 1994`; H1 about Winston Wolfe / «Волк» from *Pulp Fiction* / «Криминальное чтиво»; lead that this is a character study, not a service; two in-page CTAs (`#character`, `#facts`); trust chips: `Не услуга`, `Без заявок`, `Только факты фильма`.
4. **Hero still-life** — original LCP `<picture>` (eager, `fetchpriority="high"`, no `loading`). `sizes="(min-width: 1200px) 1200px, 100vw"`.
5. **Кто такой Вульф** (`#character`) — fictional cleaner/fixer **in the plot**; Harvey Keitel as the actor (credit); Quentin Tarantino, 1994, US crime film. No invented biography, age, rates, or “real-world” career.
6. **Зачем он в сюжете** — Bonnie / cleanup situation as **plot summary**, not a how-to. Short paraphrase only; do not paste long copyrighted dialogue.
7. **Метод** (`#method`) — 4–6 film-derived traits (calm, dress, time, coffee, professionalism) as analysis cards. Explicitly **not** an offer. Second still-life, `loading="lazy"`.
8. **Это не услуга** (`#disclaimer`) — visible fan-tribute panel: no phone, address, prices, SLA, availability, or booking; not affiliated with Miramax / the filmmakers / the actors; trademarks belong to rights holders.
9. **Факты / FAQ** (`#facts`) — `<details>/<summary>` only (zero JS). Questions are film facts (who is he, who played him, what film/year, is this a real service → no). Not service FAQ.
10. **Footer** — local identity of this repository side project; optional HTTPS reference links in the **current tab**: Russian Wikipedia `Криминальное чтиво`, IMDb `tt0110912`. No `tel:`, `mailto:`, messengers.

### Explicitly omitted blocks

Form, reviews/ratings widgets, carousel, modal, map, video, cookie banner, chat, counters, sticky phone CTA, LocalBusiness hours, prices.

## Target tree

```text
side-projects/seo-landings/winston-wolfe-v2/
  index.html
  favicon.png
  robots.txt
  ASSETS.md
  SERVER-SETUP.md
  README.md
  images/
    hero.<sha12>-{320,640,768,1024,1280,1920}.{avif,webp,jpg}
    method.<sha12>-{320,640,768,1024,1280,1920}.{avif,webp,jpg}
```

Omit `styles.css` (inline all CSS in one `<style>` in `<head>`).
Omit `script.js` unless a later measurement forces ≤15 KB `defer` JS — none is required for this IA.
Omit `sitemap.xml`.
Omit `DEPENDENCIES.md` (zero third-party runtime deps).
Do not place `browser-contract.mjs` or Lighthouse `reports/` inside the landing; reuse the existing showcase runner and store lab artifacts under this change package `evidence/`.

Optional README one-liner at repository root next to the existing showcase bullet. Do not bump `VERSION` or rewrite Current-state identity.

## Asset list

All raster. No SVG. No hotlinked posters, screenshots, or actor photos.

| ID | Role | Loading | Formats × widths | Notes |
| --- | --- | --- | --- | --- |
| `hero` | LCP still-life | eager + `fetchpriority="high"` | AVIF/WebP/JPEG × 320/640/768/1024/1280/1920 | Night sedan, briefcase, coffee steam, wet asphalt; **no people** |
| `method` | Below-fold still-life | `loading="lazy"` | same matrix | Black gloves, thermos, linen; **no people, no gore** |
| `favicon.png` | Stable icon | n/a | PNG square, multiple of 48 px, ≥48×48 | Geometric “W” / chevron mark, not a wolf portrait and not a film logo |
| OG/Twitter image | share tags | n/a | reuse `hero.<sha12>-1280.jpg` | Relative path; `og:image:width/height/alt`; **no** `og:url` |

Fingerprint: SHA-256 of each **master** source, first 12 hex chars, shared across that family's derivatives (`hero.a1b2c3d4e5f6-320.avif`). Only fingerprinted URLs may later be `immutable`. `index.html`, `favicon.png`, `robots.txt` stay unhashed / revalidate.

LQIP: CSS background color + `aspect-ratio` on the `<picture>` wrapper. No `data:` URIs, so CSP `img-src` can stay `'self'`.

`ASSETS.md` rows for every master and derivative: generator (session image tool), original work, license = repository contribution, **explicit “no actor likeness”**, no third-party stills, allowed adaptation = format/resize only.

If AVIF/WebP encoders are missing on the implementer host, that is a **BLOCKER**, not a JPEG-only ship.

## HTML / CSS / JS contract

- First child of `<head>`: `<meta charset="utf-8">` within 1024 bytes; UTF-8 no BOM.
- Viewport: `width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover` **and** safe-area padding using `max(design, env(safe-area-inset-*))` on header, container, footer.
- `referrer`: `strict-origin-when-cross-origin`.
- `og:locale`: `ru_RU` (underscore). Do not copy `ru-RU` into OG.
- `og:type`: `website`. `og:title` / `og:description` / `og:image` (+ width/height/alt). Twitter `summary_large_image`.
- Font: `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Helvetica Neue", Arial, sans-serif`.
- Logical CSS (`margin-inline`, `padding-inline`, `text-align: start`). Container max-width 1200px.
- Contrast: text ≥ 4.5:1, non-text UI ≥ 3:1; visible `:focus-visible`; `@media (prefers-reduced-motion: reduce)` disables smooth scroll and nonessential motion.
- Minify HTML/CSS. No inline event handlers. No `javascript:` / unexpected `data:` URLs.
- External links: HTTPS, current tab, no `target="_blank"` unless a later UX reason is recorded.
- Encode all copy for HTML/attribute/JSON-LD context; JSON-LD serialized then `<` → `\u003c`.

Palette (homage, not a copied poster): near-black, cream, mustard, deep red. Decorative CSS shapes only — no SVG `<img>` or inline SVG.

## schema.org types (and omissions)

JSON-LD is **optional metadata**, not a rich-result claim (page is `noindex`).

### Emit (if facts remain source-backed at implement time)

- `Movie` — *Pulp Fiction* / «Криминальное чтиво», year 1994, director Quentin Tarantino. `@id` and `sameAs` only from verified public identifiers, e.g. Wikidata `Q104123`, IMDb `tt0110912`, Russian Wikipedia film article. Omit any property that cannot be verified (exact theatrical date if unsure → year only).
- `Person` — fictional character Winston Wolfe / «Волк» / The Wolf, `description` stating fictional status, `character` of that Movie. **Do not** reuse Harvey Keitel's Wikidata `@id` for the character. Omit `sameAs` if no character-specific public page exists.
- `FAQPage` — only if the visible `<details>` set is complete and 1:1 with the markup. Report as metadata-only. Questions must not describe a purchasable service.

`@graph` is allowed. Entities we do not own use public `@id`s or blank nodes. Never mint `@id` on an invented origin.

### Omit

| Type | Reason |
| --- | --- |
| `LocalBusiness` (+ subtypes) | No real address, phone, geo, or business. |
| `Organization` | No truthful publisher identity or legal name for this fan page. |
| `WebSite` | Not a domain/subdomain home; no canonical root URL. |
| `WebPage` | Would require a canonical page URL. |
| `BreadcrumbList` | No real parent URLs / site hierarchy. |
| `Review` / `AggregateRating` | No eligible sourced reviews; would read as self-serving. |
| `VideoObject` | No video facts, no player. |
| `Speakable` | Not a US English news publisher. |
| `Service` / `Offer` / `PriceSpecification` | Fan tribute, not a fixer service. Invented prices/availability are forbidden. |

Do not claim Google FAQ/Movie rich results. Syntax validity ≠ eligibility.

## CSP notes

Generate the policy from **this page's actual features** (inline CSS, local images, optional JSON-LD, no JS file, no frames, no forms, no YouTube).

Preview (also as `<meta http-equiv="Content-Security-Policy">` so local `http.server` has a policy):

```
default-src 'self';
script-src 'sha256-<jsonld>' … ;   /* hash each application/ld+json block; omit 'self' if no .js */
style-src 'sha256-<css>';          /* hash the exact inline <style> bytes; never style-src 'unsafe-inline' */
img-src 'self';                    /* drop data: because LQIP is CSS color */
font-src 'self';
connect-src 'self';
object-src 'none';
base-uri 'self';
form-action 'none';
frame-src 'none';
frame-ancestors 'none'
```

`frame-ancestors` is ignored in meta CSP; `SERVER-SETUP.md` still documents it for a future header.

Rules:

- No `unsafe-inline` / `unsafe-eval` in `script-src`.
- No `youtube-nocookie.com` in `frame-src`.
- Recompute hashes in the same commit as any CSS or JSON-LD change.
- Production header rollout (report-only → enforce, HSTS, HTTP→HTTPS) is **documented only**. This change does not deploy a host. Until an origin exists, do not enable HSTS `preload` or claim Brotli is served.
- `form-action 'none'` matches the omitted form.

`SERVER-SETUP.md` contents: local `python3 -m http.server` from the project directory; noindex boundary; relative-asset exception; omitted sitemap; security-header checklist copied from `references/server-config.md` as **future host instructions**; honest gzip-only until a host with ngx_brotli is named; MIME types for HTML/PNG/AVIF/WebP/JPEG/`robots.txt`.

`robots.txt`:

```
User-agent: *
Disallow: /
```

## Test strategy

Add `tests/test_winston_wolfe_landing_v2.py`. Do **not** expand `SeoLandingSkillTests` inventory. Reuse `external_runtime_urls()` ideas and the existing `browser-contract.mjs` against a temp server of **this** directory.

### P0 automated (always-on unittest)

- Tree exists; every `src` / `srcset` / `href` / `imagesrcset` / icon / OG local URL resolves to a real file.
- `lang="ru-RU"`, `dir="ltr"`, `og:locale` = `ru_RU`, one H1, charset first.
- `robots` = `noindex, nofollow`; no `rel=canonical`; no `og:url`; no `sitemap.xml`; `robots.txt` disallows `/` and has no Sitemap line.
- No `<form>`, `<iframe>`, `<svg>`, `<video>`, YouTube, maps, `tel:`, analytics.
- Zero external runtime http(s) resources in HTML/CSS.
- Image families: AVIF+WebP+JPEG at 320/640/768/1024/1280/1920; LCP `<img>` has `fetchpriority="high"` and no `loading="lazy"`; method image is lazy.
- Filenames: content-hash fragment `.[0-9a-f]{8,}.` on image variants; `favicon.png` unhashed.
- System font stack present; no Google Fonts / `@font-face` urls.
- JSON-LD (if present) parses; allowed types ⊆ `{Movie, Person, FAQPage}`; forbidden types absent; no prices/availability/Offer.
- Visible disclaimer / «не услуга» / fan-tribute wording.
- `ASSETS.md` states original generation and no actor likeness.
- No `script.js`, or if added later: one file, `defer`, ≤ 15 KB, local only.

### P1 lab (skip if Node/Chrome missing, same pattern as showcase)

- Serve directory; run `browser-contract.mjs` at 320/768/1280/1920; no horizontal overflow; skip-link on first Tab; reduced-motion disables smooth scroll.
- Optional W3C Nu (`curl` to validator.w3.org) — network absence is `BLOCKER`, not a fake pass.
- Optional Lighthouse 13.4.1 × 3, median. Expect SEO ~60 from noindex. Do not write unverified scores into README.

### P2 manual (record pass/fail, do not claim WCAG certification)

Keyboard order, focus visibility, 200% zoom/reflow, contrast of red/cream on black, `details` keyboard, skip-link target, portrait+landscape safe-area, JS-disabled rendering (must be complete).

### Regression

`python3 scripts/grok_verify.py --mode pr` after implementation. Existing `tests/test_seo_landing_side_project.py` must stay green (skill hashes unchanged, showcase unchanged).

## Rollback

Trigger: missing assets, accidental indexability, actor likeness, invented prices/origin, form/iframe/third-party, skill/showcase/Trust CI drift, verifier red.

Application rollback: delete `side-projects/seo-landings/winston-wolfe-v2/` (and the focused test + optional README bullet) in one revert. No database, no host, no package rebuild.

Forward-fix: replace a single image family + hashes + HTML references in the same commit when the defect is local.

Verify after rollback: path absent, showcase/skill tests pass, `grok_verify.py --mode pr` green.

## Implementation sequence for `general_implementer`

1. Failing focused tests for the missing tree and noindex/asset contracts.
2. Generate two likeness-free masters; derive the 36 responsive files + favicon; write `ASSETS.md`.
3. Write `index.html` (inline CSS, relative assets, disclaimer, optional JSON-LD) + `robots.txt` + `SERVER-SETUP.md` + project `README.md`.
4. Compute CSP hashes from final CSS/JSON-LD bytes; embed meta CSP.
5. Green focused tests + PR verifier. Independent `code_reviewer` / `test_reviewer` after that tree freeze.

## Residual risks

- **Copyright / trademark.** Film names and short plot facts are used as commentary. Long quotes, official artwork, and actor likeness remain out. Residual legal risk is inherent to fan pages; the disclaimer does not replace counsel.
- **Likeness leak.** Image models can still emit a recognizable face. Reject and regenerate any master that looks like Harvey Keitel or another actor; tests cannot fully see this — reviewers must inspect the rasters.
- **Noindex vs “SEO landing”.** The page is structurally SEO-ready and **intentionally not crawlable**. Enabling index/canonical is a later change with a real HTTPS origin.
- **Lighthouse SEO / favicon.ico.** Local `http.server` may 404 `/favicon.ico` even with `favicon.png` linked; Best-Practices can drop a few points. Do not add a fake absolute origin to paper over it.
- **Binary size.** 36 image variants can bloat Git. Keep JPEG quality moderate; do not add a third family.
- **Encoder gap.** Missing `avifenc`/`cwebp`/`magick` blocks the image matrix.
- **JSON-LD vs CSP.** Forgetting to hash `application/ld+json` blocks will break the page under enforcing CSP.
- **Scope creep.** A “real fixer” offer, prices, WhatsApp, YouTube clip, or production domain must not be added in this change.

## Out of scope

Production hosting, DNS, TLS, indexing, human security approvals, Trust CI policy/holdout, GitHub Actions, factory/L5/M8/M9, published ZIP rebuild, skill edits, showcase edits, Bitrix, OpenAPI.
