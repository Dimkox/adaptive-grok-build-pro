# M5 Provisional Source Schedule

Navigation: [package](brief.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

- Superseding whole-program deadline: `2026-09-04 23:59 UTC+3`.
- Observation: `2026-09-03 16:00 UTC+3`, about 32 hours remain. M4's planned window is missed: PR #21 at `571cad7` has an external Trust CI failure (the preserved run identifies `root-unittest`) and a separate GitGuardian failure whose contents are not inferred; local hotfix/package candidate `9727bc3` is unpushed and not externally rechecked.
- Successor 04 contract enrollment/comparator was restacked at `2026-09-03 03:48-03:51 UTC+3` and is clean at `27b0ae6` on exact predecessor `8a7be8a`. Exact fitness passes; session-level comparator/security feedback exists, but no checked-in review report or route receipt is recorded.
- Successor 05 runtime/recovery/additive-v2 began from `27b0ae6`; preservation checkpoint `3f56b6a` and runtime checkpoint `5073fc0` were followed by product/restart checkpoint `3940267` (tree `4646582`) at `2026-09-03 12:41 UTC+3`. The exact disposable PostgreSQL-17 run executed 273 tests (272 pass, one expected fresh-cluster skip) in 221.516 seconds, then passed two actual restart/recovery phases. Session-level test/security feedback reported no open P0/P1, but no repository-bound review report, final exact-head verifier or route receipt exists.
- Successor 06 is the reserved inert systemd/installer/configuration/final-doc slice. Each successor must use its immediate predecessor as PR base; cumulative `9727bc3` → `27b0ae6` exceeds the architecture size gate and may not be squashed.

| Accepted critical path | Target | Factual gate |
| --- | ---: | --- |
| stable synthesis close | 2026-09-03 16:00-20:00 | remediation, exact-SHA local verifier and independent route reviews; no external acceptance claimed |
| M4 parity/refreeze | 2026-09-03 16:00-23:00 target, partly parallel | final documentation/package descendant, verifier/reviews, then separately authorized PR update |
| M4 external acceptance | event-triggered after 23:00 | exact PR head, App-owned Trust CI success and required signed scopes; only this permits accepted M5 restack |
| M5 accepted restack | event-triggered after accepted M4 | exact immediate predecessor, final successor-06 evidence, trusted rootless broker and live OS isolation |
| M6 accepted restack | event-triggered after accepted M5 | migration 018, semantic/repair verification and reviews |
| M7 accepted restack | event-triggered after accepted M6 | immutable shadow bundle, durable lookup and real outcomes |
| M8 accepted restack | event-triggered after accepted M7 | at least 30 eligible real human outcomes, accepted profile and demotion proof |
| M9 accepted delivery | event-triggered after accepted M8 | signed artifact, preview/staging/canary/recovery and human production authority |
| deadline decision | 2026-09-04 23:59 | report exact accepted state or named blockers; never convert source presence into acceptance |

| Provisional source-preparation lane | Target start (UTC+3) | Boundary |
| --- | ---: | --- |
| M5 successor completion preparation | 2026-09-03 20:00 | May prepare source/tests while M4 gates run; no accepted restack before M4 acceptance. |
| M6 restack preparation | 2026-09-04 00:00 | Provisional conflict/migration analysis only until accepted M5. |
| M7 restack preparation | 2026-09-04 04:00 | Provisional durable-lookup/shadow evidence work only until accepted M6. |
| M8 cohort/profile preparation | 2026-09-04 08:00 | Tooling may be prepared, but the real-human cohort cannot be synthesized or backdated. |
| M9 preview/recovery preparation | 2026-09-04 12:00 | Source/runbook preparation only; signed inputs, environment and production authority remain external. |
| final exact-state reserve | 2026-09-04 20:00 | Freeze mutable preparation; assess dependency chain and external gates through 23:59. |

These are compressed planning targets, not completion claims. There is no current evidence that every gate can fit before the deadline: M4 external acceptance is pending, M5 live isolation is blocked, and the M8 cohort and M9 signed/human inputs are not available on demand. Calendar pressure never waives dependency order, immediate-predecessor fitness, PostgreSQL/restart evidence, signed scopes, external exact-SHA Trust CI, the M8 cohort or human production authority.
