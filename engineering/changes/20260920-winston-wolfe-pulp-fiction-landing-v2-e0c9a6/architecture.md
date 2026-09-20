# Architecture — Winston Wolfe Pulp Fiction landing v2

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Authority for the design is [`evidence/analysis-architect.md`](evidence/analysis-architect.md), with path slug from [`evidence/analysis-task-analyst.md`](evidence/analysis-task-analyst.md).

## Current behavior

No Winston Wolfe landing exists. `side-projects/` contains only the skill showcase. `side-projects/seo-landings/` does not exist.

## Proposed behavior

New isolated static generate-mode landing at `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/`. Local `python3 -m http.server` preview. `noindex, nofollow`. Relative assets. No backend.

## Components and boundaries

| Path | Role |
| --- | --- |
| `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/` | New landing (only write surface besides tests + this change package) |
| `tests/test_winston_wolfe_seo_landing_v2.py` | New focused tests |
| `.agents/skills/seo-landing/**` | Untouched |
| `side-projects/seo-landing-showcase/**` | Untouched |
| OpenAPI / factory / Trust CI / packages | Untouched |

IA: skip link → sticky header → hero + LCP still-life → character → plot role → method cards + lazy still-life → not-a-service disclaimer → film-fact `<details>` FAQ → footer with Wikipedia/IMDb HTTPS links in the current tab.

## Data flow

None. Static files. In-page anchors only.

## API and event contracts

Empty. See [`evidence/analysis-integration-architect.md`](evidence/analysis-integration-architect.md).

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority.

- Applicable rule IDs: none
- Applicable canonical example IDs/versions: none
- Open or overdue debt IDs: none
- Expected governance handoff or receipt impact: none

## Bitrix-specific impact

- Modules/events/agents/components affected: none
- Cache and managed cache impact: none
- Installation/update/uninstall impact: none
- Core modification: forbidden unless explicitly approved.

## Decisions

- Slug `winston-wolfe-pulp-fiction-v2` over architect `winston-wolfe-v2`.
- Omit `sitemap.xml` and `script.js`. Inline all CSS.
- Optional JSON-LD: `Movie` + fictional `Person` + metadata-only `FAQPage`. Omit LocalBusiness/Organization/WebSite/WebPage/Review/Offer.
- Original still-lifes only; no people in images.

## Risks and mitigations

- Copyright/trademark: short plot facts + disclaimer; no long quotes or official art.
- Likeness leak: still-life-only masters; reject any face.
- Binary size: two image families only.
- Encoder gap: BLOCKER if AVIF/WebP tools missing.
