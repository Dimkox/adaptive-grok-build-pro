# Winston Wolfe Pulp Fiction landing v2

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`
Created: 2026-09-20T04:06:41+00:00
Risk: medium
Complexity: standard
Domains: frontend (route mislabeled `api` because the repository has OpenAPI files; task_domains is empty)

## Problem

The user asked for a second-version landing page about Winston Wolfe from Pulp Fiction. This repository has no v1 character landing, no `side-projects/seo-landings/` tree, and no production origin. The only related artifact is the non-indexable skill showcase.

## Outcome

A visitor can open a local, static, unofficial Russian fan/tribute one-pager about the film character Winston Wolfe from *Pulp Fiction* (1994). The page is readable with JavaScript disabled, uses only first-party relative assets, is marked non-indexable, submits nothing, and does not claim official affiliation, hosting, measured PageSpeed, or real-world fixer services. Success is repository delivery of that tree through a pull request.

## Scope

### In scope

- New generate-mode project at `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/`.
- Semantic Russian one-pager, original still-life rasters, `ASSETS.md`, `SERVER-SETUP.md`, `robots.txt` that disallows crawling.
- Characterization tests for noindex, no form, no external runtime URLs, asset existence, no actor likeness claims.
- Isolated-branch pull request. Local verification and route reviews.

### Out of scope

- Invented domain, canonical, `og:url`, sitemap host, phones, form, prices, LocalBusiness, reviews, video, maps.
- Harvey Keitel likeness, film stills, studio marks, SVG, external fonts/libraries.
- Skill or showcase edits, Trust CI, GitHub Actions, factory/L5, OpenAPI, hosting, merge, tag, release, deploy.

## Constraints

- Backward compatibility: skill SHA inventory, showcase six-file digest, Trust CI, and product runtime stay byte-identical.
- Data/privacy: no personal-data collection, no backend, no secrets.
- Performance: zero third-party first-load requests; inline CSS; no JS unless measured later (budget ≤ 15 KB).
- Operational: `noindex, nofollow` until a later change supplies a real HTTPS origin. Lighthouse/LCP numbers are not reported before the HTML stop-point.

## Bounded rulings

1. Path slug is `winston-wolfe-pulp-fiction-v2` (task_analyst + repo_explorer). Architect's shorter `winston-wolfe-v2` is not used.
2. Language: `html lang="ru-RU"`, `dir="ltr"`, `og:locale="ru_RU"`.
3. Empty integration surface. `api-event-change` is a negative freeze of existing contracts.
4. HTML stop-point still applies: show the page before claiming validation metrics.
