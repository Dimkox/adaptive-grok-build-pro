# Task analysis — Winston Wolfe Pulp Fiction landing v2

Route: `e0c9a65c0d53`
Change: `20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`
Agent: `task_analyst` (read-only)
User request: «создай второую версию посадочнйо страницы под Винстона Вульфа из Криминального чтива»

This report freezes the bounded outcome, in/out of scope, testable acceptance criteria, locale defaults, no-domain indexing policy, likeness constraint, and human gates. It does not implement, approve HTML, measure Lighthouse, invent a domain, or authorize merge/deploy.

## Recovered facts

| Source | Fact used here |
| --- | --- |
| User prompt | Create a *second version* of a landing for Winston Wolfe from Pulp Fiction. Russian request. No brief, domain, contacts, backend, prices, or images supplied. |
| Repository search | No Winston Wolfe / Pulp Fiction / «Вульф» / «Криминальное чтиво» product files exist outside this empty change package. There is no v1 to upgrade. `side-projects/seo-landings/` does not exist. |
| `.agents/skills/seo-landing/SKILL.md` | Mode is **generate**. Collect domain, keywords, language/direction/`og:locale`, business identity, CTA/contacts, favicon permission, claim owner, media facts. **Do not invent** domain, keywords, phones, endpoints, prices, claims, schema identity, or measured scores. Missing domain/keywords normally stop before a project directory is created. Output under `side-projects/seo-landings/<slug>/`. **STOP POINT**: show HTML and wait for explicit user OK **before** validation and the final report. |
| `references/tech-spec.md` §3, §10, §12, OUTPUT | Canonical/`og:url`/JSON-LD `@id` are absolute URLs. No backend → omit the form (never invent an endpoint). Never invent marketing facts. Image rights go in `ASSETS.md`. Lighthouse/LCP numbers only from pinned runs on a served page; unrun gates are `BLOCKER`, not estimates. |
| Showcase `side-projects/seo-landing-showcase/` | Local Russian static page: `lang="ru"`, `noindex, nofollow`, **no** canonical, **no** `og:url`, **no** `<form>`, relative `styles.css`, no JS, no images, no sitemap/robots host. Footer states indexing is off until a canonical domain is assigned. Lighthouse SEO 60 was expected because of crawl blocking, not a product defect. |
| `tests/test_seo_landing_side_project.py` | Showcase contracts: one H1; `noindex, nofollow`; no canonical; no form; zero external runtime URLs; `:focus-visible`; `prefers-reduced-motion`; must not claim `Lighthouse 100` or `WCAG compliant` in the HTML. |
| `AGENTS.md` | PR-only delivery. No GitHub Actions. Local `grok_verify.py --mode pr` is preflight. Merge needs the App-owned Trust CI check on the exact PR SHA. No `.env`/secrets. No production writes without an exact delegated grant. |
| Active route | `write_agent=general_implementer`; reviews=`code_reviewer` + `test_reviewer`; `required_evidence=verification, code_review, test_review`; `human_gates=[]`; `domains=["api"]` (misclassified); quality profiles `base` + `contracts`; `workflow_skills` include `api-event-change` although this change has no API/event surface. |

## Mode and “v2” ruling

This is **generate**, not `fix-existing` and not `audit-only`.

“Вторая версия” does **not** mean mutate the existing skill showcase, reconstruct a missing v1, scrape an external fan site, or invent a predecessor tree. Treat v2 as the **first** repository landing for this subject, labeled `v2` in the directory name and visible copy.

Default output path (skill §1; user did not name another directory):

```
side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/
```

Leave `side-projects/seo-landing-showcase/` and `.agents/skills/seo-landing/` unchanged except if a new characterization test file is added under `tests/`.

## Bounded outcome

A visitor can open a **local, static, unofficial Russian fan/tribute one-pager** about the *character* Winston Wolfe from the film *Pulp Fiction* (1994), served from the project folder (for example `python3 -m http.server` on that directory). The page is readable with JavaScript disabled, uses only first-party relative assets, is marked non-indexable, submits nothing, and does not claim official affiliation, production hosting, measured PageSpeed, or business services.

Success is **repository delivery of that static tree through a pull request**, not a live site.

## In scope

- One static multi-file landing under `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/` (`index.html` plus every local file it references: CSS and, only if needed, one deferred `script.js` ≤ 15 KB).
- Semantic HTML5 one-pager: header/nav/main/footer, exactly one H1, in-page CTA anchors only.
- Character-faithful **original** copy in Russian: fixer/problem-solver tone, film-context attribution, unofficial-fan disclaimer. Short attributed character flavour is allowed; long copyrighted dialogue is not.
- Original visual system: CSS, system fonts, geometric/typographic art. Optional original PNG/AVIF/WebP/JPEG variants **only** if generated as original work (not actor/studio stills) and listed in `ASSETS.md`.
- `ASSETS.md` provenance for every raster (including derivatives). If there are no rasters, say so explicitly (showcase pattern).
- `SERVER-SETUP.md` as **local preview + production-boundary notes**, not a deployment.
- `robots.txt` that blocks crawlers and **omits** a `Sitemap:` line (no real host).
- Characterization tests for the no-domain / no-form / no-likeness / no-claim contracts; reuse or copy the showcase browser-contract pattern for 320/768/1280/1920 overflow, first-tab focus, and reduced-motion when Node/Chrome exist (skip cleanly when they do not).
- Change-package fill-in (brief, requirements, architecture, test plan) consistent with this report, then PR-only delivery.
- Local `python3 scripts/grok_verify.py --mode pr` after product files change; then `code_reviewer` and `test_reviewer` reports.

## Out of scope (explicit non-goals)

- Inventing a production domain, canonical URL, `og:url`, JSON-LD `@id` host, sitemap `<loc>` host, or `Sitemap:` URL.
- Switching `robots` to `index, follow` in this change.
- Phones, messengers, emails, maps, addresses, geo, prices, rates, “services”, booking, or a lead form (no backend was supplied; tech-spec §10 forbids a form that posts nowhere).
- Invented marketing claims, guarantees, comparisons, reviews, case studies, ratings, or “100/100 PageSpeed” / “WCAG certified” copy.
- `LocalBusiness`, `WebSite`, `BreadcrumbList`, `Review`/`AggregateRating`, `FAQPage` as a Google feature, or `VideoObject` (no verified identity, hierarchy, reviews, or media facts).
- Copying or approximating **Harvey Keitel’s likeness**, film stills, official posters, studio/Miramax/Disney marks, or third-party fan-site HTML/CSS.
- SVG images, external fonts, frameworks, analytics, cookie banners, chats, YouTube/maps on first load, GitHub Actions, Trust CI / factory / OpenAPI / event-schema changes.
- Hosting, DNS, TLS, CDN, deploy, merge to `main`, tagging, GitHub Release, or any production write.
- Reconstructing a fictional v1, editing the existing showcase, or treating this as an API change because the route currently says `domains=api`.
- Claiming Lighthouse, LCP, or WCAG numbers before the HTML stop-point approval **and** pinned measurement on a served URL.

## Language and locale defaults

The user did not supply the three separate skill inputs (BCP-47 language, base direction, Open Graph locale). Defaults for this generate:

| Field | Default | Rule |
| --- | --- | --- |
| Visible copy | Russian | Request language. English proper names stay in Latin: Winston Wolfe, Pulp Fiction, Quentin Tarantino. |
| `<html lang>` | `ru` | Matches the showcase. Not copied into `og:locale`. |
| Base direction | `ltr` (omit `dir` or set `dir="ltr"`) | Russian is LTR. Do not emit `dir="rtl"`. |
| `og:locale` | Omit while non-indexable; if emitted, `ru_RU` | Open Graph `language_TERRITORY`, never `ru-RU`. |
| `hreflang` / alternates | None | Single-language landing; invented alternates are a generation error. |
| Keywords | Factual topic only | «Винстон Вульф», «Winston Wolfe», «Криминальное чтиво» / Pulp Fiction. No invented ranking keyword list. |

Do not silently copy one of these three values across formats.

## Indexing policy without a domain

Skill generate-mode wants a domain before canonical/OG/JSON-LD absolute URLs. The user already asked to create the page and supplied none. **Bounded adaptation (showcase precedent), not an invented host:**

1. `<meta name="robots" content="noindex, nofollow">`.
2. Do **not** emit `<link rel="canonical">`, `og:url`, Twitter URL, or JSON-LD `@id`/`url` with a fake origin (`example.com`, `localhost`, GitHub Pages guesses, etc.).
3. All first-party `href`/`src`/`srcset`/CSS `url()` are **relative** (tech-spec “absolute paths for ALL resources” is suspended until a real HTTPS origin exists). External `https:` runtime assets are forbidden.
4. `robots.txt`: `User-agent: *` + `Disallow: /`. No `Sitemap:` line.
5. Omit `sitemap.xml`, or if present it must not contain an invented `<loc>` host. Crawlability HTTP-200-on-deployed-host is a documented **BLOCKER** until a domain exists — not a fabricated pass.
6. Footer/README must state that indexing stays off until a later change supplies a real canonical HTTPS origin, then re-checks absolute URLs and only then may drop `noindex`.
7. Expected lab effect (showcase): Lighthouse SEO can sit near **60** because crawl is blocked. That is compliance with this policy, not a reason to add `index, follow`.

## Image and likeness constraint

- Do **not** copy, crop, trace, “in the style of the actor,” or photorealize **Harvey Keitel**.
- Do **not** use Pulp Fiction stills, official key art, DVD covers, or studio logos.
- Allowed: original CSS shapes, typography, color (dark suit / black car / clinical-cleaner mood without reproducing copyrighted frames), or original non-likeness rasters generated for this tree and recorded in `ASSETS.md` (creator, source, license, adaptation rights). Public availability of a still is not permission (tech-spec §12).
- Decorative images: `alt=""`. Informative images: purpose-based alt that does not name the actor as if the photo were him.
- Favicon: do **not** invent a studio/brand mark. Either omit (showcase; expect a local favicon 404 in Best Practices) or ship an **original** geometric PNG ≥48×48 with explicit ASSETS.md “original, not studio IP / not actor likeness.”
- Tech-spec §6: no SVG images.
- No images available and none generated → omit `<img>`/`<picture>`/OG image tags rather than pointing at missing files.

## Human gates

Route `human_gates` is empty, so **scope/design does not stop implementation**. Two gates still apply:

### Gate A — HTML stop point (skill §4 / tech-spec OUTPUT)

After the draft landing exists, the write agent **shows the HTML** (local server URL or files) and asks whether that version is OK.

- Do **not** run Lighthouse, Nu validator-as-final-report, or write PageSpeed/LCP/WCAG scores until the user explicitly confirms the HTML.
- Remarks → fix → ask again.
- If post-approval validation changes the approved HTML, obtain renewed approval before reporting.

This is a **process gate**, not a Trust CI / signed-security approval. It does not authorize merge, hosting, or indexing.

### Gate B — no Lighthouse claims without measurement

After Gate A:

- Serve the project directory; run pinned Lighthouse `13.4.1`, 3 runs, median; keep artifacts under the change evidence or the project `reports/`.
- Report only measured numbers with command + artifact path.
- Do not put “Lighthouse 100”, “PageSpeed 100”, or “WCAG 2.1 AA certified” in the landing copy (showcase test forbids the first two patterns).
- Manual accessibility checks (tech-spec §8) stay pass/fail evidence, not certification.
- Unavailable Chrome/Nu/deployed host → `BLOCKER: <reason>`, never an estimate.

No other human gates are in the route. Merge, deploy, indexing, and production origin remain **future, separately delegated** work.

## Testable acceptance criteria

Write these into `requirements.md` / `change-spec.yaml` as the typed bar. All are checkable on the tree without a domain.

1. **Given** no Winston Wolfe landing in this repository, **when** the change is implemented, **then** a new project exists at `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/` with `index.html` and every locally referenced asset present as a real file.
2. **Given** that `index.html`, **then** `<html lang="ru">`, exactly one `<h1>`, UTF-8 charset as the first head element, semantic landmarks, and visible unofficial-fan attribution to the character Winston Wolfe / film Pulp Fiction (1994).
3. **Given** no production origin, **then** `meta name="robots" content="noindex, nofollow"`, no `rel="canonical"`, no `og:url`, and no invented absolute origin in JSON-LD.
4. **Given** no contacts or backend, **then** the HTML contains no `<form>`, `mailto:`, `tel:`, messenger deep links, or invented phone/price strings.
5. **Given** the HTML and CSS, **then** `external_runtime_urls(...)` (same idea as the showcase test) is empty: no third-party scripts, styles, fonts, iframes, images, or CSS `url(https:...)`.
6. **Given** asset references, **then** every local `src`/`href`/`srcset`/CSS `url()` is relative and resolves to a file in the project folder.
7. **Given** raster or favicon files, **then** `ASSETS.md` lists creator/source/license and none are described as Harvey Keitel, film stills, or studio marks; filenames and alt text do not claim actor likeness.
8. **Given** the copy, **then** it does not claim official affiliation, services for hire, prices, guarantees, Lighthouse/PageSpeed scores, or WCAG certification.
9. **Given** 320/768/1280/1920 viewports on a local server, **then** no horizontal overflow; `:focus-visible` exists; `prefers-reduced-motion: reduce` disables nonessential motion; first Tab reaches a useful control (skip link if repeated nav exists).
10. **Given** JS is used at all, **then** it is one `defer` file, ≤ 15 KB, and the page remains complete with JS disabled.
11. **Given** product files changed, **when** `python3 scripts/grok_verify.py --mode pr` runs, **then** selected profiles pass; focused landing tests pass or skip only for missing optional Node/Chrome.
12. **Given** HTML not yet user-approved, **then** the implementation report does not include Lighthouse/LCP numbers. After approval, any scores are measured artifacts or explicit BLOCKERs.

## Route misclassification (do not “fix” by adding APIs)

The hook set `domains=["api"]`, `workflow_skills` includes `api-event-change`, and quality profile `contracts` because the repo has OpenAPI under `engineering/contracts/openapi`. This task has **no** HTTP API, events, queues, or schema migrations.

- Write owner stays `general_implementer` (route authority).
- Do **not** add OpenAPI, factory landing APIs, or event contracts to satisfy the mislabel.
- Interpret `contracts` as **page contracts**: noindex, relative assets, no form, no invented claims, asset existence.
- Reviewers stay `code_reviewer` and `test_reviewer` only. Do not spawn `frontend-change` as a write skill; the landing is still static HTML/CSS owned by `general_implementer`.

## Delivery, verification, rollback

- Isolated branch + pull request. No direct push to `main`. No `.github/workflows/`.
- Local evidence: verification receipt, `code_review`, `test_review`, bound to the final tree fingerprint.
- Merge authority remains App-owned `adaptive-trust-ci/verified@<policy-sha12>` on the exact PR head. This report is not merge authority.
- Rollback: delete the new `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/` tree and its tests; no data migration; no production host.
- Do not read `.env`, keys, or credential stores.

## Open items (ask only if implementation is blocked)

Do **not** block the static noindex generate on these. Revisit only if the user volunteers them:

- Real HTTPS origin (unlocks canonical, sitemap, `index, follow`).
- Contacts / form destination / privacy text.
- User-supplied original images and favicon permission.
- Explicit `en` locale instead of `ru`.
- Video ID + upload date (otherwise no video block).

Until then, implement the unofficial local v2 tribute under the constraints above, stop for HTML approval, and do not claim scores or search effects.
