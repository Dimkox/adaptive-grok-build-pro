# Tasks — L5 multimodal landing dogfood

All five implementation tasks are sequential and owned by the route-selected `ai_implementer`. Every task starts with its focused RED, ends with its focused GREEN and a coherent commit, and hands immutable interfaces to the next task. Final independent reviews occur only after the completed product tree passes verification.

- [x] **1. Contracts and intake:** add closed schemas/dataclasses, media-shape validation, tenant/idempotency/correlation binding, and private transient blob storage; hand off `LandingInputV1` plus canonical digest.
- [x] **2. Provider normalization:** add fixed command-provider protocol, sealed deterministic fixture, unavailable default profile, and closed spec validation; hand off `StaticLandingSpecV1` plus provider evidence.
- [ ] **3. Rendering and evaluation:** add fresh exact target-SHA/tree workspace orchestration, deterministic root `index.html`/`content.css` renderer, independent evaluator, and hard three-attempt chain; hand off one selected exact candidate or a closed terminal failure.
- [ ] **4. Artifact sealing:** add canonical manifest and deterministic site-only ZIP/sidecar construction; hand off immutable artifact identity without modifying product release packages.
- [ ] **5. API and disabled publication integration:** wire the additive API/server boundary, unavailable publisher, architecture/docs, compatibility assertions, final verifier, then route-selected reviews; hand off a clean locally ready branch with no external effect.

Detailed file-level TDD steps and commit boundaries are fixed in [`docs/superpowers/plans/2026-09-04-l5-multimodal-landing-dogfood.md`](../../../docs/superpowers/plans/2026-09-04-l5-multimodal-landing-dogfood.md).
