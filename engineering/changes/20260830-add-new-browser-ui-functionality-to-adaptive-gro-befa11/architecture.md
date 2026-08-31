# Architecture — Add new browser UI functionality to Adaptive Grok Build Pro: create a one-command local HTTP demo application with a polished responsive dashboard using real repository routing, typed-spec, architecture, governance, and verification-summary logic against bundled sample data; add automated tests and user documentation. Do not perform external writes.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The repository exposes mature CLI/library logic but has no browser product surface. Normal routing and verification CLIs are stateful and unsafe to expose directly over HTTP.

## Proposed behavior

A dependency-free read-only demo composes pure repository functions into bounded projections and serves a static responsive dashboard from `127.0.0.1`.

## Components and boundaries

- `.grok-stack/adaptive_grok/demo.py`: pure snapshot and preview service.
- `.grok-stack/adaptive_grok/demo_http.py`: HTTP protocol, security, bounds, static allowlist.
- `.grok-stack/demo/`: semantic HTML/CSS/ES modules and validated fixtures.
- `scripts/grok_demo.py`: root discovery, lifecycle, optional browser open.
- `engineering/contracts/openapi/adaptive-demo.v1.json`: frozen local API.
- Browser input reaches only route/spec computation and never becomes a path, command, URL, environment value, or Git ref.

## Data flow

`browser -> same-origin loopback HTTP -> demo service -> pure repository logic -> allowlisted projection`. Verification is a validated bundled sample and never a verifier execution.

## API and event contracts

- `GET /api/v1/health`, `GET /api/v1/snapshot`, and closed `POST /api/v1/preview`.
- No events or mutation endpoint. Errors contain request ID, stable code, safe message, and retryable flag.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Python standard library and static ES modules; no service/frontend framework.
- Visible provenance and direct-call equivalence instead of canned aggregate claims.
- Portable stdlib integration/structural UI tests are mandatory; browser screenshots are optional when a runner already exists.
- This is a product demonstration surface, not CI authority or execution plane.

## Risks and mitigations

- Canned-data perception: direct-equivalence and mutation tests.
- Sample mistaken for authority: persistent labels and forbidden-claim tests.
- Local HTTP abuse: loopback, Host/Origin checks, CSP, bounds, literal assets.
- UI drift: frozen API and focused state/accessibility tests.
