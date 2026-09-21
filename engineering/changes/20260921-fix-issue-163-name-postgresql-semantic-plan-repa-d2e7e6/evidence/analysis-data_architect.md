# Data architecture analysis — issue #163

Date: 2026-09-21. Selected role: `data_architect`; route `d2e7e68e7bd5`.
Inspected branch `fix/issue-163-repair-plan-rejections`, HEAD
`1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` in this isolated worktree.
This is static implementation guidance, not a review approval or migration result.
No tests, compilation, Docker, database connections, production SQL or external
writes were performed. Only this report is written by this analysis agent.

## Recommended bounded migration

The research packet `design-163-semantic-plan-rejections.md` matches the actual
source. Add `022_semantic_repair_plan_rejection_reasons.sql`; resources currently
end at 021, so 022 is available at the inspected HEAD. Reconfirm that reservation
before integrating another migration branch. Keep every byte of 001–021 intact.

The new resource should contain only a diagnostic header, an in-place function
replacement, and the existing explicit privilege boundary:

```sql
CREATE OR REPLACE FUNCTION factory.semantic_plan_repair(
  p_idempotency_key char(64),p_request_digest char(64),
  p_request_canonical text,p_task_id uuid
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,factory AS $$
-- Exact original declarations and body, with only the 15 NULL refusals replaced.
$$;

REVOKE ALL ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION factory.semantic_plan_repair(char,char,text,uuid)
  TO factory_semantic_coordinator;
```

This outline is not executable migration content: the implementer must carry over
the entire original body. Each replacement is exactly
`jsonb_build_object('repair_plan_rejection','<closed reason>')`. Do not split or
reorder guard groups, add new guards, change exception classes, or reuse the child
rejection channel. Unlike 021, 022 needs no regrouping of predicates.

The complete original function extracted from `CREATE FUNCTION` through its first
closing `\n$$;` has independently recomputed SHA-256
`5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32`.
Static counting confirms 13 `RETURN NULL` statements and two `ELSE NULL` arms.

| Original 018 line | Closed reason | Existing refusal group |
|---|---|---|
| 1576 | `command_input_invalid` | Isolation, command arguments and bounded size |
| 1621 | `repair_payload_invalid` | Command digest, closed shape and request fields |
| 1626 | `cycle_lineage_invalid` | Presence of previous proposal relative to cycle |
| 1632 | `idempotency_conflict` | First stored request digest mismatch |
| 1639 | `subject_not_found` | Task-bound semantic subject absent |
| 1645 | `verdict_mismatch` | Verdict absent or differs from recomputed verdict |
| 1660 | `execution_material_missing` | Result, packet, manifest, task or intent absent |
| 1689 | `previous_proposal_mismatch` | Prior cycle, proposal state and binding checks |
| 1724 | `child_handoff_mismatch` | Cross-subject handoff, source, head and time checks |
| 1761 | `lineage_mismatch` | Recursive chain length, baseline, head and authority |
| 1779 | `baseline_risk_invalid` | Existing risk vocabulary check |
| 1903 | `idempotency_conflict` | Second stored request digest mismatch |
| 1995 | `directive_conflict` | Existing directive identity/subject/body conflict |
| 2012 | `child_proposal_conflict` | Existing child identity/directive/body conflict |
| 2042 | `store_operation_rejected` | Existing exception handler |

There are fourteen distinct emitted reasons; only `idempotency_conflict` occurs
twice. `store_operation_rejected` is deliberately broader than a write failure:
the existing handler also catches JSON conversion and numeric/data exceptions.
Never expose `SQLERRM`, arbitrary JSON or caller-supplied text through a reason.

## Invariants that the replacement must preserve

- Keep the task-plus-subject lookup and its `FOR UPDATE`, the expected-verdict
  comparison, all repository/source/intent/head/authority bindings, recursive
  lineage traversal and successful response canonicalization exactly unchanged.
  There is no new tenant access path and no new table privilege. The coordinator
  still has function execution, while validator, adjudicator and runtime do not.
- Preserve both idempotency lookups and their ordering. A matching first lookup
  returns the stored response before checking current deadlines or current
  execution material. The second lookup closes the existing wait/concurrency
  window after the subject lock. Both matching arms remain
  `THEN v_prior.response_body`; only the mismatch arms change.
- Preserve the first-match escalation chain. An expired or NULL `v_deadline`
  remains `needs_human/deadline_exhausted`, persisted in the escalation and command
  result tables. It is not a precondition rejection. Writer/head/fence/budget
  escalations likewise remain successful lifecycle envelopes.
- Do not claim all rejected commands are write-free. A normal return at the child
  conflict guard follows the conditional directive insertion. That insertion may
  survive the normal function return under existing behavior. The Python store
  currently finishes the transaction before interpreting the returned document;
  keep that ordering. Do not introduce an accidental rollback by moving a new
  exception into the transaction block.
- Preserve the existing PL/pgSQL exception block. Its handler catches the listed
  unique/check/FK/conversion/range/data exceptions and retains its existing
  rollback semantics. Do not add `WHEN OTHERS`, catch timeout errors, or retry a
  refusal automatically.
- Preserve OID, owner, `SECURITY DEFINER`, search path and effective ACL when
  replacing the function. Repeat the existing PUBLIC revoke and coordinator
  grant without introducing another grantee. No new table, index, extension,
  trigger, role, schema or backfill is justified.

## Offline evidence required before PostgreSQL tests

1. Pin the original function hash above and the shipped migration prefix identities
   from the baseline. A comparison of two simultaneously edited functions alone
   cannot prove immutability. Existing 001–021 resources must not be modified to
   make a parity test pass.
2. Extract both complete function texts. In 022, normalize only the initial
   `CREATE OR REPLACE` to `CREATE`, and replace only the fifteen exact emitted
   plan-envelope expressions with `NULL`. Require byte-for-byte equality with
   the original extracted function. Do not reuse `_guard_lines`: it intentionally
   drops lines containing refusal expressions, which could hide a changed
   predicate on the same line.
3. Assert ordered site/reason mapping, fourteen distinct names, fifteen total
   occurrences, two idempotency occurrences, and no remaining `RETURN NULL` or
   `ELSE NULL` in the new body. Independently pin both matching CASE arms.
4. Compare the SQL set to the Python plan-specific allowlist, excluding only its
   fixed unknown-value fallback. The local legacy-NULL sentinel is not emitted by
   SQL. Require the exact one-key shape; extra keys stay malformed response data.
5. Preserve the existing 021 checks. Extend contiguous resource expectations from
   versions 1–21 to 1–22 and assert that planning from a real 001–021 prefix yields
   only 022, while a complete matching ledger yields no pending migration.
6. Assert the unchanged signature/security/search path and restricted grant. Scan
   statements outside the function body for forbidden schema/data rewrites;
   legitimate INSERT statements inside the unchanged function are not migration
   backfill operations.

The parser/store tests should prove a named refusal does not enter
`RepairLifecycleResult.from_dict`, unknown/non-string reason values map to the
fixed local fallback, legacy SQL/JSON NULL has its own refusal, and malformed
JSON/extra-key/scalar results remain corruption with bounded messages. Existing
success binding checks remain in force.

## PostgreSQL evidence and current-prefix integration

Use disposable databases and the existing semantic fixture after the coordinator
releases the shared CPU/Docker lane. Run the function with the semantic coordinator
capability, not a superuser-only happy path.

- Exercise valid success and matching replay, early invalid argument/payload/
  cycle refusals, missing subject, mismatched verdict, reachable previous proposal
  and lineage failures, and directive/child conflict paths. Invalid canonical JSON
  can exercise the unchanged exception arm. Where constraints make an internal
  state unreachable, document that limit and use the frozen-body proof instead of
  disabling production constraints or triggers.
- Cover both idempotency lookups. For the second, use two connections: hold the
  subject row in connection A; let B pass its absent-key lookup and visibly block
  on the subject; let A create and commit the matching or conflicting command
  result before releasing the lock. Observe blocking state and use explicit
  bounded watchdogs. Arbitrary sleeps do not prove B reached the intended lookup.
- Test deadline escalation and replay with server-clock fixtures and independently
  fresh authority. Ensure earlier escalation predicates do not mask deadline
  exhaustion. An already recorded repair result must still replay after expiry.
  Do not widen production timeouts to make these tests pass.
- Verify persistence as well as the returned envelope: unchanged stored success
  bytes, persisted escalation, no unexpected command-result row for an ordinary
  refusal, and the existing partial-directive/exception-rollback distinction where
  reachable. Do not assume normal RETURN and caught exception have equal effects.
- Existing integration assertions at `test_postgres_integration.py:6061`, `:6104`
  and `:6352` expect the old generic `repair result` corruption message. Preserve
  those scenarios and change their expected result to the specific new reason;
  do not delete them or broaden every assertion to any `StoreError`.

The retained #166 branch provides real prefix/migration contention machinery in
`factory/tests/test_execution_persistence_postgres.py:1849` onward. Its current
snapshot is hardcoded to `semantic_bind_repair_child(character,text)`, and its
populated-row inventory contains six execution tables, not semantic lifecycle
rows. On an integrated tree with 022:

- Apply actual 001–021 SQL with corresponding real ledger hashes/timestamps; run
  `PostgresMigrator.apply()` and require exactly the packaged 022 tuple, then an
  empty replay result. Do not synthesize a ledger without executing the prefix.
- Select or add `semantic_plan_repair(character,character,text,uuid)` as the
  replaced-function identity target; compare OID, owner, ACL, security flag and
  search path, require changed definition, and prove NULL-input behavior changes
  from NULL to `command_input_invalid`. Preserve the child-function evidence.
- Add populated semantic success and escalation records if claiming their data
  preservation; snapshot actual rows and old ledger timestamps before/after.
- Retain the negative real-ledger-drift case and bounded advisory-lock
  contention/timeout/retry evidence. A generic latest-suffix test that only watches
  the child function is insufficient evidence for this replacement.

The coordinator has selected verified #166 commit
`23eb62dc21a090e6bf086cbc2a568d83417b0a2e` (PR #171) as this implementation's
prerequisite and will fast-forward the isolated branch to it before writer
dispatch, retaining the actual route. The resulting PR will stack on #166.
The inherited fixture additions are the populated latest-prefix upgrade, real
ledger-drift rejection, observed advisory-lock release success and timeout/retry
cases described above; they do not yet add semantic lifecycle rows or select the
plan function. The #163 writer must make those explicit extensions on the
integrated tree before its final verification. This analysis inspected those
additions in the separate #166 worktree and did not modify either branch or
perform the integration.

## Volume, indexes, locks and downtime

Before and after, the relational schema and persistent payloads are identical;
only the function's transient refusal JSON changes. There is no backfill,
distribution assumption, row rewrite, new scan, index build or storage growth
proportional to table volume. Existing indexed digest/idempotency lookups,
subject row lock, recursive lineage and per-task aggregate queries are unchanged.
This is source-based query-plan impact reasoning, not a measured EXPLAIN or load
claim. No new index or benchmark is justified for the diagnostic substitution.

The migration still performs catalog DDL and is not lock-free.
`PostgresMigrator.apply()` already serializes migrators with advisory key
`6164374679002001`, uses one transaction, and sets local lock and statement
timeouts to five seconds. Preserve those settings and the ledger transaction.
Contention or drift must stop the operation and leave the prior ledger/function
state intact. Do not claim that a running function call necessarily blocks
`CREATE OR REPLACE`; use the migrator's real advisory lock for deterministic
contention evidence. There is no requested application data downtime or drain,
but actual operational lock timing remains unmeasured until the bounded tests.

## Rollout, recovery and observable stop conditions

Ship parser support and migration 022 together. New code against a pre-022
database recognizes legacy NULL as a refusal. Old code against 022 continues to
fail closed but may temporarily label a new refusal envelope as corruption;
successful payloads remain unchanged. No deployed runtime or database is altered
by this source task.

A future authorized rollout should confirm the packaged migration tuple, matching
001–021 ledger, unchanged capability boundary, one newly applied 022 row and
idempotent empty replay. Stop on checksum drift, unsafe roles, timeout, unexpected
ACL/owner changes or any data difference. Named bounded refusal diagnostics are
the new observable signal; no new stored metrics schema or raw SQL error logging
is needed. Existing lifecycle records remain the source of truth for successful
repairs and escalations.

If the transaction fails, remove the external blocking condition and retry via
the migrator. After 022 is applied, never edit/delete its file or ledger row.
Recovery is a separately reviewed forward migration restoring the prior function
body if required, with the compatible parser retained. This report supplies no
operational deployment authority and executes no recovery SQL.

Shared-memory fact for coordinator recording: preserve the entire predecessor
function byte-for-byte after reversing only diagnostic substitutions; this
protects predicates, replay ordering and persistence behavior more strongly than
filtering guard lines. A current-prefix migration test must inspect the function
the latest resource actually replaces.
