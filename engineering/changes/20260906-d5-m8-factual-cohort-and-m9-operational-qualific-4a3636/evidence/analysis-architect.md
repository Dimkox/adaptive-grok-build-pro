# Architect — D5 M8 factual cohort + M9 operational qualification

Route: `4a3636699111`  
Change: `20260906-d5-m8-factual-cohort-and-m9-operational-qualific-4a3636`  
Authority SHA: `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9` (published 2.0.15 product source)  
This checkout: stale `2.0.12` on `fix/path-aware-shell-policy-circuit-breaker`. Do not implement from it.  
PR #12 worktree: out of scope. Do not stack.  
Role: read-only design. No implementation in this report.

## 1. Ruling

Ship the smallest **library-only** vertical that makes the current world machine-checkable:

1. An exact-tuple **factual ledger** whose honest state is **empty / count = 0**.
2. A **fail-closed activation predicate** that remains false.
3. A **fail-closed M9 operational qualification predicate** (signed input / env / recovery / production authority) that remains false.

Do **not** activate M8, auto-merge, raise the L2 cap, add a real delivery adapter, fabricate 30 tasks, touch migrations `001`–`018`, edit deployed Trust CI, add GitHub Actions, rebuild packages, or merge.

Empty cohort is a valid ledger state. Missing records count as zero, never as “unknown, maybe 30.”

## 2. What origin/main already owns

M8 and M9 **source** is already on `main` via PR #22 (`v2.0.13`). That is repository product, not operational activation.

| Layer | Location on `fd51dcf` | Current bound |
| --- | --- | --- |
| Exact trust-profile tuple | `factory/src/adaptive_factory/autonomy.py` `AutonomyTupleV1` | `task_class=low_risk_text_only`, `authority_ceiling=L2`. Digest is the cohort key. |
| Closed evaluation cohort | `CohortEvidenceV1` | `1..10000` tasks; `minimum_human_acceptances >= 30`; zero-tolerance security/authz/dup/demotion. |
| Recommendation | `evaluate_autonomy` | One-level, `separate_activation_required=true`, `external_action_authorized=false`. No `activate()`. |
| Demotion | `demote_profile` | Immediate `L0` + `halt=true`. |
| M7 producer bridge | `m7_autonomy_bridge.py` | `1..10000` bundles; `external_acceptance_available` and `currentness_available` are **hard `False`**. |
| M7 shadow cohort | `ShadowCohortV1` | Outcomes **must be non-empty**. |
| Tests | `factory/tests/test_autonomy.py` | Header: “Synthetic actual-M7 bridge and M8 algorithm fixtures; **never factual evidence**.” Default `task_count=30`. |
| M9 handoff | `delivery/src/adaptive_delivery/m8_boundary.py` | Reparses M8; `SOURCE_STATUS=blocked_pending_durable_m8_lookup`; durable acceptance/currentness stay false. |
| M9 gate | `m8_gate_reasons` | Fail-closed on expiry, halt, demotion, `accepted_task_count < 30`, audit mismatch, ineligible recommendation. |
| M9 runtime | `DryRunController` + `FakeEnvironmentAdapter` | Exact sealed in-memory adapter only; `production is unreachable`. |
| Persistence | factory PostgreSQL `001`–`018`, L5 SQLite | **No M8 factual table.** M8/M9 original packages forbade store/API/migration work. |

Roadmap gap (`DARK_FACTORY_ROADMAP.md` §7.1 / table): earned auto-merge “deliberately inactive and capped at L2”; requires an exact-profile 30-real-task cohort **plus explicit activation**. M9 still lacks real signed input, operational env/provider, exercised recovery, and production authority.

PROJECT_STATE on **origin/main** still describes 2.0.15 as an unpublished candidate and `v2.0.14` as latest published. PR #28 (`docs/v2.0.15-published-handoff` `ef7c8fa`) is the docs-only publication sync. Neither tree contains a factual ledger.

## 3. What D5 must not do

Preserve, do not reopen:

- L2 authority ceiling and one-level recommendation.
- Deterministic L0 halt/demotion.
- Exact-profile identity = `AutonomyTupleV1` digest (class + every profile digest). Any mutation is a **new empty cohort**, never a mixed count.
- No auto-merge, no L3/L4.
- M9 sealed/unavailable default; only `FakeEnvironmentAdapter`.
- No GitHub Actions, no root packaging, no human keys, no deployed Trust CI policy/holdout/images/Postgres/App edits.
- No M7 producer mutation: do **not** relax `ShadowCohortV1` or `M7AutonomyBridgeV1` to empty just to represent “no factual tasks.” Empty is an M8 ledger state, not a fake empty shadow cohort.
- Do not convert synthetic 30-task fixtures into factual records.
- Do not stack on PR #12 (`fix/human-approval-cli`) or implement from this 2.0.12 worktree.

## 4. Smallest coherent vertical

Additive factory/delivery **library** on `origin/main`. No HTTP, no factory CLI command that activates, no PostgreSQL `019`, no VERSION/ZIP/tag.

```text
AutonomyTupleV1.digest
        │
        ▼
FactualCohortLedgerV1  ── empty by default, count=0
        │ append only if durable M7 acceptance+currentness exist (they do not)
        ▼
evaluate_activation(...)  ── False until real evidence
        │
        ▼
evaluate_m9_operational_qualification(...)  ── False until signed input + env + recovery + production authority
```

Keep `evaluate_autonomy` / `CohortEvidenceV1` / `m8_gate_reasons` / `DryRunController` as the **algorithm** layer. Synthetic tests continue to prove those algorithms. D5 adds a **factual/operational** layer that refuses to treat algorithm fixtures as evidence.

### 4.1 Persist and count when none exist

**Empty is the only honest current state.** There are no human-accepted factory tasks on `main`. Fabricating 30 is forbidden.

Introduce an M8-owned ledger, not a closed `CohortEvidenceV1` with `minItems: 0`:

- `CohortEvidenceV1` stays a **closed evaluation window** over actual M7 bundles (`1..10000`). Empty cannot be that type without mutating M7.
- `FactualCohortLedgerV1` is the **open or empty factual accumulator** keyed by `autonomy_tuple.digest`.

Proposed closed shape (v1):

```text
schema_version = 1
autonomy_tuple: AutonomyTupleV1
records: tuple[FactualAcceptedTaskV1, ...]   # 0..10000, sorted unique task_id
opened_at: aware UTC datetime
evidence_kind: "factual"                     # const
synthetic: false                             # const False
```

`FactualAcceptedTaskV1` is digest/id/timestamp/metric-only (same privacy bound as `CohortTaskEvidenceV1`): tuple digest, task_id, run_id, exact_head_sha, observed_at, m7_bundle_digest, m7_outcome_digest, human_acceptance_receipt_digest, attestation_receipt_digest, audit flags, quality/cost/latency, failure counters. No prompts, traces, secrets, or “eligible: true” booleans.

**Count rule**

```text
count(tuple) =
  0  if ledger missing
  0  if ledger exists and records == ()
  N  = number of records whose linked M7 outcome.human_decision == "merged_accepted"
       AND receipt digests match
       AND record.tuple_digest == ledger.autonomy_tuple.digest
```

Unknown, corrupt, synthetic, or tuple-mismatched input is **not counted**. It is a contract error or a zero contribution, never a substitute for 30.

**Persistence**

- stdlib SQLite (or equivalently an append-only JSON file) **local to the operator/test tempdir**.
- Pattern: L5 `landing_sqlite_store.py` isolation (STRICT tables, WAL, fail-closed recovery) **without** joining L5 jobs or factory Postgres.
- Default: no committed database, no seed rows, gitignored path. First read of a known tuple returns an empty ledger object; it does not insert 30 placeholders.
- Partition key = `autonomy_tuple.digest`. Loading a mutated tuple opens a **new** empty ledger. Never copy records across digests.
- Do **not** add factory SQL `019`. M8/M9 were explicitly source-only on migrations `001`–`018`.

**Append is fail-closed today**

`append_factual_acceptance(...)` must reject, in deterministic order:

1. `synthetic_forbidden` — fixture marker, `SYNTHETIC_ALGORITHM_FIXTURES_ONLY` payloads, or any record not `evidence_kind=factual`.
2. `tuple_mismatch` — record digest ≠ ledger tuple digest.
3. `human_acceptance_missing` — outcome is not `merged_accepted` or receipt digest mismatch.
4. `m7_bundle_blocked` — bundle status `blocked_pending_durable_lookup`.
5. `m7_acceptance_missing` — `external_acceptance_available` is false (hard false on main).
6. `m7_currentness_missing` — `currentness_available` is false (hard false on main).
7. identity/order/replay/window errors already used by M8.

Therefore the append path exists, is tested as rejecting, and **cannot store a real row on current main**. Count stays 0. That is success for D5, not a bug to paper over with fixtures.

Do not materialize `CohortEvidenceV1` from an empty ledger. Activation does not need that type when count is 0.

### 4.2 Fail-closed activation predicate

There is no activation function on main. `PromotionRecommendationV1` always requires a **separate** activation and forbids external action. D5 adds the missing predicate without adding an activate-to-true operator path.

```text
evaluate_activation(ledger, activation_record | None, evaluated_at)
  -> ActivationDecisionV1
```

`ActivationDecisionV1` (new, closed):

- `tuple_digest`, `ledger_digest`, `accepted_task_count`
- `current_level` (existing profile or `L0` if none)
- `activated: bool`
- `reason_codes: sorted unique tuple`
- `separate_activation_required: true` (const)
- `external_action_authorized: false` (const)
- `auto_merge_authorized: false` (const)
- `authority_ceiling: "L2"` (const)

`activated` is true **only if every** condition holds. Missing/unknown = false.

| # | Condition | Current fact |
| --- | --- | --- |
| 1 | Ledger `synthetic is False` and `evidence_kind=factual` | Empty ledger can satisfy this |
| 2 | Tuple digest matches activation request (if any) | N/A |
| 3 | `accepted_task_count >= 30` and equals `len(records)` of merged_accepted factual rows | **0** |
| 4 | Durable M7 acceptance available | **False** |
| 5 | Durable currentness available | **False** |
| 6 | No blocked bundles | No bundles |
| 7 | Audit/quality/security/authz/dup/cost/latency/demotion gates (same order as `_cohort_gate_reason`) | Vacuous fail on empty via insufficient acceptances |
| 8 | Not halted, not expired | No live profile |
| 9 | Recommendation, if supplied, is `qualified` or `already_at_ceiling` at L2 — and is **not** a substitute for (10) | Recommendations stay non-activating |
| 10 | Explicit `ActivationRecordV1` present: human-signed/scoped, names this exact tuple digest, does not request auto-merge or L3+ | **Absent** |
| 11 | Record does not authorize Git merge, production, or external commands | N/A |

Expected reasons on empty main: `empty_cohort`, `insufficient_acceptances`, `m7_acceptance_missing`, `m7_currentness_missing`, `activation_record_missing` (sorted unique).

Do **not** add a unit test that asserts `activated is True`. There is no real evidence. Tests that build a synthetic 30-task `CohortEvidenceV1` must still yield `activated is False` because of `synthetic_forbidden` plus missing durable acceptance/currentness/activation record.

An activation record type may exist as a closed schema whose only legal `auto_merge_authorized` is `false` and whose only legal ceiling is `L2`. Parsing a record does not activate.

### 4.3 M9 qualification predicate (stays false)

Keep dry-run algorithms. Do not require operational qualification inside `DryRunController` (that would break synthetic delivery tests and would look like a hidden adapter).

Add:

```text
evaluate_m9_operational_qualification(view) -> M9QualificationDecisionV1
```

`qualified` is true only if **all** four evidence classes are real. Each missing class is a closed reason. Current main fails all four.

| Evidence | Real means | Unavailable means on `fd51dcf` | Reason code |
| --- | --- | --- | --- |
| Signed input | Artifact + authority envelope verified against the **deployed** Trust CI public store for a real merged SHA; not a fixture digest | `SignedArtifactRefV1` exists as metadata shape only; no operational verifier/store binding in `delivery/` | `signed_input_unavailable` |
| Environment | Adapter type is **not** `FakeEnvironmentAdapter`; provider/host exists and is authorized `nonproduction_staged_delivery` or better | Controller rejects any other adapter class (`only the exact bounded in-memory fake adapter is accepted`) | `environment_unavailable` |
| Recovery | At least one **exercised** recovery against that environment with immutable evidence (halt/decrease/restore actually applied outside process memory) | `recovery.py` selects least-authority actions for in-memory dry-run only | `recovery_unexercised` |
| Production authority | Separate human production grant; scope ≠ `nonproduction_staged_delivery`; production still human-gated | `authority_scope` const `nonproduction_staged_delivery`; evaluator forces `production_requires_human`; production apply is structurally unreachable | `production_authority_absent` |

Also require `evaluate_activation(...).activated is True`. Today that adds `m8_not_activated`.

`M9DeliveryHandoffV1.durable_acceptance_available` / `durable_currentness_available` stay `False`. `SOURCE_STATUS` stays blocked. Do not add a network adapter, subprocess, credential, or production environment class.

Synthetic M9 tests remain algorithm proofs. Operational qualification tests assert `qualified is False` for: empty ledger, synthetic 30-task handoff, fake adapter, dry-run recovery chain, missing production grant.

## 5. Files likely to change

Implementer works from a **new branch off `origin/main` `fd51dcf`**, not this worktree and not PR #12/#28.

**Add**

| Path | Why |
| --- | --- |
| `factory/src/adaptive_factory/factual_cohort.py` | Ledger, append guards, `count_factual_acceptances`, `evaluate_activation` |
| `factory/src/adaptive_factory/factual_cohort_store.py` | Empty-default local SQLite/JSON; no seed |
| `factory/contracts/jsonschema/factual-cohort.v1.schema.json` | Closed v1 ledger/record/activation shapes |
| `factory/tests/test_factual_cohort.py` | Empty valid; count 0; synthetic rejected; tuple mutation starts new empty cohort |
| `factory/tests/test_factual_cohort_store.py` | Missing DB = 0; no fixture rows |
| `factory/tests/test_activation.py` | Fail-closed matrix; never `activated=True` |
| `delivery/src/adaptive_delivery/qualification.py` | Four-class M9 predicate |
| `delivery/tests/test_qualification.py` | Always false on current evidence |

**Touch (minimal)**

| Path | Why |
| --- | --- |
| `factory/contracts/jsonschema/earned-autonomy.v1.schema.json` | Only if activation decision is added as an M8 `$defs` member; prefer the new factual schema to keep evaluation shapes unchanged |
| `factory/tests/test_autonomy_schema.py` | Inventory currently equals `{earned-autonomy.v1, m7-autonomy-bridge.v1}`. A new `urn:adaptive-factory:m8:*` schema must be listed. Do not weaken closed-object rules. |
| `factory/tests/test_autonomy.py` | One assertion: synthetic 30-task evaluation still does not activate and is still labeled non-factual |
| `factory/.gitignore` | Ignore local ledger DB if a default relative path exists |

**Do not change in this slice**

- `factory/src/adaptive_factory/resources/001_*.sql`–`018_*.sql`, `store.py`, `api.py`, `cli.py`
- `m7_autonomy_bridge.py` flags, `ShadowCohortV1` non-empty outcomes
- `demote_profile` / L2 ceiling / `FakeEnvironmentAdapter` / `DryRunController` adapter lock
- `trust-ci/**`, `.github/**`, packages/ZIP/VERSION
- PR #28 docs tree as the D5 vehicle
- Human keys, `.env`, deployed policy/holdout

**Docs (only after behavior exists on the D5 product PR)**

See §8. Not in the first compile if tests are red; not on PR #28.

## 6. Tests

P0 (must fail before implementation, then pass):

1. Missing store / empty ledger → `count == 0`; constructing the ledger does not insert tasks.
2. `evaluate_activation(empty, None, now).activated is False` and includes `empty_cohort` + `insufficient_acceptances` + missing M7 durable flags + `activation_record_missing`.
3. `valid_cohort_payload(30)` / synthetic M8 handoff **cannot** enter the factual ledger (`synthetic_forbidden`).
4. Mutating any tuple field (validator, model, prompt, policy, runner, holdout, change_class, …) yields a **new** digest and a **new empty** count; old records are not visible.
5. Append without durable acceptance/currentness raises/rejects; store remains empty.
6. Activation request with `auto_merge_authorized=true` or level `L3`/`L4` is a contract error; ceiling stays L2.
7. `evaluate_m9_operational_qualification` on sealed fake dry-run is `qualified is False` with `m8_not_activated`, `signed_input_unavailable`, `environment_unavailable`, `recovery_unexercised`, `production_authority_absent` (subset as designed; all four env classes covered).
8. Existing `factory/tests/test_autonomy.py` and `delivery/tests/test_m8_boundary.py` / controller tests stay green: synthetic 30 still evaluates algorithms; demotion still L0; production still unreachable.
9. Schema inventory/parity updated; no `additionalProperties` hole.

P1:

- Corrupt/truncated ledger file → fail-closed count error, not silent 30.
- Concurrent append attempts (if SQLite) serialize; replay of same `task_id` rejected.
- `evaluate_autonomy` on synthetic 30 still returns `separate_activation_required=True` and `m7_acceptance_missing` when existing_profile is None (already true via hardcoded flags).

Do not add a test named like `test_thirty_factual_tasks_qualify`. That would require fabricated evidence.

Focused commands after implementation (write owner): factory/delivery unit tests for the new modules, then `python3 scripts/grok_verify.py --mode pr` on the D5 branch.

## 7. Rollout and rollback

**Rollout**

1. Branch from `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`.
2. Characterization tests first (empty count, activation false, M9 unqualified, synthetic ≠ factual).
3. Implement ledger + two predicates.
4. Local verify + route reviews (`code_reviewer`, `test_reviewer`).
5. Open a **new** PR to `main`. Wait for App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the exact head SHA.
6. Do not merge, tag, release, deploy, or set any activation flag. Agents have no delegated grant in this package.

No feature flag is required if `activated` and `qualified` are computed fail-closed. There is no runtime daemon to restart.

**Rollback**

Revert the PR. There is no migration, no production env, no committed cohort rows. Any operator-local SQLite created during tests is disposable. Algorithm M8/M9 on `main` remains the pre-D5 sealed source.

**Forward recovery**

If a later slice gains real M7 durable lookup, append starts working one factual row at a time. Until count ≥ 30 **and** an explicit activation record exists, predicates stay false. Tuple mutation still discards eligibility.

## 8. PROJECT_STATE / START_HERE / README / PR #28

**Update those documents only after the behavior exists on the D5 product tree.** Do not pre-claim an empty ledger or new predicates in docs.

| Surface | Use in this slice |
| --- | --- |
| `origin/main` START_HERE / README / PROJECT_STATE | Still mix unpublished-2.0.15 wording with M8 “factual 30-task cohort absent.” Leave them alone until D5 code lands, then add **one truthful sentence**: ledger exists, count=0, activation=false, M9 unqualified. Do not say the 30-task cohort is collected. |
| PR #28 `docs/v2.0.15-published-handoff` | Docs-only publication identity sync (tag `v2.0.15` = `fd51dcf`). App check already SUCCESS on `ef7c8fa`. **Do not load D5 behavior into #28.** Mixing would either lie (behavior not in that tree) or stall a docs-only merge. Humans merge #28 separately. |
| `DARK_FACTORY_ROADMAP.md` gap table | After D5 code: change “factual cohort absent” to “empty factual ledger; count 0; activation false.” Do **not** check M8/M9 exit criteria. |
| VERSION / packages / CHANGELOG release entry | No. This is not a product identity bump. |

`tests/test_project_state.py` on main pins M8/M9 checkpoint SHAs and `operational_activation: false`. After D5, extend notes/assertions only to match the new **false** predicates, not to flip activation.

## 9. Residual risk

| Risk | Mitigation |
| --- | --- |
| Synthetic 30-task tests are mistaken for the M8 cohort | Keep the existing fixture banner; ledger rejects them; activation tests assert false |
| Implementer relaxes M7 empty outcomes to “support empty cohort” | Forbidden: mutates producer authority. Empty lives only on the factual ledger |
| Implementer seeds 30 rows “so the predicate can be tested true” | Forbidden. No `activated=True` test in this slice |
| Docs PR #28 or origin/main docs updated first | Forbidden. Docs follow behavior, and not on #28 |
| Wiring qualification into `DryRunController` | Would break sealed algorithm tests or look like an adapter; keep a separate function |
| SQLite next to L5 landing store / factory Postgres | Separate file and schema; no migration `019` |
| Claiming D5 “completes M8/M9” because predicates exist | Predicates existing in the false state is progress, not activation |
| Deadline compression | Does not waive exact-SHA Trust CI, signed approvals, or the 30-task + activation rule |

## 10. Write-owner sequence

1. Leave this 2.0.12 checkout. New branch from `fd51dcf`.
2. Fill change-package requirements/architecture/test-plan from this report (empty cohort valid; no fabrication; fail-closed predicates).
3. Red tests → ledger + activation + M9 qualification → green focused tests.
4. Do not open production, do not merge, do not edit PR #12/#28.
5. After behavior exists, a **small docs hunk on the same D5 PR** may record count=0 / not activated / M9 unqualified.

D5 moves the program from “cohort absent and unrepresentable” to “cohort representable, empty, counted as zero, activation and M9 qualification explicitly false.” That is the whole slice.
