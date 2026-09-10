# Milestone planning analysis

Route: `18ea639b9d02`; inspected base: `64378d28c7b78cace463d96470c1898294b8f196`.
Scope: read-only planning; this report creates no GitHub milestone, issue, release, or authority.

## Why GitHub milestones are empty

The controller's authenticated GitHub observation found zero milestones across all states and zero issues; PR #32 is merged at the inspected base. Repository planning currently lives in the Markdown roadmap, machine-readable project state and durable change packages. Those files do not themselves create GitHub milestone objects. The repository has completed work despite the empty GitHub planning views.

[PROJECT_STATE.json][state] lists M0–M9 as implemented and delivered to main, with per-milestone implementation/review/delivery records. Its top-level observation is dated 2026-09-04 and points at an earlier main SHA; do not use its release/current-delivery fields as a fresh remote-status observation. [PR #32][pr32] adds historical accounting after that recorded observation. A later authorized synchronization should reconcile dates and links without resetting delivered milestones.

[The roadmap][roadmap] distinguishes delivered source from operational qualification. Its unchecked implementation-era lists and stale status phrases should be reconciled against final code and delivery records before creating an issue for supposedly missing code. An existing merge or local review must never be presented as a currently valid external attestation for another SHA.

## Proposed GitHub milestones

Titles below are tracking proposals, not new autonomy grants. Preserve M0–M9 source delivery as complete; use suffixes for remaining operational work. Set dates only after dependencies and observation windows are agreed.

| Proposed title | Initial state | Concrete completion criteria |
| --- | --- | --- |
| M0–M9 — Delivered repository foundation | Closed, retrospective | Link the existing milestone implementation/delivery records and merged PRs; explicitly state that closure covers repository source, not operational autonomy, real cohorts, or production activation. |
| M7.1 — Durable evidence lookup and preflight | Open, next bounded change | An additive persisted preflight resolves existing task/run records against independently observed exact-subject acceptance and external evidence; lookups survive restart; replay, mismatched identity, expiry, supersession and changed trust context are rejected. Existing V1 blocked semantics, L2 ceiling and absent external capabilities remain intact. |
| M7.2 — Operational shadow PR cycle and measurements | Open, dependent on M7.1 | An explicitly authorized, bounded issue → task → isolated execution → independent validation → PR → human decision cycle is demonstrated; WIP/PR-age/cost controls and ambiguous-write recovery work; every run captures task/profile identity, acceptance provenance and complete-or-explicitly-partial intervention/quality/recovery measurements. |
| M8.1 — Exact-profile cohort qualification through L2 | Open, dependent on M7.1/M7.2 | Bound factual records satisfy the existing per-profile sample, observation/baseline, audit, quality, cost, latency and safety gates; changed profile components start new cohorts; recommendations remain separate from activation and never exceed L2; currentness and demotion are exercised. |
| M9.1 — Reproducible staged delivery and recovery | Open, activation separately gated | An operational adapter uses a verified signed artifact for the exact merged SHA; preview/staging and bounded canary are reproducible; success/abort signals are measured; actual rollback/halt is exercised and feeds the trust profile; required human production promotion is preserved. |
| L3–L4 — Approved bounded automation and revocation | Proposed, blocked on separately approved policy | An approved class/authority contract defines allowed merge effects and audit; external exact-SHA checks and required signed scopes remain authoritative; monitored incidents, bad merges, rollback or evidence drift revoke the affected permission; representative failure drills pass. |
| L5 — Defined end-to-end operational qualification | Proposed, definition first | Approve a measurable L5 definition for named task classes, environments, allowed effects and intervention boundaries; demonstrate repeated end-to-end operation, cost/quality targets and recovery under that protocol; publish the qualification result with remaining exclusions. A label alone cannot close this milestone. |

The current roadmap defines suggested L0–L4 levels, while the actual M8 contract caps authority at L2. The existing [V1 bridge][bridge] returns false for both acceptance and currentness; the first M7.1 implementation adds a persisted lookup/preflight alongside it and preserves these V1 semantics. Therefore L5 requires an explicit definition and protocol; an offline feature bearing “L5” in its name does not establish that level. Higher-autonomy work must not be folded into the present M7 lookup change. [M8 roadmap][m8], [M8 contract implementation][autonomy].

## Historical evidence belongs in the plan

Existing real project delivery is useful source evidence and must not be reset to zero. Reconcile recoverable native task IDs, validation, explicit acceptance, intervention windows, historical profile versions and outcomes before commissioning additional qualification work. Private source inventories and details stay outside the public repository; public milestone bodies should link the generic [historical accounting runbook][history] and describe evidence categories only, with no private project names or counts.

PR counts, passing tests, deployment narratives and User-type actors do not automatically supply human task acceptance or complete intervention coverage. Imported history currently has `m8_qualification: not_evaluated` and `authority_effect: none`. A future cohort can consume an old record only after its exact required bindings are independently established; no synthetic backfill or present-day profile defaults.

## Recommended issue breakdown for M7.1

1. **Approve the acceptance/currentness trust contract.** Define the exact subject tuple, external authority identifiers, verified receipt format, bounded expiry/observation policy and missing/stale/replayed outcomes. Distinguish explicit task acceptance from PR merge, CI success and historical importer claims. Deliver the typed contract and adversarial examples for the named design gate.
2. **Persist immutable M7 observations in the existing PostgreSQL store.** Add a versioned migration and bounded repository methods tied to existing task/run identities; define uniqueness, idempotent replay, conflicting-observation rejection, provenance and retention. Provide recovery/rollback notes without rewriting old rows or migrations.
3. **Read independently issued exact-SHA external evidence.** Define the narrow read-only lookup/ingestion boundary; bind repository, task/run, PR head/base, App-owned policy-epoch check and attestation/trust-context identity. Reject wrong App, wrong subject, stale policy/holdout, unsupported receipt and missing independent verification. The repository must not mint external authority.
4. **Expose additive M7 evidence preflight.** Join durable task/run and independently verified facts with explicit currentness checks; return immutable bounded observations and reason codes through a new additive contract. Preserve existing V1 blocked bundles and always-false bridge properties; this issue does not unlock M8 eligibility or an operational action.
5. **Integrate the typed preflight and prove recovery.** Wire only the reviewed local preflight path; add causal regression, restart, duplicate/conflict, transaction-race, supersession, expiry and trust-context-change cases using isolated storage. Confirm that caller-supplied flags cannot turn missing evidence into eligibility.
6. **Close with operationally useful evidence.** Record bounded success/stale/replay/unavailable counters and a recovery runbook; update the public state/roadmap for the precise capability delivered; bind route verification/reviews and external PR acceptance to the final artifact. Do not close cohort, provider, merge automation or deployment milestones as a side effect.

Dependency order: 1 → 2 and 3 → 4 → 5 → 6. The items may be one coherent PR if the reviewed design supports it; milestones and issues are organizational metadata and do not replace routed evidence or the external merge gate.

## Durable handoff fact

An empty GitHub milestone/issue view reflects unsynchronized planning metadata, not absence of delivered M0–M9 source. Track remaining operational acceptance with separately named milestones, preserve historical project evidence privately, and treat M7 durable acceptance/currentness as the next bounded dependency rather than claiming L5 from a task count.

[state]: https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/PROJECT_STATE.json
[pr32]: https://github.com/Dimkox/adaptive-grok-build-pro/pull/32
[roadmap]: https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/DARK_FACTORY_ROADMAP.md
[m7]: https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/DARK_FACTORY_ROADMAP.md#L822
[m8]: https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/DARK_FACTORY_ROADMAP.md#L911
[autonomy]: https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/factory/src/adaptive_factory/autonomy.py#L122
[bridge]: https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/factory/src/adaptive_factory/m7_autonomy_bridge.py#L168
[history]: https://github.com/Dimkox/adaptive-grok-build-pro/blob/64378d28c7b78cace463d96470c1898294b8f196/engineering/runbooks/historical-autonomy-evidence.md
