# Investor Demo MVP Design

## Goal

Turn the command-line control stack into a product surface an investor can understand in five minutes without weakening its trust model. The demo executes real read-only repository logic, remains local, and makes sample, computed, and authoritative evidence boundaries explicit.

## Chosen design

A standard-library Python server binds to `127.0.0.1` and serves a static responsive dashboard. A pure service calls existing router, typed-spec, architecture, and governance functions and returns bounded projections. A validated bundled verification fixture illustrates evidence; entered prompts never inherit its status and show `verification=not_run`.

This has no install/build dependency and fits the existing installer. A static slide would not prove behavior; FastAPI/React would add supply chains and a build boundary without improving the MVP proof.

## Product experience

The landing view shows reviewed intent flowing through deterministic routing, typed requirements, executable architecture, governed knowledge, and evidence. A bounded prompt changes route/spec results through the real engine. Each card displays source, digest, evaluation time, status, and a concise explanation. No card implies that local/sample evidence can merge or deploy code.

Semantic landmarks, a skip link, visible focus, live updates, inline validation, partial degradation, in-memory stale/offline recovery, mobile layout, reduced motion, and text/icon status cues are required.

## Components

- `.grok-stack/adaptive_grok/demo.py`: read-only service and projections.
- `.grok-stack/adaptive_grok/demo_http.py`: transport, bounds, security, stable errors.
- `.grok-stack/demo/`: HTML/CSS/ES modules and fixtures.
- `scripts/grok_demo.py`: launcher and optional browser open.
- `engineering/contracts/openapi/adaptive-demo.v1.json`: closed API.
- focused unit/HTTP/installer/architecture tests and investor guide.

## HTTP and security boundary

Only `GET /`, allowlisted assets, `GET /api/v1/health`, `GET /api/v1/snapshot`, and `POST /api/v1/preview` exist. Preview accepts exactly schema version 1 and a 1..4000-character prompt in at most 16 KiB of UTF-8 JSON, requires same-origin semantics and `X-Adaptive-Demo: 1`, and rejects unknown fields.

The server validates Host and Origin, emits no CORS, applies CSP/nosniff/no-referrer/no-store, and returns safe stable errors. Request data never selects files, commands, URLs, imports, environment fields, sessions, or Git refs. Static paths use a literal allowlist. The browser uses `textContent`, no inline/remote assets, no service worker, and no persistent storage.

## Honesty and failure semantics

Fixtures fail validation before startup. Architecture/governance failures degrade their cards without fabricated zeros. Preview is computed/draft and verification not run. The UI never displays production verification or merge eligibility for local/sample data.

No endpoint activates routes, runs the verifier, writes receipts, invokes subprocesses, contacts GitHub/Trust CI/providers, or performs external I/O. A no-mutation test snapshots relevant state across a full walkthrough.

## Verification

Tests cover direct equivalence, fixture mutation, schemas, hostile Host/Origin, traversal, input bounds, no writes/shell/network, security headers, safe DOM, responsive/accessibility structure, installer/package inclusion, and architecture consistency. Optional installed-browser screenshots supplement, but do not replace, portable stdlib integration tests and the full verifier.

## Non-goals

No M4 queue, provider, database, daemon, cloud service, auth/tenancy, live GitHub data, telemetry, editing, signing, branch/PR/merge/release/deploy action, or frontend framework.
