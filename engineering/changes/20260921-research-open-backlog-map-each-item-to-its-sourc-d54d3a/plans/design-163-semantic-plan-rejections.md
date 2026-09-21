# Issue #163 implementation design: named repair-plan refusals

Design only, 2026-09-21; route `d54d3afd1c92`. Based on frozen PR #170 HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`, main `90078959ff816068af374ad42f4bb80fdbaec866`. No implementation, migration execution, deployment or approval is implied. Source findings and executed probes: [analysis](../evidence/analysis-integration_architect.md).

## Outcome and exact boundary

`PostgresSemanticCoordinatorStore.request_repair` must distinguish a refused planning command, a malformed stored response, and a successful lifecycle result. Add one migration `022_semantic_repair_plan_rejection_reasons.sql` after PR #170's 021, one plan-specific closed rejection reader beside the child reader, and store classification before the existing success parser. Preserve all fifteen refusal sites, all existing predicates and successful/persisted responses. Do not change `RepairLifecycleResult`, ESCALATION_REASONS, contract documents, provider/runtime behavior, migration timeouts, authority freshness, tables, indexes or permissions.

Migration 022 is reserved by this design, not by a repository mutation. Reconfirm it is free when implementation starts; if occupied, use the next contiguous version and update this packet. PR #170 must remain a separate prerequisite rather than being rewritten.

## Proposed rejection vocabulary and complete site map

The response shape is exactly `{"repair_plan_rejection":"<reason>"}`. The table refers to immutable resource 018; there are 13 RETURN NULL statements and two ELSE NULL arms. Keep every clause group intact, without adding or regrouping guards.

| Site / 018 line | Existing refusal condition | Proposed reason |
|---|---|---|
| G01 / 1576 | Non-read-committed isolation, invalid/null key/digest/task, null/oversized canonical command | `command_input_invalid` |
| G02 / 1621 | Command hash/closed shape/bindings or repair-request fields invalid | `repair_payload_invalid` |
| G03 / 1626 | Cycle 1 has prior proposal, or cycle >=2 lacks prior proposal | `cycle_lineage_invalid` |
| G04 / 1632 | First idempotency lookup exists with a different request digest | `idempotency_conflict` |
| G05 / 1639 | Subject for this task and subject digest not found | `subject_not_found` |
| G06 / 1645 | Verdict missing or body differs from recomputed expected verdict | `verdict_mismatch` |
| G07 / 1660 | Workspace result, packet, manifest, current task or accepted intent missing | `execution_material_missing` |
| G08 / 1689 | Prior proposal/cycle/state/writer/base/architecture/authority/context mismatch | `previous_proposal_mismatch` |
| G09 / 1724 | Cross-subject child handoff/task/intent/source/head/time binding mismatch | `child_handoff_mismatch` |
| G10 / 1761 | Recursive lineage length or baseline/head/authority linkage mismatch | `lineage_mismatch` |
| G11 / 1779 | Baseline risk outside existing closed set | `baseline_risk_invalid` |
| G12 / 1903 | Second idempotency lookup exists with a different request digest | `idempotency_conflict` |
| G13 / 1995 | Existing directive differs in digest, subject or body | `directive_conflict` |
| G14 / 2012 | Existing child proposal differs in digest, directive or body | `child_proposal_conflict` |
| G15 / 2042 | Existing exception handler: unique/check/FK violation, invalid text, numeric range, data exception | `store_operation_rejected` |

Fourteen distinct SQL reasons; idempotency_conflict occurs twice. Use `store_operation_rejected` rather than a write-only label because the existing exception arm also catches conversion/input errors before writes. Do not expose SQLERRM, arbitrary JSON, identifiers or database text in the reason. Do not add a wrong-task-state guard merely because the original issue mentions it: diagnose the guards actually present.

## Python channel and parser order

In `semantic_repair.py`, add `REPAIR_PLAN_REJECTION_CHANNEL`, `UNKNOWN_REPAIR_PLAN_REJECTION = "planning_rejected"`, the fourteen SQL reasons plus that fallback in `REPAIR_PLAN_REJECTIONS`, and `repair_plan_rejection_reason(data)` mirroring the strict one-key child reader. A known string returns itself; an unknown/non-string value in the exact one-key envelope returns only `planning_rejected`; any other shape returns None so the existing closed success parser rejects it. Do not use the child vocabulary or ESCALATION_REASONS for these refusals.

In `store.py:request_repair`, after fetching the result:

1. Decode a string JSON response. Put JSONDecodeError under the existing stored-corruption diagnosis (bounded fixed error, original cause retained); it is not a refusal. This keeps malformed stored wire data in the corruption class rather than letting raw JSON parser errors escape.
2. Classify the exact rejection envelope and raise `StoreError("semantic repair plan rejected: <allowlisted reason>")` without a parser exception cause/context.
3. Classify `response is None` separately as `StoreError("semantic repair plan rejected: store_returned_null")`, supporting a pre-022 database and JSON `null`. This local sentinel is not emitted by 022 and is excluded from SQL-vocabulary equality.
4. Only then call `RepairLifecycleResult.from_dict` with its current TypeError/ValueError-to-`stored semantic repair result is corrupt` handling.
5. Preserve every existing subject/verdict/cycle, child/directive and escalation request-digest binding check and its error string.

An envelope plus extra fields is corrupt, even if the extra fields make a valid lifecycle body; neither parser may accept channel smuggling. A valid replay with a mismatched request binding remains a binding error. These changes do not add an HTTP response policy; existing StoreError handling remains authoritative.

## Deadline, persistence and transaction invariants

`018:1850+` already turns `v_deadline IS NULL OR v_deadline::timestamptz <= clock_timestamp()` into `v_reason='deadline_exhausted'`. That creates a valid, persisted `needs_human` lifecycle result and escalation. **It must not become a new rejection envelope or StoreError.** Preserve first-match ordering of the existing escalation chain, the first/second idempotency replay checks and response canonicalization. An already recorded successful repair must still replay after its deadline, because the first idempotency check precedes deadline evaluation.

Do not claim all refusals are write-free: G14 follows the conditional directive INSERT. A normal RETURN can retain prior work just as it does in 018. Preserve that behavior; separately flag any desired transactional cleanup as new scope. G15's existing PL/pgSQL exception block rolls back work within that block; preserve its exception list and structure. No additional catches, retries, generic exception swallowing or forced rollbacks.

## Migration mechanics and parity proof

022 contains `CREATE OR REPLACE FUNCTION factory.semantic_plan_repair(char,char,text,uuid) RETURNS jsonb` with the original LANGUAGE, SECURITY DEFINER and `SET search_path=pg_catalog,factory`. Retain function identity/ownership and existing ACL, and repeat the same PUBLIC revoke/coordinator EXECUTE grant as 018 if following 021's style; no additional roles get execution. No table/row/schema rewrite occurs outside the function definition.

Freeze all existing 001–021 bytes. The exact extracted original `semantic_plan_repair` text (from CREATE through the first closing `\n$$;`) has SHA-256 `5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32` in the inspected tree. A test must pin that value so coordinated edits to old/new bodies cannot make parity pass.

For stronger parity than dropping whole guard lines: extract both function texts; normalize only CREATE OR REPLACE back to CREATE, then replace each of the fifteen exact plan-envelope return expressions in the new body with NULL. Assert exact equality with the old function text. Require the ordered mapping and multiplicities above (15 sites, 14 names; idempotency_conflict twice, others once), and forbid any remaining RETURN NULL / ELSE NULL refusal site in 022. Keep both `THEN v_prior.response_body ELSE <idempotency envelope>` arms pinned explicitly. This catches changed predicates, removed checks, inverted CASE arms, altered inserts and changes to the deadline branch, rather than merely comparing a subset of lines.

## Tests and implementation order

1. Add failing Docker-free tests for the vocabulary/parser/store separation and expected migration identity. Reuse `ProbeCoordinatorStore`, `repair_fixture`, `request` and `result_wire` from `test_semantic_repair_lifecycle.py`; no fabricated database connection is needed.
2. Add the one-key reader and store handling. Cover every known reason, unknown string, numbers/list/object reason, legacy None, JSON null, malformed JSON, empty/list/scalar/extra-key result, success, corrupted digest, mismatched bindings. Refusals must never call `RepairLifecycleResult.from_dict`; assert no invalid_object trace or parser cause on those arms. Corrupt bodies must retain the ContractError cause where applicable.
3. Add 022 with only the mapped substitution. Extend `test_migrations.py`: immutable original hash, exact reversible body equality, vocabulary equality excluding fallback, 15-site multiplicity, expected signature/security/ACL, current contiguous resource count (22) and prefix planning. Do not weaken the existing 021 tests.
4. Add PostgreSQL runtime tests using the existing semantic fixture. Exercise early invalid command/hash/cycle/subject refusals, reachable verdict/material/lineage conflicts, directive/child conflicts, success, matching replay and conflicting idempotency. For states made unreachable by storage constraints, document that fact and rely on the exact frozen-body/site proof instead of disabling production guards to force them.
5. Exercise both idempotency lookups. For the second lookup, use two connections: hold the subject lock, let the competing command pass the first absent-key lookup and wait on the subject, then commit a stored command result with matching or conflicting digest before release. Synchronize by observed blocking state and explicit watchdogs, not arbitrary sleeps. Verify matching stored bytes and conflict reason respectively. This is request concurrency, separate from migration contention.
6. Deadline regressions: fresh valid material with expired deadline returns/persists/replays `needs_human/deadline_exhausted`; NULL deadline follows the same existing escalation where constructible; valid unexpired material permits repair; a recorded success still replays after expiry. Derive fixture time from the server, keep authority independently fresh, and ensure earlier budget/context/verdict branches do not mask the intended deadline branch. No production timeout widening.
7. Exception regression: a safely constructed invalid canonical JSON reaches existing G15 and returns store_operation_rejected; a controlled constraint-error case verifies existing subtransaction rollback when practical. Named non-exception conflicts retain original persistence semantics.
8. Run focused unit tests, then coordinated disposable PostgreSQL/current-prefix checks after implementation. Only then full route verification and independent code/test/data/security review as selected by the implementation route; external exact-head Trust CI remains separate.

## Coordination with issue #166

The currently prepared #166 requirements explicitly select `discover_migrations()[-1]` and the real prefix, preserve all old ledger rows/timestamps, verify OID/owner/ACL and test bounded advisory-lock contention. Its inspected documentation lives under `20260921-test-issue-166-ship-a-postgresql-current-prefix-af166e` in the dedicated #166 worktree.

On a tree including 022, its historical fixture must apply actual 001–021 SQL with real ledger rows, then the real migrator must return exactly the 022 Migration tuple; replay returns empty. Record the SHA from the actual packaged bytes. Extend its function-identity target mapping to inspect **semantic_plan_repair** for 022, while retaining semantic_bind_repair_child coverage for 021 where historical coverage exists; a test that only watches the old function is insufficient for 022. Preserve populated success/escalation rows and both functions' unchanged effective privileges. Do not fix latest=021 or repurpose the existing 021 test to hide loss of that evidence.

#166 must not be asked to modify production migration code or timeout values. Migration concurrency uses its documented advisory lock and server-side cancellation; do not claim an executing function necessarily blocks CREATE OR REPLACE. Deliver #163 after #170 and merge/rebase the #166 test contract before final verification. The coordinator owns cross-branch sequencing.

## Rollout, recovery, completion

Ship parser support and 022 in one product PR. Upgrading code before the database remains diagnostic-compatible through legacy NULL classification. Upgrading the database while an old process still runs continues to fail closed on the new envelope but may log the former corruption message until code is upgraded. State this short mixed-version diagnostic limitation explicitly; successful payloads are unchanged.

Run migration only through an independently authorized operational step. A failed migration transaction must leave the 001–021 ledger intact and permit retry after the blocking condition is removed. Once applied, never edit/delete 022 or the ledger to roll back. Recovery is a later forward migration restoring the prior body if needed, with the compatible parser retained; no recovery SQL or deployment is executed by this packet.

Done means all fifteen refusals are named, the fourteen-reason vocabulary is closed and synchronized, legacy NULL is separate from genuine corruption, deadline/escalation/replay behavior and bindings are unchanged, immutable-body/current-prefix evidence passes, and the final PR has the required independent exact-head gates. No implementation-complete claim is made here.
