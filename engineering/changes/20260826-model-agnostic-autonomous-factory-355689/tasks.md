# Design gate checklist — Model Agnostic Autonomous Factory

- [x] Read AGENTS.md, root README.md, DARK_FACTORY_ROADMAP.md, route `35568941ae59`, and the exact active package.
- [x] Run all five route-selected read-only analysis roles and store their reports in this package.
- [x] Freeze the provider-neutral architecture, trust boundaries, protocol, limits, and roadmap gates in the canonical design.
- [x] Complete the durable Markdown projections and typed change spec without placeholders.
- [x] Record and pass the final design self-review and focused documentation/spec validation.
- [x] Transition the package to `scoped` without crossing `scope_and_design_approval`.
- [x] Create one local design/docs commit on `feature/model-agnostic-factory` and stop for user review.

Implementation tasks are intentionally absent. They require a later user-approved scope after M1 completion is separately framed.

## Approved stacked implementation

- [x] Record the user's expansion from design-only scope to full exact M2 -> M3 -> M4 implementation without functional cuts.
- [x] Write and self-review `docs/superpowers/plans/2026-08-28-m3-controlled-knowledge-debt.md`.
- [x] Write and self-review `docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md`.
- [ ] Stack M3 on exact M2-A `635c9ddf2d63c1ea823074106976a8f3de6299a9`, execute its TDD tasks, run one final verifier/review wave, and open the first stacked PR.
- [ ] Stack M4 on reviewed M3, execute its TDD tasks including one real PostgreSQL exit run, run one final verifier/review wave, and open the second stacked PR.
- [ ] After M4 API review, scope a separate `/home/pall/baby-bot` admin adapter/deployment change; require human Telegram token rotation and URL-log redaction before activation.

The historical sentence above records the original design gate and is retained as design history; it no longer describes the user's later explicitly expanded implementation scope.
