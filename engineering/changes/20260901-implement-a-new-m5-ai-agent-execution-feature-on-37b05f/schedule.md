# M5 Provisional Source Schedule

Navigation: [package](brief.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

- Target: `2026-09-08 00:00 UTC+3`.
- Source base: exact M4 review head `460a8a01a6394cac710b4e3f9eea3d94d4beef89`; the former `94fc5ad878e6b15df6418303caada49a3b93bf4c` anchor is lineage only. Separate local M4 candidate `01a10f5` is not this branch's parent, not pushed and not merged, so M5 requires restack plus fresh evidence after M4 settles.
- Source checkpoint: Task 5 is exact `161199bb163e0ba84ac1b32010be87f113df5e86`; Task 6 connects its architecture/contracts/installer/current docs without asserting delivery or acceptance.
- Execution order: contracts/protocol/adapters -> brokers/workspace -> migration/API -> recovery/systemd -> docs/architecture/installer -> locally feasible verification.
- Parallel program rule: M5 and M6 source may develop concurrently on isolated branches; external merge/integration remains M4 -> M5 -> M6. M6 paused at `5c5c371` still targets the old `61db79f` bridge, lacks current result fields/linkage and is `BLOCKED` pending M5 restack.
- Blocking exits: a dedicated rootless host must prove credential and egress isolation, and a trusted live Git snapshot broker must attest the factual result head. This host lacks the required tools and denies unprivileged user namespaces with `EPERM`.
- M7-M9 remain roadmap only. No calendar state creates semantic verdict, PR, trust-level, deployment, external-write, or production authority.
