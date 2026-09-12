# L5 production runtime implementation plan

This is the saved first-slice plan. Its source implementation is complete but unverified. The user subsequently authorized all six remaining production items and selected II-Tonya plus Pump Selector as the evidence basis; the operative continuation is `engineering/changes/20260912-l5-production-completion-verification-deferred-b-8632a3/six-point-continuation.md`. That continuation supersedes the fixed old source pin, no-new-dependency limit and earlier delivery deferral below. Tests, new test authoring, verification and reviews remain paused. No production acceptance is claimed.

**Goal:** Complete the existing L5 landing runtime's durable server composition and bounded HTTP provider boundary before operational activation.

**Architecture:** Reuse `SQLiteLandingJobStore`, the strict landing normalization decoder, and the existing render/evaluate/seal builder. Add an HTTP-specific profile and normalization adapter; retain the native Codex and unavailable APIs. The server owns only resources it creates and keeps live providers explicitly opt-in.

**Tech stack:** Existing Python, HTTPX, FastAPI/Uvicorn and SQLite; no new dependencies, queues, services or PostgreSQL migrations.

**Spec:** `docs/superpowers/specs/2026-09-04-l5-multimodal-landing-dogfood-design.md`, extended by the active change brief and the user's 2026-09-12 continuation request.

## Execution constraints

- User instruction «прверки пока не проводим»: do not run tests, builds, lint, verification, independent reviews or live probes. New test authoring is also deferred; save regression scenarios as documentation and continue implementation.
- Exactly one implementation owner acts as route `general_implementer`; controller writes only change documentation and shared memory.
- Preserve published archives, version identity, native Codex API, v1 landing API (`live_url: null`), source pins, M0–M9 contracts and migrations.
- Never read credentials or `.env`; authored runtime code may consume explicitly configured operator credentials only after opt-in. Do not activate it in this session.
- Keep implementation marked unverified. No check receipts, readiness declaration, push, merge, release or deployment during the deferred phase.

## Task 1 — Truthful bounded HTTP normalization

Files: `factory/src/adaptive_factory/landing_live_executors.py`, additive HTTP profile/normalizer module as needed, small reuse seam in `landing_normalizer.py`/`landing_runtime.py` only if needed. Save future regression scenarios in the change package.

- [ ] Add closed HTTP profile identity bound to provider, supported endpoint/model, limits, prompt/schema/decoder and adapter version; never invent Codex executable facts for HTTP.
- [ ] Reuse strict text/DOCX normalization and draft/spec decoding. Explicitly reject unsupported media before blob access/HTTP; do not discard an image silently.
- [ ] Bind composed executor requests to the exact profile and restrict provider origins; no redirect, environmental proxy discovery or automatic retries.
- [ ] Stream bounded response bytes under a monotonic deadline; validate terminal response, model/choice/content shape and factual usage. Stable reason codes replace leaked provider error bodies.
- [ ] Save future regression scenarios for identity mismatch, unsupported media, malformed/oversized/slow responses, truthful usage and default no-call behavior. Do not execute them.

## Task 2 — Durable server composition and ownership

Files: `factory/src/adaptive_factory/settings.py`, `server.py`, additive composition module if useful. Save settings/server/composition regression scenarios in the change package.

- [ ] Add explicit normalized private state/source/scratch/output configuration and strict provider enablement. Config absence preserves unavailable behavior.
- [ ] Reuse SQLite durability, require it for operational HTTP composition, and preserve injected-service ownership.
- [ ] Bind startup to implemented exact source policy without retargeting it. Validate config before acquiring provider capability.
- [ ] Close created stores on composition/startup failure and application shutdown. Prevent a second service process from recovering or modifying an active writer's work.
- [ ] Preserve interrupted-state recovery with no model-call replay. Document the existing bounded recovery capacity and shutdown behavior.
- [ ] Save restart/config/lifecycle regression scenarios without authoring or running tests.

## Task 3 — Operational handoff

Files: `factory/README.md`, `engineering/runbooks/l5-production-runtime.md`, `README.md`, `START_HERE.md`, `PROJECT_STATE.json`, active change package.

- [ ] Document exact config, supported inputs, single-writer operation, recovery/stop/rollback and observable terminal outcomes.
- [ ] Keep production publisher unavailable until a concrete target, signed artifact acceptance and resource-bound authorization exist.
- [ ] Record unresolved source refresh, PDF/audio/image capability, publication and operational proof separately from implemented runtime work.
- [ ] Leave all checks and release delivery explicitly deferred; publish no success evidence.

## Later verification, currently paused

Once the user resumes checks, run the focused HTTP/composition/server/SQLite cases, then `python3 scripts/grok_verify.py --mode pr`, route-selected independent reviews, and exact-head external Trust CI through the PR. Only later evaluate operational activation and reversible publication with concrete target authority.
