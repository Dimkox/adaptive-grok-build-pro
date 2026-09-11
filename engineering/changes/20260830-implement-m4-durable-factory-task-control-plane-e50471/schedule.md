# Dark Factory M0–M9 Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver milestones M0 through M9 on a dependency-bound calendar, preserving exact-SHA Trust CI, signed human approval, verification, review, rollback, and recovery gates.

**Architecture:** M0 is the external trust root. M1, M2, and M3 provide the typed intent, executable architecture, and controlled-learning interfaces consumed by M4; M4 through M9 then execute sequentially. Calendar time never overrides a failed or missing gate.

**Tech Stack:** Python 3, PostgreSQL, Docker/rootless isolated runners, GitHub App Check Runs, repository change packages, exact-SHA receipts, OpenAPI and JSON Schema.

**Spec:** `DARK_FACTORY_ROADMAP.md` and `engineering/changes/20260830-implement-m4-durable-factory-task-control-plane-e50471/change-spec.yaml`

## Global Constraints

- All dates and times in this document use UTC+3 (Moscow time).
- The superseding hard delivery deadline for the complete M0–M9 program is **2026-09-08 00:00 UTC+3**; normal execution must finish by 2026-09-07 20:00 so the final four hours remain a protected release/recovery reserve.
- Product changes are PR-only; direct pushes to protected/shared branches are prohibited.
- A milestone cannot cross its exit gate without the App-owned exact-SHA Trust CI check and every required signed approval scope.
- Local verification and review receipts are workflow evidence, never merge authority.
- Human approval private keys remain outside the agent environment.
- M4 consumes the accepted M1/M2/M3 interfaces; it does not recreate them.
- M5 through M9 start sequentially only after the predecessor reaches its external exit gate.
- A late external gate does not permit bypassing trust controls. Recover time first by removing non-exit-criterion scope, increasing safe read-only parallel preparation, and shortening idle handoffs; if the deadline becomes impossible, record and report the exact blocker immediately.
- M8 is evidence-bound, not merely time-bound. M9 cannot start until the shadow cohort satisfies M8 exit criteria.

---

## Current compressed milestone calendar

| Milestone | Actual or planned start | Planned completion | Entry gate | Exit gate |
|---|---:|---:|---|---|
| M0/M1/M2 — prerequisite closure | 2026-08-31 21:00 | 2026-09-01 06:00 | External App/host and current heads available | Fresh M0 proof; accepted M1; PR #16 integrated into M2; exact-head checks and signed scopes |
| M3 — Controlled Knowledge and Debt | 2026-09-01 06:00 | 2026-09-01 14:00 | Exact accepted M2 head | Restacked PR #11, exact-head Trust CI, signed scopes, accepted head |
| M4 — Durable Factory Control Plane | 2026-09-01 14:00 | 2026-09-02 18:00 | Exact accepted M1/M2/M3 and fresh M0 proof | Real PostgreSQL exit gate, five reviews, exact-SHA Trust CI |
| M5 — Isolated Execution Plane | 2026-09-02 18:00 | 2026-09-03 18:00 | M4 external exit gate | Ephemeral isolation, scoped capabilities, orphan recovery |
| M6 — Semantic Validation and Repair | 2026-09-03 18:00 | 2026-09-04 14:00 | M5 external exit gate | Independent validation and bounded repair proven |
| M7 — PR Lifecycle and Shadow Mode | 2026-09-04 14:00 | 2026-09-05 12:00 | M6 external exit gate | Automated PR lifecycle runs with human shadow decisions |
| M8 — Earned Low-Risk Autonomy | 2026-09-05 12:00 | 2026-09-06 20:00 | M7 shadow telemetry available | Frozen documentation-only candidate class and at least 30 human-accepted tasks meet evidence thresholds |
| M9 — Preview, Canary, and Recovery | 2026-09-06 20:00 | 2026-09-07 20:00 | M8 evidence exit gate | Non-production preview/staging/canary and recovery proof |
| Final program reserve | 2026-09-07 20:00 | **2026-09-08 00:00** | M9 implementation frozen | Final exact-SHA checks, receipts, rollback/recovery evidence, no new scope |

## Immediate critical path

### Task 1: Publish and validate the isolated M2 Trust CI hotfix

**Files:**
- Existing branch: `fix/m2-trust-ci-zombie-process-group`
- Evidence: `engineering/changes/20260831-fix-trust-ci-bounded-workspace-process-cleanup-i-fa3ae6/`

**Interfaces:**
- Consumes: M2 head `9493741dd34fdfa1e37efdc09b35e30d5535be7c`
- Produces: externally checked stacked hotfix head `5b2a259be0180388d2648c0f535a2469ea91196e`

- [x] **2026-08-31 18:50:** Complete local exact-HEAD verification, reviews, receipts, and clean worktree.
- [x] **2026-08-31 19:00–19:30:** Materialize exact delegated grants for the authorized branch push and stacked PR creation.
- [x] **2026-08-31 19:30–20:30:** Push the hotfix branch and open PR #16 against `milestone/m2-executable-architecture`.
- [x] **2026-08-31 20:30–21:00:** Confirm success of `adaptive-trust-ci/verified@06ecf1c875bc` on exact head `5b2a259be0180388d2648c0f535a2469ea91196e`. This proves the hotfix PR head only; PR #16 is not marked merged or integrated.

### Task 2: Close M2 and restack M3

**Files:**
- M2 branch: `milestone/m2-executable-architecture`
- M3 worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-m3`
- Pull requests: `#10` and `#11`

**Interfaces:**
- Consumes: accepted hotfix and current M2/M3 heads
- Produces: accepted M2 and M3 heads for the M4 base

- [ ] **2026-08-31 21:00–23:00:** Obtain the required signed scope and integrate checked PR #16 into M2 without changing tested bytes; preserve the exact accepted identity.
- [ ] **2026-08-31 23:00–2026-09-01 03:00:** Advance PR #10 to the accepted hotfix identity, run its fresh exact-head Trust CI, obtain its signed scopes, and close M0/M1 evidence in parallel.
- [ ] **2026-09-01 03:00–06:00:** Accept M2 only after all exact-SHA gates pass; preserve the dirty M3 worktree and establish an isolated exact-base restack workspace.
- [ ] **2026-09-01 06:00–10:00:** Restack M3 on the accepted M2 head, resolve only bounded overlaps, and run focused plus full local verification.
- [ ] **2026-09-01 10:00–12:00:** Run route-selected reviews, record fingerprint-bound receipts, update PR #11, and start its exact-head Trust CI.
- [ ] **2026-09-01 12:00–14:00:** Obtain required `database` and `governance` scopes and accept M3; prepare M4 fixtures read-only while the external gates run.

### Task 3: Start M4 implementation

**Files:**
- Change package: `engineering/changes/20260830-implement-m4-durable-factory-task-control-plane-e50471/`
- Planned service root: `factory/`

**Interfaces:**
- Consumes: exact accepted M1/M2/M3 interfaces and fresh M0 observation
- Produces: durable task/run/attempt control-plane contracts consumed by M5

- [ ] **2026-09-01 14:00–15:00:** Record fresh M0 availability and exact accepted M1/M2/M3 identities; regenerate the M4 route on that base.
- [ ] **2026-09-01 15:00–20:00:** Implement immutable task/run/attempt contracts and checksum-locked PostgreSQL migrations from failing contract/state-machine tests.
- [ ] **2026-09-01 20:00–2026-09-02 02:00:** Implement idempotent intake, transactional transitions, leases, fencing, capacity, and restart semantics.
- [ ] **2026-09-02 02:00–08:00:** Implement budgets, retries/dead-letter, kill switches, append-only audit, authenticated local API/CLI, and bounded reconciliation.
- [ ] **2026-09-02 08:00–12:00:** Run real disposable PostgreSQL concurrency, failure, restart, fencing, accounting, and reconciliation tests; remediate failures.
- [ ] **2026-09-02 12:00–15:00:** Freeze product scope; run full verifier and the code, test, security, data, and release reviews on one fingerprint.
- [ ] **2026-09-02 15:00–18:00:** Record receipts, update README, open/update the M4 PR, and require exact-head Trust CI and every signed scope before the M4 exit gate.

## Sequential delivery windows

### Task 4: M5 — Isolated Background Execution Plane

- [ ] **2026-09-02 18:00:** Start integration only after the M4 external exit gate; permit read-only design/test preparation before it.
- [ ] **2026-09-02 18:00–2026-09-03 12:00:** Build and test workspace management, immutable packets, restricted launch, secret/network boundaries, artifacts, manifests, and orphan reconciliation.
- [ ] **2026-09-03 12:00–18:00:** Complete isolation drills, verification, reviews, PR, exact-SHA Trust CI, and signed approvals.

### Task 5: M6 — Independent Semantic Validation and Bounded Repair

- [ ] **2026-09-03 18:00:** Start integration only after the M5 external exit gate; prepare schemas/evals read-only during late M5.
- [ ] **2026-09-03 18:00–2026-09-04 08:00:** Implement and test structured findings, independent validator/adjudicator contexts, bounded repair loops, and stop conditions.
- [ ] **2026-09-04 08:00–14:00:** Complete adversarial validation, verification, reviews, PR, exact-SHA Trust CI, and approvals.

### Task 6: M7 — Automated Pull-Request Lifecycle and Shadow Mode

- [ ] **2026-09-04 14:00:** Start integration only after the M6 external exit gate; prepare PR fixtures read-only during late M6.
- [ ] **2026-09-04 14:00–2026-09-05 06:00:** Implement and test delegated branch/PR flow, exact artifact summaries, source linkage, rate limits, and human shadow decisions.
- [ ] **2026-09-05 06:00–12:00:** Complete lifecycle drills, verification, reviews, PR, exact-SHA Trust CI, and approvals.

### Task 7: M8 — Earned and Revocable Low-Risk Autonomy

- [ ] **2026-09-05 12:00:** Freeze M8 to one documentation-only candidate class and start only after the M7 exit gate; cohort definitions and replay fixtures may be prepared read-only beforehand.
- [ ] **2026-09-05 12:00–2026-09-06 14:00:** Execute at least 30 human-accepted representative tasks, recording quality, overrides, rollback, latency, and false-negative evidence without automatic authority expansion.
- [ ] **2026-09-06 14:00–20:00:** Evaluate thresholds, candidate-class bounds, revocation, policy identity, reviews, exact-SHA Trust CI, and signed scopes. M8 promotion occurs only if every gate and the minimum cohort pass; otherwise report the exact blocker and do not claim promotion.

### Task 8: M9 — Preview, Staging, Canary, and Recovery-Aware Delivery

- [ ] **2026-09-06 20:00:** Start only after the M8 evidence exit gate; preview/recovery fixtures may be prepared read-only during the cohort.
- [ ] **2026-09-06 20:00–2026-09-07 10:00:** Implement and test exact-SHA non-production previews, smoke/contract/migration/rollback checks, signed promotion requests, staging, canary evaluation, halt, and automated rollback.
- [ ] **2026-09-07 10:00–16:00:** Execute non-production staging/canary and recovery drills; production mutation remains outside scope without separate authorization and approvals.
- [ ] **2026-09-07 16:00–20:00:** Complete verification, security/release reviews, exact-SHA Trust CI, signed scopes, recovery evidence, and documentation parity. Claim M9 only if every gate passes; otherwise report the exact blocker.
- [ ] **2026-09-07 20:00–2026-09-08 00:00:** Freeze scope; use the protected reserve only for final exact-SHA receipts, rollback proof, documentation parity, and release decision. No new feature work enters this window.

## Schedule-control protocol

At every work session:

1. Read this file and the active route before taking a development action.
2. Mark a checkbox complete only when its repository/external evidence exists.
3. Do not start a dependent milestone because its clock time arrived; require its entry gate.
4. When a gate is late, append a dated schedule-change record below immediately; recover time without bypassing the gate and escalate as soon as the 2026-09-08 00:00 deadline is threatened.
5. Preserve the original baseline dates; record adjustments as deltas rather than rewriting history.
6. Keep all external writes behind exact delegated grants and all merges behind the App-owned exact-SHA check plus signed scopes.

## Schedule-change record

### 2026-08-31 — Deadline compression

- Previous program deadline: 2026-10-14 18:00 UTC+3.
- User-mandated hard deadline: **2026-09-15 00:00 UTC+3**.
- Recovery strategy: continuous execution, read-only preparation of successor milestones, minimum exit-criterion scope, compressed handoffs, and a protected final four-hour reserve; no Trust CI, signed-approval, security, migration, or recovery gate is waived.

### 2026-08-31 — Superseding management deadline

- Superseded program deadline: 2026-09-15 00:00 UTC+3 (retained above as historical schedule-change evidence).
- New user-mandated hard deadline: **2026-09-08 00:00 UTC+3**.
- Recovery strategy: continuous hourly handoffs, read-only successor preparation, minimum exit-criterion implementation, one frozen documentation-only M8 candidate class, a minimum cohort of 30 human-accepted tasks, and non-production-only M9 validation, with the final four hours protected.
- The deadline cannot override exact-SHA Trust CI, signed approvals, sequential integration, PostgreSQL/security/review gates, the M8 evidence cohort, or M9 recovery proof. M8 promotion and the M9 completion claim occur only if their gates pass; otherwise the exact blocker is reported instead of fabricating delivery.
