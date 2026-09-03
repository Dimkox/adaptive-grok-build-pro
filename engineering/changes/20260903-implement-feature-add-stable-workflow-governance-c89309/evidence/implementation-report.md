# Stable workflow synthesis implementation report

Status: implementation complete locally; durable change remains `implementing` pending parent-owned exact-head verification and route-selected independent reviews.

## Delivered locally

- Closed exact authority for Superpowers v6.3.0, BMAD v6.11.0 and Spec Kit v1.0.4 with tag-object/peeled SHAs, official URLs and MIT attribution; the immutable config instance and its real closed Draft 2020-12 schema are separate, and no upstream bytes were copied.
- Additive deterministic typed task DAG, monotonic states, BMAD-style canonical ledger, SpecKit-style intent→task traceability and stable `missing|partial|contradicts|unrequested` findings, bounded convergence/repair, content-addressed snapshots and closed digest-chain journal.
- Weekly exact-due local review intake for newest qualifying stable releases and bounded post-pin head/compare candidates, with strict GET-only allowlist/JSON/UTF-8/body/tag/header/timeout/call bounds, normalized untrusted metadata, atomic durable ignored state, contention/no-I/O behavior and unknown/stale/degraded semantics.
- Explicit CLI, inert hardened source-only systemd units, installer contract/CLI inventory, distinct architecture node and sole read-only GitHub edge, and bounded router regression repair.
- Factual repository current-state documentation distinguishes the separate observed direct unsandboxed executor pilot from unproven M5 broker isolation; the stable monitor cannot interact with it.

## Verification

- Design gate: change-spec v2 PASS, 11/11 ACs mapped.
- Focused final: 51/51 PASS; Ruff and Bandit PASS.
- Architecture validate, drift and generated diagram parity: PASS.
- Full root: 578/578 PASS in 383.962 seconds.
- Post-root contract-enrollment repair: impacted stable/architecture/installer tests 101/101 PASS; stable/router 52/52 PASS; exact-predecessor architecture fitness PASS; Ruff and Bandit PASS. Parent exact-head verification remains required for the frozen commit.
- Review remediation: reproduced and repaired all e56045a findings with adversarial state/journal/snapshot/lock, realistic GitHub topology, concrete transport/deadline, bounded synthesis readiness/input, recovery, no-subprocess, router morphology and CLI/systemd regressions. Focused stable/review/router is 65/65 PASS and expanded architecture/fitness/structure/installer/project-state is 196/196 PASS; architecture, exact-base fitness and static gates remain PASS. The journal is now projection authority, runtime errors are fixed/redacted, compare stays frozen-pin anchored, and exact-SHA claims remain exclusively outside this monitor in Trust CI.
- Timing replan: at `2026-09-03 16:00 UTC+3`, the superseding whole-program deadline became `2026-09-04 23:59 UTC+3`. Current surfaces separate stable/M4 source preparation from event-triggered accepted M4 → M5 → M6 → M7 → M8 → M9; unevidenced isolation, human cohort, signed-input and external gates make the deadline at risk, not promised.

## Residual boundaries

No live GitHub sweep, scheduler installation/enablement, source/pin update, package install, PR/push/merge, Trust-CI check, release, deployment or production action occurred. ETag is only a bounded cache hint; branch head is observation only. Final verifier, independent reviews, PR delivery and external exact-SHA Trust CI remain parent/human gates.
