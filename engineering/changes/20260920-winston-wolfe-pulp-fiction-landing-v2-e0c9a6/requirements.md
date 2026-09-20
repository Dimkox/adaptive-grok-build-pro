# Requirements — Winston Wolfe Pulp Fiction landing v2

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001: Project exists at `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/` with `index.html` and every locally referenced asset as a real file.
- [ ] AC-002: `html lang="ru-RU"`, `dir="ltr"`, exactly one H1, UTF-8 charset first in head, visible unofficial-fan attribution to Winston Wolfe / Pulp Fiction (1994).
- [ ] AC-003: `noindex, nofollow`; no canonical; no `og:url`; no invented origin in JSON-LD; `robots.txt` disallows `/` and has no Sitemap line; no `sitemap.xml`.
- [ ] AC-004: No `<form>`, `mailto:`, `tel:`, messenger links, invented phone/price strings, iframes, SVG, video, or third-party first-load resources.
- [ ] AC-005: Original still-life images only (no actor likeness); `ASSETS.md` records provenance; LCP image eager + `fetchpriority="high"`; method image lazy; AVIF/WebP/JPEG at 320–1920.
- [ ] AC-006: Copy does not claim official affiliation, services for hire, prices, guarantees, Lighthouse/PageSpeed scores, or WCAG certification.
- [ ] AC-007: Focused tests pass; `python3 scripts/grok_verify.py --mode pr` passes after product files change.

## Failure and edge cases

- Missing referenced image/CSS/favicon is a hard fail.
- Any generated face resembling Harvey Keitel is rejected and regenerated.
- Encoder absence for AVIF/WebP is a BLOCKER, not a JPEG-only ship.
- Lighthouse SEO near 60 from noindex is expected, not a reason to index.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none added
- Canonical-example deviations and evidence: none
- Intentional debt created, repaid, or accepted: none

## Non-functional requirements

- Security: meta CSP from actual features; `form-action 'none'`; `frame-src 'none'`; no secrets.
- Reliability: static files; JS-disabled complete render.
- Performance: LCP still-life; system fonts; no third-party first load.
- Observability: no analytics. Local verification receipt is the success signal.
