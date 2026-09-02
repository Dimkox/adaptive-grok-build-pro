# Dark Factory M0-M9 Calendar Implementation Plan

All times are UTC+3. The superseding hard deadline is **2026-09-08 00:00 UTC+3**; normal work freezes at 2026-09-07 20:00 and the final four hours are reserved for exact-SHA gates, receipts, documentation parity and recovery evidence. The older 2026-09-15 deadline is retained only as superseded history.

Current execution checkpoint: M4 `2.0.13` release-state baseline `56e12b2b394436ee227c66d78b1caba8f7317c78` passed 14/14 local verifier gates at `2026-09-02T10:51:29Z`. This bounded follow-up closes exact shipped-ZIP/source parity, all-runtime database bounds/single-transaction cancel, and audited legacy retry exhaustion without fence advance; because it changes the tree, exact-head verification and route-selected reviews must produce fresh receipts after commit. PR #17 closed at `2026-09-02T10:08:38Z` as an exact duplicate of open source PR #21 at `460a8a01`; PR delivery, a new exact-SHA external Trust CI result, unresolved PR #21 GitGuardian FAILURE metadata and merge remain absent. PRs #12/#13 remain old-epoch `ACTION_REQUIRED`; PR #15's current-epoch Trust CI conclusion is `FAILURE` and GitGuardian is `SUCCESS`, with cause not inspected or inferred. Their unique scopes need clean successor extraction and no successor PR is claimed. M5 Tasks 1-6 are provisional at `141e51e75b2bb337fa3bb1544639c6c46c287309` and are the next accepted step after M4, with rootless host proof/restack/reviews pending. M6 Task 3 is provisional at `f3b2c0d07116686b27feab4b60166e8a7402d672`, with deterministic verdict persistence and local focused 67/67, legacy 40/40, PG17 1/1 and architecture PASS, but is quarantined behind accepted M5 and Task 4 is untouched. M7 `c8b450f494b3d44b580556c6a612b21a3a780368` is synthetic-only; M8 Task 1 is `5735e762b8d7571887f6fa4ac9cf10cd1fad1954`; M9 Task 1 is source-only at `000301796ac19c518ede110b97b9de09dc077cbd`. Parallel source work is not acceptance; restack, reviews, PR delivery and Trust CI remain dependency ordered M4 → M5 → M6 → M7 → M8 → M9.

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
