# Stable workflow synthesis implementation plan

Approved by the user (`утверждаю stable-синтез`), including weekly intake of newest stable releases and bounded post-pin change/bugfix candidates.

1. Freeze analyses, typed ACs, design, rollback and release boundary; transition the durable change to implementing and commit this checkpoint.
2. RED/GREEN closed pins, typed DAG/transitions/findings/convergence, snapshots, and journal CAS/corruption/resume/contention.
3. RED/GREEN fixed fake transport, release/tag/head/compare/cache/error matrix, atomic state, due/clock/locking behavior.
4. RED/GREEN CLI mutation boundary, inert units, architecture node/edge/ownership, and router bounded terms.
5. Update factual current docs; run focused, architecture, and full baseline checks. Leave `implementing` for parent-owned verification/reviews.

No step authorizes external/production actions or tracked automatic pin/source changes.

Timing is governed by the superseding whole-program deadline `2026-09-04 23:59 UTC+3`. The stable-synthesis target is remediation and focused evidence by `2026-09-03 18:00`, followed by parent exact-head verification and independent reviews by `20:00`; in parallel M4 may prepare its final descendant through `23:00`. Accepted integration remains event-triggered: M4 external acceptance must precede accepted M5, then M6, M7, M8 and M9; provisional source-preparation targets are listed in the [canonical M5 schedule](../../../engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/schedule.md) and are not acceptance claims.
