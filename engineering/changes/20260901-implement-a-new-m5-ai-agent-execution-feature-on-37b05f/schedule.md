# M5 Provisional Source Schedule

Navigation: [package](brief.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

- Target: `2026-09-08 00:00 UTC+3`.
- Source lineage: Tasks 1-6 source is exact `141e51e75b2bb337fa3bb1544639c6c46c287309`; historical Task 5 checkpoint `161199bb163e0ba84ac1b32010be87f113df5e86` remains evidence only.
- Current restack checkpoint: normal merge onto exact M4 `56e12b2b394436ee227c66d78b1caba8f7317c78`, preserving M4 migration `013` and moving M5 execution to `014`. A newer M4 exact SHA requires another normal merge; no acceptance or delivery is asserted.
- Execution order: contracts/protocol/adapters -> brokers/workspace -> migration/API -> recovery/systemd -> docs/architecture/installer -> locally feasible verification.
- Parallel program rule: M5 and M6 source may develop concurrently on isolated branches; external merge/integration remains M4 -> M5 -> M6. M6 Task 3 at `f3b2c0d07116686b27feab4b60166e8a7402d672` is `BLOCKED` pending accepted-M5 restack and migration move to `015`.
- Blocking exits: a dedicated rootless host must prove credential and egress isolation, and a trusted live Git snapshot broker must attest the factual result head. This host lacks the required tools and denies unprivileged user namespaces with `EPERM`.
- M7-M9 remain roadmap only. No calendar state creates semantic verdict, PR, trust-level, deployment, external-write, or production authority.
