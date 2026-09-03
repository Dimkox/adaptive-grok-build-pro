# M5 Provisional Source Schedule

Navigation: [package](brief.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

- Hard deadline: `2026-09-08 00:00 UTC+3`; normal verification reserve begins `2026-09-07 20:00 UTC+3`.
- Observation: `2026-09-03 12:49 UTC+3`, about 107 hours remain. M4's planned window is missed: PR #21 at `571cad7` has an external Trust CI failure (the preserved run identifies `root-unittest`) and a separate GitGuardian failure whose contents are not inferred; local hotfix/package candidate `9727bc3` is unpushed and not externally rechecked.
- Successor 04 contract enrollment/comparator was restacked at `2026-09-03 03:48-03:51 UTC+3` and is clean at `27b0ae6` on exact predecessor `8a7be8a`. Exact fitness passes; session-level comparator/security feedback exists, but no checked-in review report or route receipt is recorded.
- Successor 05 runtime/recovery/additive-v2 began from `27b0ae6`; preservation checkpoint `3f56b6a` and runtime checkpoint `5073fc0` were followed by product/restart checkpoint `3940267` (tree `4646582`) at `2026-09-03 12:41 UTC+3`. The exact disposable PostgreSQL-17 run executed 273 tests (272 pass, one expected fresh-cluster skip) in 221.516 seconds, then passed two actual restart/recovery phases. Session-level test/security feedback reported no open P0/P1, but no repository-bound review report, final exact-head verifier or route receipt exists.
- Successor 06 is the reserved inert systemd/installer/configuration/final-doc slice. Each successor must use its immediate predecessor as PR base; cumulative `9727bc3` → `27b0ae6` exceeds the architecture size gate and may not be squashed.

| Dependency window | Compressed target | Factual gate |
| --- | ---: | --- |
| M4 parity, repair and recheck | immediate; already delayed | final documentation/package-parity descendant, rebuilt package if inventory changes, fresh verifier/reviews, then separately authorized PR update and App-owned exact-head success |
| M5 successor 05 source | by 2026-09-03 18:00 | checkpoint `3940267` has migration 017, additive v2, atomic terminal and actual two-restart PG17 recovery proof; final exact-head verifier/reviews remain |
| M5 successor 06 / exit | 2026-09-03 18:00-2026-09-04 06:00 | inert units/installer/docs, exact predecessor fitness/reviews; trusted rootless broker and live OS isolation remain external blockers |
| M6 | 2026-09-04 06:00-2026-09-04 20:00 | accepted M5 restack; first migration renumbered to 018; semantic/repair evidence |
| M7 | 2026-09-04 20:00-2026-09-05 14:00 | accepted M6; real shadow PR lifecycle evidence |
| M8 | 2026-09-05 14:00-2026-09-07 08:00 | accepted M7 and at least 30 eligible real human outcomes; this cohort is deadline-critical and cannot be synthesized |
| M9 | 2026-09-07 08:00-2026-09-07 20:00 | accepted M8, real signed inputs, preview/canary/recovery proof and human production authority |
| protected reserve | 2026-09-07 20:00-2026-09-08 00:00 | exact-state checks, reviews, external gates and recovery decision |

These are compressed planning windows, not completion claims. The pending M4 external rerun, M5 live isolation gate and M8 cohort are deadline-critical blockers; there is no current evidence that every gate will fit. Calendar pressure never waives dependency order, immediate-predecessor fitness, PostgreSQL/restart evidence, signed scopes, external exact-SHA Trust CI, the M8 cohort or human production authority.
