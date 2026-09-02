# M5 Provisional Source Schedule

Navigation: [package](brief.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

- Target: `2026-09-08 00:00 UTC+3`.
- Source root: exact final local M4 `571cad7877431ac5ab5779b53fe9f7effd6859ce` (tree `9d29f25d3af4fc9f97bbb8b3d4970906b69338fd`).
- Slice 01: contracts/protocol/adapters plus brokers/workspace and partial architecture ownership at truth-bound head `34dd6184fc506bb927699b382f13546e59503974` (tree `c9c4db5102534af60b7095479c4cf06f51a1fcfb`; product checkpoint `9ba284e`); exact-predecessor fitness and focused checks pass, but no delivery authority exists.
- Slice 02: exact predecessor `34dd6184fc506bb927699b382f13546e59503974`; add migration `014`, execution persistence/API lifecycle and its separate additive OpenAPI fragment, then run focused and explicit-predecessor fitness checks.
- Successor order: slice 02 migration `014`/execution API -> slice 03 security/recovery/systemd -> slice 04 final docs/installer/state/exact-head verification. Each slice uses its immediate predecessor for fitness and remains PR/external-gate dependent.
- Provisional M6/M7/M8 source may remain isolated, but external merge/integration remains M4 -> M5 slices 01-04 -> M6 -> M7 -> M8.
- Blocking exit: a dedicated rootless host must prove credential and egress isolation. This host lacks the required tools and denies unprivileged user namespaces with `EPERM`.
- M7-M9 remain roadmap only. No calendar state creates semantic verdict, PR, trust-level, deployment, external-write, or production authority.
