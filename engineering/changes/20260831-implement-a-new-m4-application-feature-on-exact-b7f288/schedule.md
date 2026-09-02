# Dark Factory M0-M9 Calendar Implementation Plan

All times are UTC+3. The superseding hard deadline is **2026-09-08 00:00 UTC+3**; normal work freezes at 2026-09-07 20:00 and the final four hours are reserved for exact-SHA gates, receipts, documentation parity and recovery evidence. The older 2026-09-15 deadline is retained only as superseded history.

Current execution checkpoint: M4 production `4f75558770f2f332b32b4a47fe6afa61fcc524ec` is present in current-main integration code candidate `da7ec8d7d40f52663aba1ff59bf03ccf209395b0` after three verifier-bypass repairs. The intermediate exact-head local verifier passed 14/14 with 469 changed files, but this documentation refresh still requires final verification and five fresh reviews/reports/receipts; PR delivery, a new exact-SHA external Trust CI result, unresolved PR #21 GitGuardian FAILURE metadata and merge remain pending. M5 Tasks 1-6 source are complete only provisionally at clean head `141e51e75b2bb337fa3bb1544639c6c46c287309`, with rootless live-host isolation and final M4 restack/reviews pending. M6 has only clean provisional Task-1 bridge `3def83eb915ca68e66379269526ffa64822a1104`; migration `014`, service/API behavior, recovery, metrics and final restack/reviews remain pending. M7 clean provisional source `c8b450f494b3d44b580556c6a612b21a3a780368` has synthetic algorithm evidence only and still needs accepted-M6 restack/runtime/real-outcome proof/reviews. M8 began at `46a6c8eba6b5bd8e4654f3041e52061cdd1a15d6` and has a first source-only Task-1 closed-contract slice at clean provisional head `5735e762b8d7571887f6fa4ac9cf10cd1fad1954`; Tasks 2-3, a factual profile, a 30-real-task cohort, activation and acceptance are absent. M9 is design-only at `055051e26e26bf08fa85376523ba6632afcca747`, with no product source, real signed input, environment/recovery proof or production authority. Parallel source work is not acceptance; restack, reviews, PR delivery and Trust CI remain dependency ordered M4 → M5 → M6 → M7 → M8 → M9.

| Milestone | Start | Completion | Exit gate |
| --- | ---: | ---: | --- |
| M0/M1/M2 prerequisites | 2026-08-31 21:00 | 2026-09-01 06:00 | fresh M0 proof and accepted M1/M2 |
| M3 controlled knowledge/debt | 2026-09-01 06:00 | 2026-09-01 14:00 | accepted exact-head M3 |
| M4 durable control plane | 2026-09-01 14:00 | 2026-09-02 18:00 | real PostgreSQL, five reviews, exact-head Trust CI |
| M5 isolated execution | 2026-09-02 18:00 | 2026-09-03 18:00 | isolation/capability/orphan proof |
| M6 semantic validation/repair | 2026-09-03 18:00 | 2026-09-04 14:00 | independent validation and bounded repair |
| M7 PR lifecycle/shadow | 2026-09-04 14:00 | 2026-09-05 12:00 | shadow PR lifecycle evidence |
| M8 earned low-risk autonomy | 2026-09-05 12:00 | 2026-09-06 20:00 | one frozen docs-only class and >=30 human-accepted tasks |
| M9 preview/canary/recovery | 2026-09-06 20:00 | 2026-09-07 20:00 | nonproduction recovery proof |
| protected reserve | 2026-09-07 20:00 | 2026-09-08 00:00 | final exact-state release decision |

## M4 hourly window

- 2026-09-01 14:00-15:00: bind accepted M1/M2/M3/M0 identities and route.
- 15:00-20:00: contracts, state and checksum migrations from failing tests.
- 20:00-02:00: intake, transitions, leases, fences, capacity and restart semantics.
- 02:00-08:00: budgets, retry/dead, kills, audit, API/CLI and reconciliation.
- 08:00-12:00: real disposable PostgreSQL concurrency/restart exit tests.
- 12:00-15:00: current-main integration, state/README/roadmap coherence, exact-tree verifier and five reviews on one fingerprint.
- 15:00-18:00: review fixes if any, receipts, PR preparation and external exact-head gate; branch push or PR mutation still requires exact delegated authority.

## Control protocol

Milestones remain dependency-gated, not clock-triggered. Calendar time never waives App-owned exact-SHA Trust CI, signed human scopes, real PostgreSQL/security/review gates, the M8 cohort or M9 recovery proof. External writes require exact delegated grants; production mutation is outside this plan. If a gate misses its window, compress only non-exit scope and report the exact blocker rather than claim completion. Cross-links: [root current state](../../../README.md), [roadmap](../../../DARK_FACTORY_ROADMAP.md), [M4 package](../../../factory/README.md).
