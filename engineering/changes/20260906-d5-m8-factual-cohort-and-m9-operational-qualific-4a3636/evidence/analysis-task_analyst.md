# Analysis — task_analyst

Change: `20260906-d5-m8-factual-cohort-and-m9-operational-qualific-4a3636`  
Route: `4a3636699111` · intent=`feature` · risk=`low` · complexity=`standard` · domains=`generic`  
Write owner: `general_implementer`  
Analysis wave: `repo_explorer` / `task_analyst` / `architect` / `docs_researcher`  
Reviews after implementation: `code_reviewer` + `test_reviewer`  
Evidence kinds: `verification`, `code_review`, `test_review`  
Human gates on this route: **none**  
Skills loaded: `/adaptive-delivery`, `feature-workflow` (analysis only)

Narrow question: convert user-chosen **D5 (continue M8 cohort / M9 ops)** into a bounded outcome this route **can** ship as repository product. Smallest coherent vertical. Testable AC. Explicit non-goals (no fake cohort, no auto-merge, no production deploy, no merge of PRs, no live pilot). What remains human-blocked.

Read-only except this evidence report. No application-code edits. No `.env`. No push / tag / merge / deploy from this agent.

Companion fact report: `evidence/analysis-repo_explorer.md` (same change). This note converts those facts into scope and AC.

---

## Ruling (one screen)

D5 as written — “factual 30-task exact-profile cohort, durable currentness, M8 activation, signed M9 input, operational environment/provider, exercised recovery, human production authority” — **cannot be completed by this route**. Completing it would require fabricating human-accepted tasks, flipping hardcoded unavailable lookups, or claiming production. All three are forbidden.

**This route’s D5** is therefore **not** “finish M8/M9 ops”. It is:

> Ship fail-closed **cohort/activation accounting** and **M9 operational-qualification checks** on published `origin/main` `fd51dcf`, so the product can *report* that D5 is incomplete and *refuse* to claim qualified / activated / operational / auto-merge / production without evidence.

After this slice, D5 remains **incomplete by design**. The honest close statement is: *accounting exists; ops do not*.

| Layer | Meaning |
| --- | --- |
| Published identity | `v2.0.15` on `fd51dcf`. Do not retag, rebuild ZIP, or bump `VERSION`. |
| Current checkout | `fix/path-aware-shell-policy-circuit-breaker` @ `7c61e3b` is **2.0.12**. Implementing here ships the wrong tree. |
| M8/M9 source | Already on `main` via PR #22 / `v2.0.13`. Evaluation exists, L2-capped, inactive. |
| Factual cohort | **0** records. Synthetic 30-row fixtures are algorithm tests only. |
| M9 | Sealed in-memory adapter only. Production is unreachable in code. |
| Deadline `2026-09-08` | `superseded_unachievable_historical_target`; `gate_waiver: false`. Compress scope; do not skip gates. |
| Route honesty | generic / low / `general_implementer` / no `security_reviewer` / `human_gates=[]`. Cannot authorize production, auto-merge, or 30 human-accepted tasks. |
| Do not pick | PR #12 (separate unique CLI successor), PR #13, PR #15, PR #28 as git parent, stale path-aware branch. |

Route `human_gates: []` means the implementer may proceed after this bounded design. It does **not** authorize merge, activation, production, or human approval keys.

---

## Verified facts (against origin/main and published handoff, not this 2.0.12 checkout)

Checked 2026-09-06 from git objects. Do not treat the dirty local tree as product.

| Item | Verified value | Source |
| --- | --- | --- |
| `origin/main` | `fd51dcfed6b33f4a8707c0db602328146df17cc9` — `feat(pilot): bounded Codex issue-to-draft-PR capability (2.0.15 candidate) (#27)` | git |
| `origin/main` `VERSION` | `2.0.15` | `origin/main:VERSION` |
| Published handoff | `origin/docs/v2.0.15-published-handoff` `ef7c8faeb5d339c5b4343de61162ea611c130c4d` | git |
| Handoff `observed_main_sha` | `fd51dcfed6b33f4a8707c0db602328146df17cc9` | `PROJECT_STATE.json` |
| Latest published release | `v2.0.15` (handoff). `origin/main:PROJECT_STATE.json` still lists `v2.0.14` as latest and is **stale relative to the handoff**. Prefer the handoff ledger for currentness. | both `PROJECT_STATE.json` |
| Local HEAD | `7c61e3b` on `fix/path-aware-shell-policy-circuit-breaker`, VERSION `2.0.12` | git status |
| M1–M9 source on main | PR #22 checked head `b5eba759c309a92f92f4d4003d025795c7f8a1f9`, merge `8599d45f4f28285381b05a53feb3059de92eb2a8`, release `v2.0.13` | ROADMAP §3.3, PROJECT_STATE |
| M8 checkpoint | `a937ac8d200a4e143c295fabd482b19bc8cc4286` | PROJECT_STATE `milestones.M8` / `integrated_stack.m8_head` |
| M9 source checkpoint | `64b10689ce78a0464a494440f3fa981e18789687` | PROJECT_STATE `milestones.M9` |
| M8 implementation notes | Evaluation delivered; **factual 30-task cohort, durable currentness, and activation remain absent**; L2 cap; L0 demotion mandatory | ROADMAP M8 current status; PROJECT_STATE M8 notes |
| M9 implementation notes | Sealed in-memory adapter; **real signed input, operational environment/provider, exercised recovery, production authority remain absent** | ROADMAP M9 current status; PROJECT_STATE M9 notes |
| M8 calendar | `status: indeterminate`, `minimum_human_accepted_tasks: 30` | PROJECT_STATE `active_delivery.schedule.m8_calendar` |
| M9 entry requires | `accepted_m8`, `signed_artifact`, `environment_evidence`, `recovery_evidence` | PROJECT_STATE `schedule.m9_entry_requires` |
| Deadline | `2026-09-08T00:00:00+03:00`, `superseded_unachievable_historical_target`, **`gate_waiver: false`** | PROJECT_STATE `schedule.superseded_target`; `decisions.md` 2026-08-31 |
| Factual cohort records on main | **0**. `"minimum_human_acceptances"` appears in schema, `autonomy.py`, and synthetic tests only | repo_explorer count |
| `M7AutonomyBridgeV1.external_acceptance_available` | hardcoded `False` | `factory/src/adaptive_factory/m7_autonomy_bridge.py` |
| `M7AutonomyBridgeV1.currentness_available` | hardcoded `False` | same |
| `PromotionRecommendationV1` | `separate_activation_required` must be `True`; `external_action_authorized` must be `False` | `autonomy.py` |
| Synthetic 30-row eval | `accepted_task_count==30` still yields `reason_code=="m7_bundle_blocked"`, levels stay L0, `external_action_authorized==False` | `test_closed_m7_bundle_blocks_forged_thirty_row_qualification` |
| M9 adapter | `FakeEnvironmentAdapter`; only `preview` / `staging` / `bounded_canary`; production raises `production is unreachable` / `production recovery is unreachable` | `fake_environment.py`, `controller.py`, `recovery.py` |
| M8 handoff | `SOURCE_STATUS = blocked_pending_durable_m8_lookup`; durable flags False; producer pin `PROVISIONAL_M8_PRODUCER_SHA = f53275d5…` (historical, not `fd51dcf`) | `delivery/src/adaptive_delivery/m8_boundary.py` |
| Factory CLI | Control-plane UDS commands only. **No autonomy / cohort / qualification command.** | `factory/src/adaptive_factory/cli.py` |
| Delivery package | Library only. No CLI script. | `delivery/pyproject.toml` |
| Autonomy SQL | **None.** Factory migrations 001–018 have no M8 cohort/activation tables. | `factory/src/adaptive_factory/resources/` |
| Qualification module | **Absent** on `origin/main`. | `git ls-tree` |
| PR #12 | OPEN, unique lazy CLI imports; **do not pick for this change** | runbook `20260905-open-pr-reconciliation.md` |
| Pilot | Pre-pilot. Landing profile stale (`6990103` vs observed `80d6215`). No live model turn. | PROJECT_STATE `pilot_delivery` |
| Route | `4a3636699111`, `write_agent=general_implementer`, `required_evidence=verification+code_review+test_review`, `human_gates=[]` | `route.json` / `active-route.json` |

M8/M9 **algorithms are already the product**. D5’s missing pieces are **evidence and authority**, not another restack of `evaluate_autonomy` / `evaluate_delivery`.

---

## What D5 is not (this route)

1. **Not a 30-task factory.** There are no 30 human-accepted exact-profile tasks to ingest. Writing 30 JSON fixtures, cloning `valid_cohort_payload()`, or labeling test rows `merged_accepted` is fabrication.
2. **Not activation.** `evaluate_autonomy` always emits `separate_activation_required=True` and `external_action_authorized=False`. There is no activation store. Flipping those constants is a contract violation (`external_action_forbidden` / `separate_activation_required`).
3. **Not durable currentness.** The M7 bridge properties are hardcoded `False`. Making them `True` without a signed durable lookup forges authority the dataclass was designed to refuse.
4. **Not M9 ops.** The only adapter is sealed in-memory. Adding a network/provider adapter, signed live input, or production stage is out of this generic/low route and out of M9’s own original AC (“No operational adapter, I/O, persistence, … is present”).
5. **Not auto-merge.** Ceiling is L2: “automated reviewers recommend; human merges every PR”. L3/L4 are unrepresentable (`unsupported_level` on ceiling other than L2).
6. **Not merge/deploy/pilot.** No delegated grant names those operations. PR #12/#28 stay untouched. Landing-profile refresh is a different change.
7. **Not a deadline waiver.** `gate_waiver: false`. The allowed response is a smaller honest slice.

If a later route ever *does* hold 30 real tasks plus signed activation plus an operational adapter, that is a **new** high-risk / security-sensitive change with human gates. It is not this PR.

---

## Outcome (observable, this route)

An operator or subsequent agent, working from a reviewed `origin/main`-based checkout, can evaluate **M8 cohort/activation accounting** and **M9 operational qualification** against candidate records (including the empty set and the existing synthetic fixtures) and receive a **closed, fail-closed status** that:

- reports `factual_accepted_task_count = 0` for the published tree and for any synthetic/test payload;
- reports durable M7 acceptance/currentness as unavailable;
- reports M8 activation as absent and `external_action_authorized = false`;
- reports M9 as `non_operational` with explicit blockers (no signed real input, sealed in-memory adapter only, no exercised operational recovery, no human production authority);
- **refuses** to emit `qualified` / `activated` / `operational` / `auto_merge_authorized` / `production_ready` for those inputs;
- treats calendar deadline `2026-09-08` as non-waiving history.

Observable user result: D5 becomes a **queryable product status** instead of a narrative claim. The program does not become autonomous or operational.

---

## Smallest coherent vertical

One library vertical on **`fd51dcf`**, not a new service, not PostgreSQL, not a provider.

**Name it qualification accounting, not cohort collection.**

1. **Leave the stale 2.0.12 checkout.** New branch / worktree from `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`. Recreate this change package there. Do not parent on PR #28 or PR #12.
2. **Characterization first (existing origin/main behavior, keep green):**
   - empty candidate set is not a cohort;
   - synthetic 30-row `valid_cohort_payload()` evaluates to `m7_bundle_blocked` / not activated;
   - `FakeEnvironmentAdapter` cannot represent `production`;
   - recommendation flags cannot be set to authorize external action.
3. **Add fail-closed accounting types + pure evaluators** that *wrap* existing M8/M9 records; do not reimplement `evaluate_autonomy` / `evaluate_delivery` / `choose_recovery`.
4. **Add tests** that prove synthetic, empty, mutated, and “caller claims activated” inputs fail closed, and that the empty published tree reports the documented blockers.
5. **Optional thin stdlib reporter** (function and/or `python -m` in `delivery` or `factory`) that prints the closed JSON status. Do **not** bolt this onto the factory UDS CLI (`adaptive-factory` requires `--token-file` and talks to a live control socket).
6. Local `python3 scripts/grok_verify.py --mode pr`, then independent `code_reviewer` + `test_reviewer`. Open a **new** PR to `main`. Stop.

Recommended split (architect may refine names; do not add a database):

| Surface | Owner package | Job |
| --- | --- | --- |
| M8 account | `factory` next to `autonomy.py` | Classify candidate cohort/activation evidence; count only factual rows; emit blockers; never authorize |
| M9 qualification | `delivery` next to `m8_boundary.py` | Inspect adapter kind, signed-input presence, recovery evidence class, production authority; compose M8 account |
| Tests | `factory/tests` + `delivery/tests` | Empty / synthetic / forged-activation / production-claim / deadline-non-waiver |

Keep existing `evaluate_autonomy` fail-closed path unchanged. Accounting **must not** become a backdoor that returns `qualified` when `evaluate_autonomy` returns `m7_bundle_blocked` / `m7_currentness_missing`.

---

## In scope

- New isolated branch from `origin/main` `fd51dcf`.
- Closed qualification/account records (v1) with exact integer counts, boolean evidence flags, reason-code blockers, and digest of the evaluated input set.
- Fail-closed classification of candidate records:
  - `synthetic` — test fixtures, `SYNTHETIC_ALGORITHM_FIXTURES_ONLY`, repository ids such as `synthetic/repository` / fixture `owner/repository`, payloads from `factory/tests` or `delivery/tests/synthetic_fixtures.py`;
  - `untrusted` — missing receipts, caller-supplied eligibility/currentness/activation flags, unsigned “activation”, production claims, unknown fields;
  - `factual_candidate` — only if a record could *in principle* be real (this tree has none; the type exists so a later honest ingest can use it without rewriting the evaluator).
- Empty input and synthetic 30-row input both yield `factual_accepted_task_count = 0` (synthetics are reported separately as `synthetic_task_count` if counted at all, and **never** toward the 30-task floor).
- Explicit blockers at least:
  - M8: `insufficient_factual_acceptances`, `m7_acceptance_unavailable`, `m7_currentness_unavailable`, `m7_bundle_blocked` (when present), `activation_record_absent`, `external_action_forbidden`, `authority_capped_l2`, `auto_merge_unrepresentable`;
  - M9: `signed_input_absent`, `operational_environment_absent`, `adapter_sealed_in_memory`, `exercised_operational_recovery_absent`, `human_production_authority_absent`, `production_unreachable`, `m8_inactive`.
- Constants that cannot be True on this tree without new evidence types this route will **not** add: `durable_acceptance_available`, `durable_currentness_available`, `activation_present`, `external_action_authorized`, `auto_merge_authorized`, `operational`, `production_ready`.
- `calendar_deadline_waives_gates = false` even if evaluation time is after `2026-09-08T00:00:00+03:00`.
- Tests covering empty set, synthetic 30-row, forged activation/external-action/production flags, FakeEnvironmentAdapter, and composition (M9 cannot be operational while M8 account is inactive).
- Append-only `decisions.md` fact: D5 on this route is qualification accounting, not ops.
- This change package / evidence. Local verify + code/test reviews. Open successor PR to `main`.

---

## Out of scope / explicit non-goals

- Implementing on `fix/path-aware-shell-policy-circuit-breaker` / VERSION `2.0.12`.
- Using PR #28 as git parent or mixing docs-sync.
- Picking, merging, closing, or cherry-picking **PR #12** (lazy CLI), #13, #15, #28.
- Fabricating or checking in 30 “human-accepted” tasks, receipts, or trust-profile tuples.
- Counting synthetic fixtures toward `minimum_human_acceptances`.
- Setting `external_acceptance_available` / `currentness_available` to True, or adding a caller-supplied override field the M7 bridge currently rejects.
- An activation API that can succeed, a live profile store that raises `current_level` above L0, or auto-merge.
- Operational environment/provider adapter, network, hosting, I/O, subprocess, credentials, PostgreSQL cohort tables, migrations 019+.
- Signed real supply-chain input, production stage, or recovery against a real environment.
- Live pilot, landing-profile refresh, model turn, target-repo write.
- VERSION bump, ZIP rebuild, tag, GitHub Release, merge to `main`, deploy, production mutation.
- Reading `.env`, human approval keys, Trust CI signing keys, GitHub App keys.
- GitHub Actions.
- Restacking M8/M9 algorithms already on main (`autonomy.py`, `m8_boundary.py`, `evaluator.py`, `controller.py`, `fake_environment.py`, `recovery.py`) except as strictly required call sites.
- Updating PR #28’s `PROJECT_STATE.json` / root README current-state (docs successor stays independent). A one-line product docstring that the new status is `inactive`/`non_operational` is enough.
- Claiming D5 complete.

---

## Frozen boundaries (must not change)

- `PromotionRecommendationV1.separate_activation_required is True`
- `external_action_authorized is False` on recommendation and demotion
- Tuple `authority_ceiling == "L2"`; L3/L4 unrepresentable
- `M7AutonomyBridgeV1` availability properties remain locally False
- `FakeEnvironmentAdapter` remains the only adapter; production environments remain unrepresentable
- Factory migrations 001–018 byte-preserved
- Published `v2.0.15` tag, ZIP `1f0f64557fd258df7e533f674bb4e7c55d4a1a51454d48bcfecfa5487d08e9d7`, sidecar
- `/approvals`, Trust CI policy digest, branch protection, deployed holdout/images/Postgres
- Human private keys and server-mounted trust store
- Existing synthetic tests must stay labeled synthetic and must **keep failing closed** (do not “fix” `m7_bundle_blocked` by making fixtures look factual)

---

## Testable acceptance criteria

Close **this** change only when all of these are true on the **same** successor tree, branched from `fd51dcf`, not from `7c61e3b` or PR #12/#28.

### A. Base and delivery hygiene

- [ ] AC-A1: Successor branch contains ancestor `fd51dcfed6b33f4a8707c0db602328146df17cc9` and is **not** `fix/path-aware-shell-policy-circuit-breaker`.
- [ ] AC-A2: Product diff vs `origin/main` is limited to new qualification/account modules + their tests + optional stdlib reporter, this change package/evidence, and short `decisions.md`/`mistakes.md` appends. No `VERSION`, packages ZIP, `.github/workflows/`, factory SQL/migrations, `trust-ci/` CLI, `pilot/`, `compose.yaml`, `policy.py`/`api.py`/`worker.py`.
- [ ] AC-A3: New PR to `main`. PRs #12/#13/#15/#28 are neither merged, closed, nor used as `base`.
- [ ] AC-A4: No merge, tag, deploy, live API write, human-key use, or production adapter.

### B. M8 fail-closed accounting

- [ ] AC-B1: Given **no** candidate records, when the M8 account is evaluated, then `factual_accepted_task_count == 0`, `minimum_human_acceptances == 30`, `activation_present is False`, `durable_acceptance_available is False`, `durable_currentness_available is False`, `external_action_authorized is False`, `auto_merge_authorized is False`, `status == "inactive"`, and blockers include `insufficient_factual_acceptances` and `activation_record_absent`.
- [ ] AC-B2: Given the existing synthetic 30-row `valid_cohort_payload()` / `synthetic_m8_evidence()`, when classified and accounted, then those rows do **not** increment `factual_accepted_task_count`; `evaluate_autonomy` on that payload still returns a non-`qualified` reason (`m7_bundle_blocked` today) with `external_action_authorized is False`; account status remains `inactive`.
- [ ] AC-B3: Given a caller-supplied activation or recommendation payload with `external_action_authorized=True` or `separate_activation_required=False`, when parsed/accounted, then the contract/account **rejects** it (`external_action_forbidden` / `separate_activation_required` / untrusted), and does not mark `activation_present`.
- [ ] AC-B4: Given `authority_ceiling="L3"` or any auto-merge claim, when parsed/accounted, then it is rejected or reported `auto_merge_unrepresentable`; never `auto_merge_authorized`.
- [ ] AC-B5: Given evaluation time after `2026-09-08T00:00:00+03:00`, when accounted, then `calendar_deadline_waives_gates is False` and the same blockers remain.
- [ ] AC-B6: Given two different trust-profile tuple digests, when mixed in one account, then they are **not** summed into one 30-task cohort (exact-profile rule); mutation of any tuple component is a new empty account.

### C. M9 fail-closed operational qualification

- [ ] AC-C1: Given default `FakeEnvironmentAdapter` and no extra evidence, when qualified, then `adapter_kind` is sealed in-memory, `operational is False`, `signed_input_present is False`, `exercised_operational_recovery is False`, `human_production_authority_present is False`, `production_ready is False`, `status == "non_operational"`.
- [ ] AC-C2: Given an observation/environment named `production`, when evaluated through existing delivery/recovery or the new qualifier, then the error/reason includes production unreachable / `production_requires_human`; qualifier does not report operational success.
- [ ] AC-C3: Given a passing local `test_recovery.py`-style identity/plan result, when qualified as “exercised operational recovery”, then it is **not** accepted (`exercised_operational_recovery` stays false). Unit-test recovery ≠ operational recovery.
- [ ] AC-C4: Given M8 account `inactive`, when M9 qualification is composed, then M9 cannot report `operational` (`m8_inactive` blocker). M9 must not claim ops “around” inactive M8.
- [ ] AC-C5: Qualifier inspects adapter **type/capability**, not a caller boolean `operational=true`. A payload flag cannot mint an operational environment.

### D. Non-claims encoded in the record

- [ ] AC-D1: The closed status document/object contains an explicit `claims` or equivalent map where `m8_qualified`, `m8_activated`, `m9_operational`, `auto_merge`, `production_ready` are all `false` for empty and synthetic inputs.
- [ ] AC-D2: Status reason codes are drawn from a closed enum (no free-text success). Unknown reason → fail closed.
- [ ] AC-D3: Existing `factory/tests/test_autonomy.py` and `delivery/tests/test_m8_boundary.py` remain green and still document synthetics as non-factual.

### E. Verification and review (this route)

- [ ] AC-E1: `python3 scripts/grok_verify.py --mode pr` PASS on the successor tree.
- [ ] AC-E2: `code_reviewer` and `test_reviewer` inspect the actual diff; reports stored under this change package; `grok_review.py` receipts bind the **same** fingerprint.
- [ ] AC-E3: `VERSION` remains `2.0.15`. Published ZIP/sidecar digests unchanged.
- [ ] AC-E4: Close statement does **not** say M8 is active or M9 is operational. It says accounting/qualification checks shipped and D5 ops remain blocked.

---

## Failure and edge cases

- Implementing on 2.0.12 checkout → ships the wrong product. **Hard fail.** Leave it.
- Basing on PR #12 or #28 → mixes unique CLI/docs work with M8/M9 accounting. **Hard fail.**
- Checking in 30 synthetic tasks as `engineering/evidence/m8-cohort/*.json` and counting them → fabrication. **Hard fail.**
- “Fixing” `test_closed_m7_bundle_blocks_forged_thirty_row_qualification` so a 30-row fixture becomes `qualified` → forges currentness. **Hard fail.**
- Adding `external_acceptance_available: true` as a JSON field the bridge currently ignores/hardcodes → bypass. Reject unknown fields; keep properties False.
- PostgreSQL table for “cohorts” filled by tests → looks durable, is still synthetic. Out of scope.
- New `OperationalEnvironmentAdapter` with network → different route, not generic/low.
- Treating `human_gates: []` as activation/merge permission → forbidden.
- Treating App-owned Trust CI success on this PR as M8 activation → PROJECT_STATE already states merge eligibility ≠ autonomy.
- Deadline-driven skip of blockers → forbidden; encode non-waiver in the record.
- Reporter that prints “ready” / “qualified” when blockers is non-empty → fail the test, fail the review.

---

## What remains human-blocked (D5 leftover; not this PR)

These stay **open after a passing successor**. Do not stall accounting on them, and do not perform them.

| Blocked action | Why it stays blocked |
| --- | --- |
| Collect ≥30 **real** human-accepted tasks for one exact trust-profile tuple | No such tasks exist; humans merge every PR; this route cannot mint them |
| Durable M7 acceptance + currentness lookup | Hardcoded unavailable; needs a signed external lookup outside PR domain |
| Human-signed M8 **activation** record | Separate authority; local receipts and Trust CI merge checks do not activate |
| Raise a live profile above L0 / enable L2 recommendation as governance | No activation store; ceiling still L2 with human merge |
| Auto-merge (L3+) | Unrepresentable; never initially eligible classes include Trust CI, production, secrets |
| Real signed M9 input (supply-chain artifact + promotion authority) | Human/signing outside agent environment |
| Operational environment/provider deployment | Not in repo; Fake adapter only |
| Exercised recovery on that environment | Current recovery tests are local identity/plan only |
| Human production promotion | `production_requires_human`; no agent production authority |
| Merge this successor PR | App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on the **new** head SHA + signed scopes |
| Merge PR #28 docs handoff | Human-owned; already a separate OPEN PR |
| Close/merge PR #12 | Different unique successor; not this change |
| Live pilot model turn | Stale landing profile `80d6215`; default-unavailable |
| Tag / GitHub Release / deploy | Need exact delegated grant **and** remaining external gates |
| Waiver of 2026-09-08 | Recorded unachievable; `gate_waiver: false` |

---

## Constraints

- **Backward compatibility:** Existing M8/M9 contracts, reason codes, and tests stay valid. Accounting is additive.
- **Data/privacy:** No production dumps, no customer tasks, no secrets in fixtures. Synthetic payloads remain opaque hex.
- **Performance:** Pure in-memory evaluation; bound candidate lists (reuse M8 `MAX_COHORT_TASKS = 10_000`); no I/O in the evaluator core. A reporter may read stdin/files the caller names, not `.env`.
- **Operational:** No service restart, no image rebuild, no policy digest change. Rollback is revert of the successor commit.
- **Security:** This route selected **no** `security_reviewer`. Stay inside accounting/qualification so that remains honest. Crossing into adapters, signing, Trust CI policy, or activation success is a **stop** and re-route.
- **Observability:** Status must expose counts, booleans, blocker codes, tuple digest if present, and the four forbidden claims as false. No success metric that treats D5 as done.

---

## Recommended implementer tasks (after analysis wave)

1. New worktree/branch from `origin/main` `fd51dcf`. Copy/recreate this change package there; do not commit it from `7c61e3b`.
2. Characterization tests: empty account; synthetic 30-row still not factual; production unreachable; flags cannot authorize.
3. Implement M8 account + M9 qualifier as pure functions over existing types.
4. Compose them so M9 ops cannot be claimed while M8 is inactive.
5. Keep `evaluate_autonomy` / `FakeEnvironmentAdapter` behavior unchanged.
6. `python3 scripts/grok_verify.py --mode pr`.
7. Independent code + test reviews; bind receipts.
8. Open successor PR to `main`; state in the PR body that D5 **ops remain blocked** and this ships fail-closed accounting only. Stop.

Do **not** wait for 30 real tasks. Do **not** implement PR #12 in the same PR. Do **not** declare M8/M9 complete.

---

## Residual risks

- This change package currently exists as **untracked files on the stale 2.0.12 working tree**. It must be recreated on an `origin/main` branch; committing it from `7c61e3b` attaches the wrong parent.
- `origin/main:PROJECT_STATE.json` still says `latest_published_release: v2.0.14` and `observed_main_sha: 1751b585…`. Authoritative currentness is `origin/docs/v2.0.15-published-handoff`. Do not “fix” that ledger in this product PR (that is PR #28’s job).
- Delivery still pins M8 producer SHA `f53275d5…`, not `fd51dcf`. Accounting may *report* the pin mismatch as an informational blocker; do not silently retarget the pin in this slice unless architect proves it is required for the new types. Retargeting is a separate exact-SHA binding change.
- Runtime `active-route.json` can be overwritten by later sessions. Implementer must follow **this** package `route.json` (`4a3636699111`) and `allowed_agents`.
- A future agent may treat a green qualification-accounting PR as “D5 done”. AC-E4 and the PR body must make the opposite claim mechanically (`claims.*.false`).

---

## Decision record for the next agent

**Base:** `origin/main` `fd51dcfed6b33f4a8707c0db602328146df17cc9`.  
**Not base:** current checkout `7c61e3b`; PR #12; PR #28.  
**Ship:** fail-closed M8 cohort/activation **accounting** + M9 operational **qualification checks** that refuse to claim ops without evidence.  
**Do not ship:** 30 fake tasks, auto-merge, production adapter, activation success, live pilot, merge, deploy, tag, PR #12.  
**Done when:** successor PR is open, `grok_verify --mode pr` PASS, code_review + test_review receipts bound to that tree, and the new status reports inactive/non-operational for empty and synthetic inputs.  
**Not done when:** factual cohort, currentness, activation, signed input, operational environment, exercised recovery, or production authority appear — they should not.

D5 is **converted**, not completed.
