# integration_architect — Winston Wolfe Pulp Fiction landing v2

Change: `20260920-winston-wolfe-pulp-fiction-landing-v2-e0c9a6`  
Route: `e0c9a65c0d53`  
Agent: `integration_architect` (read-only except this report)  
Question: are any real external-system, API, webhook, form, or event integrations required for this landing?

**Ruling: no. This change has an empty integration surface.** Do not invent adapters, OpenAPI paths, webhooks, outbox tables, queues, reconciliation jobs, form backends, analytics pixels, or third-party widgets. The user asked for a static character landing. The route’s `api` domain is repository background, not task demand.

---

## 1. What was actually asked

User objective (change-spec `OBJ-001`, route `task`):

> создай второую версию посадочнйо страницы под Винстона Вульфа из Криминального чтива

That is a static one-pager about a fictional Pulp Fiction character. The brief, requirements, architecture, and `change-spec.yaml` are still stubs: no domain, no lead URL, no CRM, no messenger, no phone, no analytics, no hosting origin. Sibling reports (`analysis-repo-explorer.md`, `analysis-docs-researcher.md`) confirm there is **no v1 landing in this tree** and no production hostname.

Typed contracts on this change (`change-spec.yaml` `contracts`):

| Kind | Entries |
| --- | --- |
| `openapi` | `[]` |
| `events` | `[]` |
| `json_schema` | `[]` |

Keep those arrays empty. Filling them to “satisfy” the `api` domain would be an invented integration.

---

## 2. Why the route says `api` (misclassification)

`.grok-stack/runtime/active-route.json` (and the copied `route.json`):

- `task_domains`: `[]` — the prompt contains none of the router’s API keywords (`api`, `rest`, `graphql`, `endpoint`, `openapi`, `webhook`).
- `domains`: `["api"]` — inherited from **repository** detection, not the task.
- `repo.signals`: `["contract:engineering/contracts/openapi"]`.
- `workflow_skills`: `adaptive-delivery`, `feature-workflow`, **`api-event-change`**.
- `quality_profiles`: `base`, **`contracts`**.
- `risk`: `medium` because `_risk()` treats any combined domain in `{api, event, integration, data, ai}` as medium-risk contract work.
- `write_agent`: `general_implementer` — correct. Write-owner selection prefers `task_domains`; empty task focus does **not** select `integration_implementer`.
- `analysis_agents` includes `integration_architect` because `analysis_domain_agents.api` maps to this agent.

Cause in `.grok-stack/adaptive_grok/repo.py`: if `engineering/contracts/openapi/` contains any `.yaml`/`.yml`/`.json` other than `.gitkeep`, the repo is tagged `api`. This tree has `adaptive-demo.v1.json` and `trust-ci.v1.json`. `_domains()` then does `unique_ordered([*task_domains, *repo.domains])`, so a static-landing prompt still routes as `api`.

This is **repository-default contamination**, not a requirement to change those contracts. `NODE-SEO-SHOWCASE-LAB` already has `public_contracts: []`. Factory L5 `landing_*.py`, Trust CI OpenAPI, demo `/api/v1/*`, and factory-control/semantic/execution OpenAPI are **out of bounds** for a character page.

---

## 3. How to apply `api-event-change` without inventing an API

The skill’s seven steps, applied as a **negative freeze** (do the check; do not create producers):

| Skill step | Application here |
| --- | --- |
| 1. Freeze current and proposed contracts | Current: Trust CI, factory, demo OpenAPI and all event schemas stay byte-identical. Proposed: **no new contract**. |
| 2. Identify producers, consumers, adapters, owners | **None** for this landing. The page is static files under `side-projects/seo-landings/`. |
| 3. Compatibility / versioning | N/A — no payload, no version bump, no deprecation. |
| 4. Auth, errors, idempotency, retries, PII | N/A at runtime. Do not collect personal data. |
| 5. Outbox when txn + publication must align | **No transactional state, no publication.** No outbox. |
| 6. Contract and replay/retry tests | Do not add API contract tests. Add static-page tests (no `<form>` POST, no external runtime URLs). |
| 7. Staged rollout / consumer migration | Not an API rollout. Delivery is PR-only static files. No consumers to migrate. |

`contracts` quality profile runs `contract-structure` against **existing** repo contracts. It is a pass/fail shape check, not a mandate to add OpenAPI. Do not touch `engineering/contracts/**`, `factory/contracts/**`, or `delivery/contracts/**`.

`AGENTS.md` API/events/integrations rules (contract-first HTTP, outbox, adapters, production writes) apply **when an interface exists**. They do not authorize creating one. “Do not introduce a service, database, queue, framework, or dependency without explicit architectural justification” forbids a lead API invented for this page.

---

## 4. Explicit no-integration design

Implement as static files only, following `$seo-landing` generate-mode output under a new slug (repo_explorer recommendation: `side-projects/seo-landings/winston-wolfe-pulp-fiction-v2/`). Runtime is local `python3 -m http.server` or equivalent. No application process.

### Forbidden on this change

- Backend, serverless function, CGI, PHP handler, factory landing HTTP, demo `/api/v1/preview`.
- Invented form `action` (`/api/lead`, Formspree, Google Forms, Bitrix24 web forms, mailto-as-fake-API).
- Webhooks, queues, Kafka/Rabbit, AsyncAPI, outbox tables, reconciliation jobs, DLQ.
- Third-party widgets on **first load**: analytics, tag managers, chats, cookie-consent vendors, maps, YouTube iframes, fonts (Google Fonts), JS/CSS CDNs, pixel trackers.
- Production writes to 1C, Bitrix24, SAP, ERP, WMS, payment, CRM, hosting, DNS, search-console sitemap ping.
- New OpenAPI/event schemas, adapters, anti-corruption layers, ID maps.
- Reading `.env` or credentials to “wire” a form.
- Deploy, merge, or live-host mutation (separate exact delegation; not this design).

### Allowed (not integrations)

- Semantic HTML/CSS, optional single deferred first-party `script.js` ≤ 15 KB with **zero** network calls.
- In-page fragment CTAs (`#brief`, `#contact`) and showcase-style local prompt copy that **does not submit**.
- Local images, favicon, `ASSETS.md`, `SERVER-SETUP.md` (instructions only; the file does not deploy).
- `mailto:` / `tel:` **only if** the user later supplies a real address/number. None exist today → omit.
- Implementer-side validation tools (W3C Nu, Lighthouse against `127.0.0.1`) are **lab gates**, not page runtime. They must not appear as `<script src>` / `<link>` on the landing.

### Adjacent systems that must stay disconnected

| System | Why it looks related | Why it is not this landing |
| --- | --- | --- |
| Factory L5 `landing_*.py`, `landing_backend_api.py` | Name contains “landing” | Autonomous dogfood runtime; architecture-bound; different product |
| `delivery/.../landing-publication-request` | Publication contract | Filesystem publication of L5 artifacts, not a public site |
| `engineering/contracts/openapi/adaptive-demo.v1.json` | HTTP API | Loopback investor demo; no mutation; not a lead sink |
| `engineering/contracts/openapi/trust-ci.v1.json` | HTTP API | Merge authority; must not be referenced by the page |
| Showcase `seo-landing-showcase/` | Existing static HTML | Capability demo fixture; byte-frozen; not Winston Wolfe |

No adapter is required to “isolate” these. Isolation is **non-coupling**: do not import, fetch, or hyperlink them as backends.

---

## 5. Form / CTA policy (no destination collected)

Tech-spec §10 form submission contract (skill-pinned):

> Collect the submission destination and method in the brief BEFORE generating the form … Never invent an endpoint. No backend exists → omit the form, or ship it as an explicitly labeled stub … A form whose submission defaults to the current page and delivers nothing anywhere is forbidden.

**Policy for v2:**

1. **No `<form>`.** There is no first-party handler, no documented form service, no consent/privacy text, no data owner. A posting form would be a fake integration.
2. **CTA is in-page only.** Primary/secondary buttons are `<a href="#…">` (or a non-submitting `<button type="button">` that only reveals on-page copy). Copy may invite the user to “call Winston” in character **without** collecting leads.
3. **Do not stub a POST that looks live.** An unlabeled `action=""`, `action="#"`, or `action="/api/lead"` is a generation failure under §10.
4. **No messengers, WhatsApp, Telegram, or calendars** until the user supplies a real URL.
5. **PII:** do not add name/email/phone fields. No honeypot, because there is no handler to discard spam into.
6. **Success/error UX for submit:** not applicable. Do not fake “message sent”.
7. Record in `SERVER-SETUP.md`: “No lead backend. Forms omitted until a destination is collected.”

Showcase precedent (`side-projects/seo-landing-showcase/index.html` + `tests/test_seo_landing_side_project.py`): no `<form>`, CTA shows a local prompt, zero external runtime URLs. New tests for this slug should assert the same.

---

## 6. Crawlability files without a live host

Skill OUTPUT lists `robots.txt` and `sitemap.xml` as project files. Tech-spec §3/§7 crawlability then requires:

- HTML canonical and sitemap `<loc>` as **absolute** URLs on a real origin;
- `robots.txt` `Sitemap:` fully qualified;
- HTTP 200 for both files **on the deployed host**.

The user supplied **no domain**. Skill §0a: do not invent domain/canonical/`og:url`/JSON-LD `@id`. Repository practice (`decisions.md` 2026-09-01; showcase README/SERVER-SETUP; docs_researcher): stay `noindex, nofollow` until a verified production origin exists. Mixing tech-spec production `index, follow` with an invented `https://site.com/` is the L5-era mistake already recorded.

**Policy:**

| File | Ship? | Content rules without a host |
| --- | --- | --- |
| HTML robots meta | Yes | `noindex, nofollow`. No `index, follow`. |
| `<link rel="canonical">`, `og:url`, JSON-LD absolute `@id`/`url` | **No** | Omit. Do not mint a fake origin. |
| `robots.txt` (local file) | Yes, as a **local** file | `User-agent: *` + `Disallow: /` (or equivalent “not for public crawl”). **No** `Sitemap:` line pointing at an invented host. Do not ping Google/Bing. |
| `sitemap.xml` (local file) | Yes, as a **local** file only if it does not claim a live host | Prefer a short XML comment-free file **or** omit `<loc>` absolute public URLs. Honest option: a one-URL sitemap is **not** valid without an origin — ship a documented **placeholder** that `SERVER-SETUP.md` labels `not deployed; loc withheld until origin is collected`, **or** ship the file with no `<url>` entries and state that the crawlability HTTP 200 gate is `BLOCKER: no live host`. Never write `https://example.com/` / `https://winston-wolfe.example/`. |
| Hosted `/robots.txt` and `/sitemap.xml` | **No** | There is no host. Do not treat GitHub raw URLs as the canonical origin. |
| Tech-spec §7 gate 6 (curl deployed robots/sitemap) | Report **BLOCKER** | Missing deployed URL. Do not fabricate HTTP 200. |

`SERVER-SETUP.md` must say: production origin, canonical, indexable robots/sitemap, TLS, and MIME verification are **out of scope** until a later change with a real HTTPS origin. Local preview: `python3 -m http.server` on the project directory. That local server is not an integration and not a production write.

Do not submit sitemaps, call Search Console APIs, or add DNS/hosting config.

---

## 7. What would become an integration later

These are **future changes**, each needing its own route, contracts, and (where applicable) exact delegated production write. They are **not** in scope now.

### A. User supplies a production domain / canonical origin

Still not an API by itself, but origin-bound SEO becomes real:

- HTML `canonical`, `og:url`, JSON-LD `@id`/`url` using that exact HTTPS origin (allow-list `https`; reject `javascript:`).
- `robots.txt` may add a fully qualified `Sitemap:` line; HTML robots may move to `index, follow` only after review.
- `sitemap.xml` `<loc>` must match the HTML canonical; `lastmod` only from a verifiable content-change timestamp.
- Crawlability gate 6 becomes runnable against the **deployed** host (HTTP 200), not localhost-as-production.
- Hosting/TLS/DNS/CDN and Search Console verification are **infra + production writes** (`AGENTS.md`): require an exact delegated operation. This landing change must not perform them.
- Indexing is still not an adapter; it is origin configuration.

### B. User supplies a lead / form endpoint

**This is the first real API/event integration.** Then `api-event-change` applies in earnest:

- Freeze a contract: OpenAPI (or documented third-party form API) for `POST` fields, content type, auth, error model, idempotency key.
- Destination must be a first-party handler or a **named** form service from the brief — never invented.
- Collect consent/privacy text and data owner; record storage in `SERVER-SETUP.md`.
- Native `<form>` with visible labels, `autocomplete`, honeypot; server validates the same field contract.
- Timeouts, retries, duplicate-submit guard, observable success/failure.
- If a local database transaction must align with an outbound event (CRM, email, Bitrix24, 1C), add an **outbox** and reconciliation; that requires `integration` domain, adapters, and human gates for production writes.
- PII: retention, access, no secrets in the page, audit without logging payloads.
- Third-party form widgets load only under tech-spec §11 consent/activation — not on first load.
- New tests: contract tests + one end-to-end delivery check (skill §10). Untested delivery is a blocker, not “done”.
- `change-spec.yaml` `contracts.openapi` / `events` would gain real IDs. `write_agent` might become `integration_implementer` if the **task** names the API.

### C. Other later triggers (each is an integration or third-party dependency)

| Later user input | Becomes |
| --- | --- |
| Analytics / tag manager | Third-party first-load or consent-gated script; dependency manifest; CSP; **not** first-load in v2 |
| Chat / cookie vendor | §11 deferred widget + consent; documented origin |
| Map / YouTube Mode S | Facade (zero requests until click) or explicit first-load embed recorded as a dependency |
| CRM / Bitrix24 / 1C / payment | Enterprise adapter, secrets outside Git, production-write grant |
| Webhooks inbound (e.g. form-service callbacks) | Event contract, auth, idempotency, replay tests |
| Live hosting of this slug | Deploy/infra; not a code adapter; exact delegation |

Until those inputs exist, the design stays empty.

---

## 8. Implementer constraints (for `general_implementer`)

- Do not add adapters, OpenAPI, events, or factory/demo/Trust CI wiring.
- Do not “fix” the route by editing `engineering/contracts/openapi` to remove the `api` signal.
- Keep `change-spec.yaml` contract lists empty; add an invariant in the package (architect/task_analyst) that the landing performs zero runtime network I/O.
- New tests belong on the **new** slug (no form, no `http(s)`/`//` runtime URLs, `noindex`), not by retargeting showcase digest tests.
- `api-event-change` is satisfied by the freeze in §3, not by creating a lead API.
- Production deploy remains out of scope.

---

## Conclusion

**Integration surface:** empty. No external systems, no HTTP APIs, no webhooks, no events, no outbox, no adapters, no reconciliation, no production writes.

**Form/CTA policy:** omit `<form>` and any posting `action`. CTAs are in-page anchors or non-submitting controls. Do not invent `/api/lead` or third-party form URLs. No PII fields until a real destination, consent text, and data owner are collected.

**Crawlability files without a live host:** ship `robots.txt` (and only a non-claiming local `sitemap.xml`) as **files in the project**. HTML stays `noindex, nofollow`. No canonical/`og:url`/JSON-LD origin. No `Sitemap:` URL to a fake host. Deployed robots/sitemap HTTP 200 is `BLOCKER`, not a fabricated pass. Local `http.server` is preview only.

**If the user later supplies a domain:** origin-bound SEO and honest robots/sitemap become a follow-on static change (still not an API) plus separately delegated hosting. **If the user later supplies a lead endpoint:** that is the first real integration — freeze an OpenAPI/form-service contract, then apply `api-event-change` for validation, idempotency, PII, retries, and (only if txn+event must align) outbox/reconciliation. Until then, the misclassified `api` domain / `api-event-change` skill is a **negative freeze of existing contracts**, not a license to invent a backend.
