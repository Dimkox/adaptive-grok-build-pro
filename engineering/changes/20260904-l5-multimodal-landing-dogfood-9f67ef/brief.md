# L5 multimodal landing dogfood

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260904-l5-multimodal-landing-dogfood-9f67ef`
Route: `9f67efd2575c`
Control design base: `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`
Dogfood target: `github.com/Dimkox/ai-dark-factory-landing` at `176efcaab931c2482781ff163c621b10aa05dee9`, tree `f2bdcecc6dbe9ecc82007610d398ca12bd75e07f`
Created: 2026-09-04
Risk: red
Domains: AI, API, frontend, security

## Problem

The repository has a reviewed static landing showcase and delivered M4-M9 control, execution, validation, autonomy, and delivery contracts, but it has no executable repository-local path that turns one bounded text, audio, image, PDF, or DOCX input into a closed landing specification, an independently evaluated candidate, and a deterministic site artifact. The public domain is indexed according to user-supplied SERP evidence, while its origin bytes, full route inventory, rollback snapshot, provider profile, Trust CI candidate evidence, and hosting authority are unavailable.

## Outcome

Provide an offline, deterministic, repository-local vertical that accepts one bounded multimodal input, uses a fixed command-provider port with a sealed conformance fixture, renders a static candidate in an isolated workspace of the exact target SHA/tree, evaluates no more than three attempts, and emits an exact-SHA ZIP plus SHA-256 sidecar. The default provider profile and production publisher remain unavailable, so the vertical proves contracts and orchestration without claiming an operational model call, target mutation, publication, deployment, or L5 production autonomy.

## Scope

### In scope

- Add closed versioned contracts for input identity, normalized landing specification, provider evidence, candidate attempts, evaluation, artifact identity, and local result state.
- Accept exactly `text`, `audio`, `image`, `pdf`, and `docx` through an additive authenticated API boundary with strict size, type, tenant, repository, idempotency, and correlation checks.
- Add fixed executable command-provider ports selected only from trusted configuration, one sealed deterministic test fixture, and a default unavailable profile with no fallback or network access.
- Render only escaped static HTML/CSS to root `index.html` and `content.css` inside a fresh disposable workspace of the exact private target SHA/tree; never mutate its read-only local clone.
- Run an independent deterministic evaluator and bounded repair loop with one initial attempt and at most two repairs.
- Produce a canonical candidate manifest, deterministic ZIP, and `.sha256` sidecar bound to the exact candidate SHA/tree and all relevant input/profile/evaluator identities.
- Add a production publisher interface whose repository composition is disabled and fail-closed.
- Preserve all delivered M0-M9 behavior, migrations `001`-`018`, the product `2.0.13` ZIP, and `side-projects/seo-landing-showcase/` byte-for-byte.

### Out of scope

- Live AI/provider calls, credentials, customer or proprietary input transfer, OCR/transcription service integration, and provider fallback.
- Database migrations, durable shared service activation, systemd installation, or mutation of persistent/shared PostgreSQL.
- Importing or cherry-picking any stale feature branch; the approved cherry-pick count is zero.
- Reading, replacing, or claiming preservation of the unknown live document root.
- Push, pull request, merge, tag, release, DNS/TLS/WAF/hosting change, Namecheap write, deployment, or any other external/production action.
- A claim that the generated result is live, operational L5 autonomy, indexed, or accepted by Trust CI.

## Constraints

- **Backward compatibility:** Existing OpenAPI documents, M4-M9 contracts, migrations, release artifacts, and showcase bytes remain unchanged. L5 contracts and source are additive.
- **Data and privacy:** Raw input is tenant-bound, content-addressed, private, transient, excluded from Git/model logs/evidence, and destroyed after the bounded local run. Durable records contain closed projections and digests only.
- **Security:** Untrusted content never selects commands, providers, tools, paths, origins, policies, or authority. Command arrays and executable identities are fixed by trusted configuration; shell evaluation, network destinations, inherited credentials, and production publisher capability are absent.
- **Performance:** One request accepts one bounded input, provider output is bounded, total candidate attempts are at most three, and artifact inventory/bytes are finite and deterministic.
- **Operational:** The truthful terminal local outcomes are `artifact_ready`, `provider_unavailable`, `needs_human`, `rejected`, or `cancelled`. `live` and `indexed_observed` are unreachable in this change.

## Approval and authority

The user statements recorded in [`evidence/human-approval.md`](evidence/human-approval.md) satisfy `scope_and_design_approval` for this design and the later repository-local implementation described here. They do not authorize a provider call, data transfer, push, PR, merge, release, signing, hosting mutation, deployment, or production action.
