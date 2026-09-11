# repo_explorer: M8/M9 product vs operational evidence

Inspected **origin/main** `fd51dcfed6b33f4a8707c0db602328146df17cc9` (VERSION `2.0.15`). Workspace checkout is stale 2.0.12 and was not treated as product. `origin/docs/v2.0.15-published-handoff:PROJECT_STATE.json` binds the same SHA and states v2.0.15 is published repository delivery only.

Recommended implementation base: **`fd51dcfed6b33f4a8707c0db602328146df17cc9`**.

## Implemented on main (contracts + algorithms, not operations)

| Path | Role |
| --- | --- |
| `factory/src/adaptive_factory/autonomy.py` | M8 tuple, `CohortTaskEvidenceV1`, `CohortEvidenceV1`, `AutonomyProfileV1`, `PromotionRecommendationV1`, `evaluate_autonomy`, `demote_profile` |
| `factory/src/adaptive_factory/m7_autonomy_bridge.py` | Thin M8 envelope over actual M7 producer bodies; **`external_acceptance_available` and `currentness_available` are hardcoded `False`** |
| `factory/contracts/jsonschema/earned-autonomy.v1.schema.json` | Closed JSON Schema for M8 records |
| `factory/contracts/jsonschema/shadow-cohort.v1.schema.json` | M7 shadow cohort producer schema |
| `factory/contracts/jsonschema/m7-autonomy-bridge.v1.schema.json` | Bridge envelope schema |
| `factory/tests/test_autonomy.py` | **Synthetic** 30-row fixtures; file docstring: never factual evidence |
| `factory/src/adaptive_factory/recovery.py` | M5/M6 **execution** workspace recovery (orphans), not M8/M9 promotion recovery |
| `delivery/src/adaptive_delivery/m8_boundary.py` | Reparses M8 records; `SOURCE_STATUS = blocked_pending_durable_m8_lookup`; durable flags `False`; `m8_gate_reasons` |
| `delivery/src/adaptive_delivery/{controller,evaluator,fake_environment,recovery}.py` | M9 staged delivery: preview/staging/bounded_canary only; in-memory fake adapter; least-authority recovery |
| `delivery/tests/test_m8_boundary.py`, `test_recovery.py` | Synthetic M8 handoff + local recovery identity tests |

M8/M9 **source** is already on main (v2.0.13 lineage, still present at 2.0.15). Checkpoints: M8 `a937ac8d`, M9 `64b10689`.

## How gates are represented (fail-closed)

**Cohort size / human-accepted tasks**

- Schema + `CohortEvidenceV1`: `minimum_human_acceptances` integer **minimum 30**.
- Qualification: every linked M7 outcome must be `human_decision == "merged_accepted"`; else `human_acceptance_missing`. Count vs floor: `insufficient_acceptances`.
- M9 `m8_gate_reasons`: `accepted_task_count < 30` **or** count ≠ `len(tasks)` → `m8_profile_ineligible`.

**Activation**

- `PromotionRecommendationV1.separate_activation_required` **must be `True`**.
- `external_action_authorized` **must be `False`** on recommendation and demotion.
- `evaluate_autonomy` always emits those two constants. There is **no activation API or store** in this tree.

**L2 cap**

- Tuple `authority_ceiling` const `"L2"`.
- Promotion is one level: `LEVELS[index(current)+1]`; at L2, `already_at_ceiling`.
- Existing profile starts at stored level; missing/expired profile is **L0**.

**L0 demotion**

- `demote_profile`: any valid trigger set → `current_level="L0"`, `halted=True`, `resulting_level="L0"`, `halt=True`, no external action.
- Trigger enum: security/authorization failure, incorrect_merge, rollback, escaped_defect, invalid_attestation, policy_bypass, unexplained_regression.

**M7 durable authority**

- Bridge always reports acceptance/currentness unavailable.
- Evaluator then returns `m7_acceptance_missing` / `m7_currentness_missing` even for a perfect 30-row synthetic cohort (`test_closed_m7_bundle_blocks_forged_thirty_row_qualification`).
- Bundles in synthetic fixtures are `blocked_pending_durable_lookup` → `m7_bundle_blocked` first.

**M9 production**

- `evaluator` / `controller` / `fake_environment` / `recovery`: `production is unreachable` / `production recovery is unreachable` / only three nonproduction stages representable.
- Fake adapter is sealed in-memory, not a provider.

## Factual cohort records on main: **0**

Counted on `origin/main`:

- No JSON artifacts of `CohortEvidenceV1` / earned-autonomy instances outside **schema**.
- `"minimum_human_acceptances"` appears in schema, `autonomy.py`, `test_autonomy.py`, `synthetic_fixtures.py` only.
- Tests explicitly label 30-row payloads as synthetic (`synthetic-m8-wire-cohort`, `synthetic/repository`).
- Do not invent or count those fixtures as human-accepted tasks.

Durable stores **absent from the repository** (and from PR domain): PostgreSQL runtime, signed human receipts, Trust CI currentness lookups, environment/provider registries, production grant store. `PROJECT_STATE.json` `intentionally_untracked` lists those.

## Fail-closed behavior (current)

1. Cannot claim `qualified` without durable M7 acceptance + currentness (both locally false).
2. Cannot set `external_action_authorized=True` or skip `separate_activation_required`.
3. Cannot advance M9 into `production` or recover production.
4. Demotion is always L0 + halt.
5. M9 refuses ineligible/halted/expired/blocked-bundle M8 handoffs (`m8_profile_ineligible`, `m8_recommendation_ineligible`, `m8_evidence_expired`).
6. M8 producer pin in delivery: `PROVISIONAL_M8_PRODUCER_SHA = f53275d5ed84022200419b399c799a995ed91a45` (historical M8 commit, not `fd51dcf`).

## What would have to change (operations vs code)

**To RECORD a factual cohort (still not activation)**

- Outside-repo: ≥30 distinct real tasks with M7 `merged_accepted`, human evidence digests, audit sampling covering every UTC day in the window (≥20% audit rate, all audits accepted), zero security/auth/duplicate/demotion counts, quality/cost/latency within tuple floors.
- Durable M7 lookup so `external_acceptance_available` and `currentness_available` can be **true without forging** (today they cannot be set on the dataclass).
- Persist `CohortEvidenceV1` bound to a real `AutonomyTupleV1` (repo, policy, runner, holdout, provider≠validator).
- This is **evidence + store + likely a bounded bridge change** so availability is derived from signed lookup, not a local boolean.

**To ACTIVATE autonomy**

- Separate human-signed activation record (not `evaluate_autonomy` output).
- Policy/store that may set a live profile `current_level` to L1/L2 **after** qualification, still L2-capped, still demote-to-L0.
- Explicit operational grant; local receipts and Trust CI merge checks do **not** activate M8 (`PROJECT_STATE` / roadmap).

**To deploy / qualify M9**

- Signed delivery input (promotion + observations) against a **real** environment/provider, not `FakeEnvironmentAdapter`.
- Exercised recovery on that environment (current `test_recovery.py` is local identity/plan only).
- Human production authority **outside** the agent; production remains unreachable in code until that authority exists.
- Pin/update M8 producer SHA if the live producer is `fd51dcf` rather than `f53275d5`.

## Ruling for this change

Repository product at **`fd51dcf` already implements M8/M9 algorithms**. D5 cannot be completed by fabricating 30 tasks or flipping fail-closed flags. Missing data: **0 factual cohort records**, **no durable currentness/acceptance**, **no activation store**, **no operational provider**, **no exercised production recovery**, **no human production grant**. Next implementation, if any, should be an evidence/ingestion path on SHA `fd51dcf`, not a restack of synthetic qualification.
