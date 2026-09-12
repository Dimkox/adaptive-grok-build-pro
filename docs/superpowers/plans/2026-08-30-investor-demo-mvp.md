# Investor Demo MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Repository routing permits exactly one `frontend_implementer` as write owner for all tasks.

**Goal:** Ship a one-command investor-ready local browser demo backed by real read-only product logic.

**Architecture:** A pure Python service exposes allowlisted projections through a loopback standard-library HTTP adapter. Static HTML/CSS/ES modules render explicit sample/computed/live provenance and accessible states.

**Tech Stack:** Python 3.11+ standard library, existing `adaptive_grok`, HTML5, CSS, ES modules, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-30-investor-demo-mvp-design.md`

## Global constraints

- No external writes, request-driven subprocesses, route activation, verifier execution, GitHub/Trust CI/provider calls, or arbitrary paths.
- Bind to loopback; API is closed, bounded, same-origin, versioned, and read-only.
- Use real repository logic and explicit `bundled_sample`, `computed_preview`, and `live_repository` provenance.
- Add no root packaging marker, JS dependencies, database, framework, or daemon.
- TDD every behavior and record RED/GREEN commands in the implementation report.

### Task 1: Service and fixtures

Create `.grok-stack/adaptive_grok/demo.py`, bounded fixtures, and `tests/test_demo.py`. Tests first prove deterministic shape, direct router/spec equivalence, live architecture/governance summaries, fixture mutation, provenance, preview `not_run`, and no authority claims. Implement the minimum service with existing pure functions.

### Task 2: Closed HTTP API

Create `.grok-stack/adaptive_grok/demo_http.py`, `scripts/grok_demo.py`, OpenAPI v1, and `tests/test_demo_http.py`. Tests first cover endpoints, JSON shape, body/prompt bounds, unknown fields, Host/Origin, methods, traversal, headers, errors, and no mutation. Implement literal asset routing and lifecycle.

### Task 3: Dashboard

Create semantic HTML, responsive CSS, and ES modules under `.grok-stack/demo/`. Tests first lock labels/live regions, safe DOM, no remote/inline assets, source/status rendering, loading/validation/degraded/stale states, reduced-motion/focus/forced-colors, and mobile invariants. Implement the five-minute story without hard-coded verdicts.

### Task 4: Product integration

Update architecture model/rules/diagrams, installer inventory, package/structure tests, `README.md`, `QUICKSTART.md`, and `docs/INVESTOR_DEMO.md`. Keep the README graph complete if core nodes change. Run demo, architecture, installer, manifest, and structure suites.

### Task 5: Identity and evidence

Update VERSION/CHANGELOG/notes, run full PR verification, complete route-selected reviews, record receipts, and build the local ZIP/checksum. Do not push, merge, tag, publish, or deploy.
