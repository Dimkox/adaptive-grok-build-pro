# Dark Factory M0-M9 Calendar Implementation Plan

All times are UTC+3. The superseding hard deadline is **2026-09-08 00:00 UTC+3**; normal work freezes at 2026-09-07 20:00 and the final four hours are reserved for exact-SHA gates, receipts, documentation parity and recovery evidence. The older 2026-09-15 deadline is retained only as superseded history.

Current execution ruling: M4 repair, provisional M5 branch `milestone/m5-isolated-execution-provisional-m4` / route `37b05f579320`, and provisional M6 branch `milestone/m6-semantic-validation-provisional-m4` / route `82aac86a3bf9` may develop source in parallel from M4 anchor `94fc5ad`. M5 is blocked on a suitable rootless-isolation host. Acceptance, restack, PR delivery and Trust CI remain dependency ordered M4 → M5 → M6; no milestone is complete merely because its provisional branch exists.

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
- 12:00-15:00: scope freeze, verifier and five reviews on one fingerprint.
- 15:00-18:00: receipts, README, PR preparation and external exact-head gate.

## Control protocol

Milestones remain dependency-gated, not clock-triggered. Calendar time never waives App-owned exact-SHA Trust CI, signed human scopes, real PostgreSQL/security/review gates, the M8 cohort or M9 recovery proof. External writes require exact delegated grants; production mutation is outside this plan. If a gate misses its window, compress only non-exit scope and report the exact blocker rather than claim completion. Cross-links: [root current state](../../../README.md), [roadmap](../../../DARK_FACTORY_ROADMAP.md), [M4 package](../../../factory/README.md).
