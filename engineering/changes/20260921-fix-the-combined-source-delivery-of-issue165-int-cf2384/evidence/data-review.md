# Independent data review

**PASS — no blocking data findings in the reviewed source diff.**

- Reviewer: route-selected `data_reviewer`; route `cf23849faca6`.
- Base: `5674c369c4a427d42bde2a5fb3a3e2f73c853cd0`.
- Reviewed head: `c8ed34d0731e12e65f75f568d8fb3e9f0f64b2d5`.
- Reviewed Git tree: `5f481c6555b22df363f14d5d2d96d6d03a2c624c`.
- Scope: issue 163 data path and tests within the combined 165/163/62/118 delivery; additive 022, refusal parsing, transaction behavior, immutable prefix and populated upgrades. Other selected reviewers own the diagnostic and runner implementation reviews.

This is independent source/evidence review. It does not authorize migration,
deployment or merge, and it is not a current verification receipt. The coordinator
must freeze reports and handoff, refresh the complete verification and receipts,
and obtain the exact-head external App check before delivery.

## Identity and evidence checked

I read the contract, entrypoints, active route, required workflow skills, active
package, adopted data analysis, candidate provenance and the actual base-to-head
data diff. Independent byte comparisons found all 21 SQL resources 001–021
unchanged from the delivered base. All seven issue 163 files match their frozen
manifest SHA-256 values. The 022 resource is
`3bd08d907c538ab3964727fdca91eb35565821889d1999da8fcba1278613267d`.

The complete initial integrated verifier ran at
`4bc43cb7876d92b11efb289a121dcfef0a0355ac`; the inspected diff to the reviewed head
contains only the six recorded handoff/evidence files, with no source or test
delta. I independently matched `combined-full-initial-report.json` to its
recorded SHA-256
`d797b047c16090a7b4869a30d27edc3b5a2b2a5cf6936bcfd9b82164b779d32f`.
The report records overall PASS, root 877 tests/1426 subtests, factory-unit 60,
and the complete factory suite against disposable PostgreSQL 804 tests with 2
skips, plus successful restart/reconciliation probes and source stability.
These are recorded coordinator results; I did not rerun them.

The PostgreSQL command performs actual `unittest discover` over `factory/tests`
(`run_disposable_exit.py:191`), including the inspected migration and lifecycle
classes. The verifier retains only the last 12000 characters per output stream
(`verification.py:360`); its committed PostgreSQL tail has the 804/2 terminal
result but not every individual test result or skip identity. Historical focused
evidence preserves the original deadline-fixture failure and its separate
corrected pass; those attempts are not relabeled as one successful original run.

## Concrete findings

1. **SQL behavior and capability boundaries are preserved.** I extracted the
   original 018 plan function and 022 replacement independently. Replacing the 15
   new refusal expressions with `NULL` and reversing `CREATE OR REPLACE` restores
   the original body exactly, SHA-256
   `5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32`.
   Both idempotency lookup arms are included. All predicates, clause order,
   row locks, query text, write order, escalation handling and exception scope
   therefore remain unchanged. The 14 emitted reasons match the closed Python
   vocabulary. The function retains its signature, return type,
   `SECURITY DEFINER`, fixed `pg_catalog,factory` search path, PUBLIC revocation
   and coordinator-only grant. No table, index, backfill, data rewrite or changed
   query-plan requirement is introduced by 022.

2. **Refusals remain separate from successful lifecycle results.**
   `semantic_repair.py:108` accepts only the exact one-key plan-refusal envelope.
   Unknown or invalid values become the fixed `planning_rejected` value without
   echoing stored text. Mixed envelopes and the child-refusal channel remain
   corruption. `store.py:683` exits the cursor, transaction and connection before
   parsing/classification; SQL/JSON NULL gets a bounded legacy refusal and
   malformed JSON remains stored-result corruption. Existing success parsing and
   all request, child and escalation binding checks remain intact. The public
   API's fixed 409 `store_conflict` response is unchanged (`api.py:384`).

3. **Commit, rollback, deadline and replay semantics are retained.**
   Source assertions at `test_postgres_integration.py:5797` and `:5826`
   distinguish the SQL exception arm, which rolls back its earlier directive
   insert, from a normal child-conflict return, which preserves the directive.
   The offline test at `test_semantic_repair_lifecycle.py:616` also checks normal
   context exits before the Python error. Deadline exhaustion remains a
   persisted `needs_human` result, not a plan refusal. The real-server case at
   `test_postgres_integration.py:6003` checks matching success replay after expiry,
   unchanged stored response/timestamp, and new deadline escalation persistence
   and replay. Both second-lookup outcomes observe a real subject lock wait
   before committing the first command, then check the unchanged committed row
   (`test_postgres_integration.py:5911`).

4. **Both populated upgrade proofs survive integration.**
   `test_execution_persistence_postgres.py:1903` builds the actual prior SQL
   prefix with real name/hash ledger entries and nonempty execution, semantic
   success and escalation records. The current case applies 021→022; the
   explicit historical case at `:2034` supplies actual 001–021 resources to the
   real migrator and preserves 020→021. Before/after comparisons retain complete
   sampled rows from 16 tables, every old ledger timestamp, both functions'
   OIDs, owners, sorted ACLs, security/search-path configuration and effective
   coordinator/validator/adjudicator/runtime permissions. Only the selected
   function definition changes. Reapplication returns no migrations and leaves
   the snapshot equal. Replacing the former one-row fixture assertion with
   nonempty rows accommodates the richer fixture; full row equality remains.

5. **Failure and contention recovery remain bounded.**
   The existing real-ledger drift test requires no mutation before correction
   and retry. Advisory contention observes the actual migrator lock, separately
   checks release-to-success and timeout-to-rollback/retry, and scopes watchdog
   cleanup to its unique worker identity. The migrator retains 5-second lock and
   statement bounds (`migrations.py:200`); no production timeout is widened.
   This is a bounded function replacement with no volume-dependent backfill.

## Limits and later operational requirements

The tests do not universally exercise every guarded branch.
`execution_material_missing` is prevented by the chosen fixture's referential
bindings; invalid baseline risk and NULL manifest deadlines are rejected by its
typed producers. Their preservation is supported by exact whole-body/site
comparison, not a claim of runtime branch coverage or universal unreachability
under arbitrary owner-corrupted storage. The recorded skips remain skips.

No production-volume, deployment-duration or live readiness claim follows from
disposable PostgreSQL results. `store.py:1325` requires exact package/database
migration-version agreement: accepting legacy NULL does not make a mixed 021/022
rollout readiness-compatible. A later authorized operation needs coordinated
drain/package/database rollout, immutable prefix/hash validation, bounded
timeout/drift stop conditions and readiness/replay readback. After 022 is applied,
recovery requires a separately reviewed additive forward migration and a
compatible package; removing 022, rewriting its ledger or reverting source alone
does not provide recovery.

Work performed here was read-only Git/text/JSON inspection, static SHA-256/body
comparisons and status inspection, plus this report. No tests, lint, compilation,
Docker, database operations, receipts, source/shared-state edits, commits,
external writes, keys or additional agents were used. The coordinator handoff
fact is to preserve both prefix proofs and post-transaction refusal
classification while completing final evidence and external delivery gates.
