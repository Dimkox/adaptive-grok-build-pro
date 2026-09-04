# Dark Factory M0-M9 Dependency-Relative Implementation Plan

Calendar promises are replaced by dependency-relative gates. The M4 local-ready target is the current **2026-09-03** work: freeze the approved source/documentation, rebuild the tracked `2.0.13` candidate from that clean source HEAD, and obtain fresh local exact-head verifier and route-selected review evidence. Those local steps do not establish external acceptance.

**T0** is the time at which an **externally accepted exact M4 SHA** is recorded. T0 is unknown now: no SHA or time may be assigned until a separately authorized successor pull request receives the App-owned exact-SHA Trust CI result, all required signed scopes, and protected merge/acceptance. PR #17 remains a closed exact duplicate of open source PR #21 at `460a8a01`; neither supplies T0 for this changed candidate, and PR #21's unresolved GitGuardian FAILURE metadata is preserved without inspecting or dismissing the finding.

Current reversible source context does not advance the acceptance clock. M5 Tasks 1-6 are provisional at `141e51e75b2bb337fa3bb1544639c6c46c287309`; M6 Task 3 is provisional at `f3b2c0d07116686b27feab4b60166e8a7402d672`; M7 `c8b450f494b3d44b580556c6a612b21a3a780368` is synthetic-only; M8 Task 1 is source-only at `5735e762b8d7571887f6fa4ac9cf10cd1fad1954`; and the locally verified commit `000301796ac19c518ede110b97b9de09dc077cbd` is an M9 source-only Task-1 contract slice. None is accepted or delivered, and M9 still lacks later tasks, real signed input, environment/recovery evidence and production authority.

| Milestone | Earliest entry | Completion clock | Required exit gate |
| --- | --- | --- | --- |
| M4 local-ready candidate | Current 2026-09-03 work | local target only | clean source/docs freeze, direct deterministic package rebuild, fresh exact-head verifier and route-selected reviews |
| M4 external acceptance / T0 | after separately authorized PR preparation | unknown until recorded | App-owned exact-SHA Trust CI, required signed scopes, protected merge and acceptance record |
| M5 isolated execution | T0 | no fixed calendar date | restack on accepted M4, rootless host isolation/capability/orphan proof, reviews and exact-head acceptance |
| M6 semantic validation/repair | only after accepted M5 | no fixed calendar date | restack/renumber, independent validation, bounded repair and exact-head acceptance |
| M7 PR lifecycle/shadow | only after accepted M6 | no fixed calendar date | runtime and real-outcome shadow evidence, reviews and exact-head acceptance |
| M8 earned low-risk autonomy | only after accepted M7 | indeterminate until the cohort exists | at least 30 human-accepted tasks for the exact class/profile tuple, complete metrics and accepted M8 |
| M9 preview/canary/recovery | only after accepted M8 plus signed artifact, environment and recovery evidence | no fixed calendar date | reproducible environment proof, exercised recovery, human-owned production decision and accepted M9 |

The former **2026-09-08 00:00 UTC+3** deadline is a **superseded and unachievable historical target**, not a current promise and never a waiver. The still older 2026-09-15 date is also superseded history. Missing a former date cannot compress, reorder, skip or weaken an exit gate.

## Control protocol

Acceptance remains strictly ordered M4 → M5 → M6 → M7 → M8 → M9. Parallel local source work may be preserved as provisional evidence, but every milestone restacks after its predecessor's accepted exact SHA and earns fresh review/external evidence; no elapsed time converts provisional source into acceptance. External writes require exact delegated grants, and production mutation is outside this plan. Cross-links: [root current state](../../../README.md), [roadmap](../../../DARK_FACTORY_ROADMAP.md), [M4 package](../../../factory/README.md).
