# D5 — M8/M9 fail-closed qualification accounting

Change ID: `20260906-d5-m8-factual-cohort-and-m9-operational-qualific-4a3636`
Route: `4a3636699111`
Base: `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9` (published 2.0.15)
Write owner: `general_implementer`

## Problem

The user chose D5: M8 factual cohort (≥30 human-accepted tasks + activation) and M9 operational qualification. M8/M9 **algorithms** are already on `main`. Factual cohort count is **0**. Durable M7 acceptance/currentness are hardcoded unavailable. There is no activation store. M9 is a sealed in-memory adapter. Completing D5 as ops would require fabricating tasks or claiming production.

## Outcome

A reviewed checkout of `fd51dcf` can evaluate M8 cohort/activation accounting and M9 operational qualification and receive a closed fail-closed status: `factual_accepted_task_count=0`, not activated, not operational. Synthetics never count toward 30. Deadline `2026-09-08` does not waive gates. D5 remains incomplete by design; accounting exists, ops do not.

## Scope

### In scope

- New branch from `fd51dcf`, not this 2.0.12 checkout, not PR #12/#28.
- `FactualCohortLedgerV1` keyed by `AutonomyTupleV1` digest; empty is valid; missing = 0.
- Fail-closed `append` that cannot store a real row while M7 flags are false.
- `evaluate_activation` always `activated=false` on this tree; no `activated is True` test.
- `evaluate_m9_operational_qualification` all four evidence classes false; not wired into `DryRunController`.
- Tests: empty, synthetic-30, forged activation/production, tuple mutation → new empty cohort.
- Append-only `decisions.md` fact. Local verify + reviews + new PR. No merge.

### Out of scope

- Fabricating 30 human-accepted tasks or counting synthetics toward the floor.
- Flipping `external_acceptance_available` / `currentness_available`.
- Auto-merge, L3/L4, activation API that can succeed, production adapter, migrations 019+, VERSION/tag/ZIP.
- Live pilot, landing-profile refresh, PR #12/#13/#15/#28, human keys, GitHub Actions.
- Claiming D5 complete.

## Constraints

- Keep L2 cap, L0 demotion, `separate_activation_required=true`, `external_action_authorized=false`.
- Do not restack `evaluate_autonomy` / `DryRunController` except as call sites.
- No factory PostgreSQL changes. Ledger is local/temp JSON or equivalent, not a committed DB.
