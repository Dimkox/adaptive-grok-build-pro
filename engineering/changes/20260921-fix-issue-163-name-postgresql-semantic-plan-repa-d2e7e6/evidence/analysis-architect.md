# Issue #163: bounded architecture decision

Date: 2026-09-21. Route: `d2e7e68e7bd5`. Role: selected `architect`, read-only product analysis. Inspected branch `fix/issue-163-repair-plan-rejections`, HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. This is an implementation recommendation, not implementation verification or merge approval.

## Decision

Use the existing database/store boundary to distinguish a planning refusal from a malformed lifecycle result. Add one versioned function replacement, one plan-specific closed reader beside the existing child reader, and classification in `PostgresSemanticCoordinatorStore.request_repair` before the existing success parser. Keep `RepairLifecycleResult`, successful and persisted response bodies, service authorization, HTTP error policy, and all SQL predicates unchanged. No new service, framework, dependency, schema table, index, or generic rejection abstraction is needed.

The earlier `plans/design-163-semantic-plan-rejections.md` packet in the backlog research change is consistent with the inspected source. Migration `022` is available in this tree; the latest resource is `021_semantic_repair_child_rejection_reasons.sql`. Recheck the number at integration time rather than overwriting any resource another delivered branch introduces.

Coordinator sequencing decision: advance this branch by fast-forward from the inspected #155 head to the verified #166 prerequisite `23eb62dc21a090e6bf086cbc2a568d83417b0a2e` before the single writer starts, and stack the #163 PR on #166. Keep the existing tool-generated route identity. Recheck the original function hash and migration inventory on that actual implementation base; this report does not claim the planned advance has already happened.

## Source evidence and failure boundary

- `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql:1527` defines `semantic_plan_repair(char,char,text,uuid)`. Static extraction through its closing `\n$$;` confirms SHA-256 `5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32`, thirteen `RETURN NULL` statements and two `ELSE NULL` arms. These measurements were file reads, not SQL execution.
- `factory/src/adaptive_factory/store.py:665` commits the function transaction, decodes any string response, and passes every result to `RepairLifecycleResult.from_dict`. A legitimate SQL NULL refusal consequently becomes `stored semantic repair result is corrupt`, chained from a contract parsing error.
- `factory/src/adaptive_factory/semantic_repair.py:334` defines a closed success/escalation contract and verifies nested digests and bindings. The existing child rejection reader near the top of this module provides the appropriate small implementation pattern.
- `factory/src/adaptive_factory/service.py:326` still requires the coordinator/operator capability and repository access before requesting repair. `factory/src/adaptive_factory/api.py:384` maps StoreError to the existing fixed HTTP 409 response. This task should not expose database reason strings through a new HTTP contract.
- `factory/src/adaptive_factory/migrations.py:69` rejects missing or altered applied resources. An edit to 018, deletion of a newly applied 022, or a source revert that removes 022 is not database rollback.

## Producer/consumer contract

The SQL refusal value is exactly `{"repair_plan_rejection":"<reason>"}`. Its fourteen producer codes map to the existing fifteen sites:

| Existing refusal | Code |
| --- | --- |
| Initial isolation/key/digest/canonical-size/task guard | `command_input_invalid` |
| Command hash, closed shape and repair fields | `repair_payload_invalid` |
| Prior-proposal/cycle consistency | `cycle_lineage_invalid` |
| Either idempotency lookup finds another request digest | `idempotency_conflict` |
| Subject absent for the requested task/digest | `subject_not_found` |
| Verdict absent or different from expected verdict | `verdict_mismatch` |
| Required execution material absent | `execution_material_missing` |
| Previous proposal mismatch | `previous_proposal_mismatch` |
| Cross-subject child handoff mismatch | `child_handoff_mismatch` |
| Recursive lineage mismatch | `lineage_mismatch` |
| Baseline risk outside the existing set | `baseline_risk_invalid` |
| Existing directive conflict | `directive_conflict` |
| Existing child proposal conflict | `child_proposal_conflict` |
| Existing exception-handler arm | `store_operation_rejected` |

Use a separate `REPAIR_PLAN_REJECTION_CHANNEL`, `REPAIR_PLAN_REJECTIONS`, `UNKNOWN_REPAIR_PLAN_REJECTION = "planning_rejected"`, and `repair_plan_rejection_reason`. The reader accepts only the exact single-key mapping. Known string values retain their code; unknown strings and non-string values in that exact envelope become the fixed local fallback. Other shapes return no rejection classification and remain subject to the unchanged lifecycle parser. Never interpolate the raw reason value, SQLERRM, row contents or identifiers into the StoreError.

After fetching the database response, keep this order outside the existing transaction context:

1. Decode a string JSON response, translating malformed JSON to the existing bounded corruption error with its original exception cause.
2. Recognize the closed plan-rejection envelope and raise `StoreError("semantic repair plan rejected: <allowlisted reason>")` without a contract-parser cause or context.
3. Recognize Python `None` (SQL NULL or decoded JSON null) as `StoreError("semantic repair plan rejected: store_returned_null")`. This is a compatibility sentinel, not a SQL reason.
4. Parse the unchanged `RepairLifecycleResult`; preserve all subsequent subject/verdict/cycle, child/directive and escalation request-digest checks and their diagnostics.

The Python fallback is excluded from SQL-vocabulary equality. An envelope with any extra key must remain corrupt, including a valid-looking lifecycle body with an added rejection key. Successful replay bodies cannot bypass existing request-binding checks.

## Invariants and exclusions

Replace only the fifteen NULL refusal expressions. Preserve the exact function argument types, return type, language, SECURITY DEFINER, `search_path=pg_catalog,factory`, subject `FOR UPDATE`, both idempotency lookups, exception list, inserts, canonicalization and capability privileges. Preserve the existing PUBLIC revoke/coordinator EXECUTE grant; verify unchanged function OID, owner and effective ACL on upgrade.

Do not regroup clauses or add a task-state guard inferred from the issue narrative. Do not widen lock, statement or authority freshness limits. Keep child rejection vocabulary and lifecycle `ESCALATION_REASONS` independent of this new protocol channel.

Expired or null deadlines already select `needs_human/deadline_exhausted` through the existing escalation branch. That result is persisted and replayable; it is not an anonymous refusal. A previously recorded matching repair remains replayable after deadline expiry because the first idempotency lookup precedes deadline evaluation. Preserve first-match ordering of the whole escalation chain.

Do not describe every refusal as write-free. The child-conflict RETURN follows the possible directive INSERT, and the Python transaction has already committed before response classification. Moving classification or raising inside that transaction would silently change persistence behavior. Preserve this boundary; the existing exception block retains its own rollback semantics. Any transactional cleanup belongs to separately routed work.

## Acceptance and evidence required from implementation

- Pin the original function hash above. Reverse only `CREATE OR REPLACE` and each exact new envelope expression to the original text, then require byte-for-byte function equality. This checks the entire function, including successful inserts, deadlines and CASE arms; matching only selected guard lines is weaker.
- Assert exactly fifteen replacement sites, fourteen emitted codes, `idempotency_conflict` twice and every other producer code once; require SQL/Python set equality after removing only the Python fallback. Preserve the current 021 evidence and all 001–021 bytes.
- Add offline regressions for every known code, unknown/non-string values, legacy NULL and JSON null, malformed JSON, extra-key/scalar/list bodies, valid lifecycle results, corrupt digests and request-binding mismatch. Rejection/legacy paths must not call the lifecycle parser and must not retain `invalid_object` in exception cause/context. Genuine corruption must keep its cause.
- Exercise reachable PostgreSQL refusal paths, successful planning, both idempotency lookups, persisted deadline escalation and successful replay after expiry. Use observed blocking state and bounded watchdogs for the second lookup race. Storage constraints may make some sites unreachable through ordinary fixtures; record that limitation and retain the full-body proof rather than weakening guards to manufacture coverage.
- Verify the populated current-prefix upgrade, not just a clean install: real 001–021 ledger and retained rows, apply actual 022 only, unchanged function identity/privileges, then empty replay. Coordinate this with issue #166; its latest-function target must become `semantic_plan_repair` when combined with 022 while retaining historical 021 coverage.
- After implementation, run the route's full preflight and the selected independent code, test and data reviews on the frozen tree. Only the external exact-head App check and required external approval scopes establish merge eligibility.

No test, compiler, Docker command, SQL execution or deployment ran for this analysis. External Trust CI for PR #170 currently owns the heavy execution lane.

## Rollout and recovery

Ship compatible Python reading and additive migration 022 in the same source PR after the #155 and #166 prerequisites. At the parser boundary, new code still diagnoses an old database's NULL through `store_returned_null`; an old parser still refuses the new envelope through its corruption path. These are fail-closed diagnostic properties, not an operational rolling-upgrade guarantee. `factory/src/adaptive_factory/store.py:1325` requires the database version to equal `len(discover_migrations())`, so either mixed-version direction reports not-ready: package 022 against database 021, and package 021 against database 022. Keep that readiness check unchanged.

Plan a separately authorized coordinated rollout: drain affected work, stage the matching application/resources, apply the additive migration with the existing migrator, start the matching version, and verify readiness before resuming intake. Do not promise zero downtime or present a parser-compatible but not-ready mixed version as accepted service. Successful lifecycle wire bodies remain unchanged throughout the source contract.

An operational migration run requires its own exact authorization. It changes only the function definition/expected grants, with no backfill or data rewrite. Retain existing migrator transaction and timeout behavior. On failure, confirm the applied prefix is intact and retry only after the actual blocking condition is removed; do not widen timeouts as part of this issue.

After successful application, retain packaged 022 and its ledger record. Recovery requires a separately tested forward migration restoring the previous function behavior if necessary while keeping the compatible reader. This source task neither deploys such a correction nor changes external Trust CI state.

## Shared-memory fact for coordinator

Record in shared memory after the implementation proves it: classifying protocol refusals before a closed success parser preserves useful diagnostics without widening the lifecycle schema, while exact reversible function-text comparison prevents incidental predicate or transaction changes. Keep recorded escalation outcomes and command refusals as distinct channels. The initial architecture draft inferred deployment compatibility from parser compatibility without checking strict migration-version readiness; cross-agent integration review exposed that gap, and the rollout above now requires coordinated drain/upgrade/readiness instead.
