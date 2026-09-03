# Stable synthesis and program critical path

All times are UTC+3. Observation: `2026-09-03 16:00`; superseding whole-program deadline: **`2026-09-04 23:59`**.

| Critical path | Target | Gate |
| --- | ---: | --- |
| Stable synthesis remediation/evidence | Sep 3 16:00-18:00 | focused and structural GREEN on one exact source SHA |
| Stable synthesis verifier/reviews | Sep 3 18:00-20:00 | parent exact-head verifier, independent route reviews and fresh receipts |
| M4 final-descendant preparation | Sep 3 16:00-23:00, parallel | package parity and exact-head verifier/reviews; source-complete only |
| M4 external acceptance | event-triggered after 23:00 | authorized PR update, App-owned exact-head Trust CI and signed scopes |
| Accepted M5 → M6 → M7 → M8 → M9 | event-triggered after each accepted predecessor | no accepted restack starts before its predecessor; exact gates remain mandatory |
| Deadline decision | Sep 4 23:59 | report exact accepted state and blockers, never infer acceptance from source presence |

Provisional source preparation may start at Sep 3 20:00 (M5), Sep 4 00:00 (M6), 04:00 (M7), 08:00 (M8) and 12:00 (M9), with final exact-state reserve at 20:00. Those hours are preparation targets only: M5 still needs trusted rootless/live isolation, M8 needs at least 30 eligible real human outcomes, and M9 needs signed inputs, an environment, recovery proof and human production authority. There is no current evidence that these external gates can complete by the deadline.

See the [implementation plan](../../../docs/superpowers/plans/2026-09-03-stable-workflow-synthesis.md), [root status](../../../README.md), [roadmap](../../../DARK_FACTORY_ROADMAP.md), [M4 schedule](../20260831-implement-a-new-m4-application-feature-on-exact-b7f288/schedule.md) and [M5 canonical schedule](../20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/schedule.md).
