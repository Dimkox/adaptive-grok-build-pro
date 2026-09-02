# Requirements — M7 local shadow handoff

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Required behavior

- Closed bridge/evidence contracts bind product SHAs and task/run/fence/packet/manifest/verdict/evidence/receipt identities.
- A frozen roadmap-compatible `ReadyForPrBundleV1` serializes canonically but exposes only `ready_for_human`.
- Stale linkage, duplicate outcome, incomplete evidence, non-pass or contradictory semantic evidence fail deterministically.
- Operator instructions are fixed local/manual step identifiers; no command, URL, target, token or credential field exists.
- One exact cohort tuple aggregates 1–10,000 outcomes using integer counts and millionths; multiple failure codes are sorted.
- M4 runtime remains unchanged until accepted M5/M6 producer facts exist.

## Bounds and gates

Identifiers are at most 128 bytes; values are NFC UTF-8; public dataclasses are frozen; unknown versions/fields fail closed. The evaluator requires at least 30 human-merged accepted tasks, at least 14 days or a complete release cycle, a 30-task human-only baseline, first-pass acceptance ≥90%, rework ≤10%, validator FN ≤5%, FP/disagreement ≤10%, p95 repairs ≤2 and max repairs ≤3, all cost/latency/deadline/budget bounds, ≥30% median review-time reduction, and zero critical/high misses, security misses, unauthorized effects, rollbacks, escaped defects, duplicate dispatches or unaccounted calls. Injection containment must be 100%.

The maximum output recommendation is human L2 review. Human merge and independent exact-SHA Trust CI remain mandatory.
