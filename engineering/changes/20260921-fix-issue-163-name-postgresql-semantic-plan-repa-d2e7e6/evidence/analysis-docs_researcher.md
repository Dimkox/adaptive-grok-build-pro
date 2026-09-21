# Issue #163: acceptance, contracts and operational compatibility

Date: 2026-09-21. Selected role: `docs_researcher`. Route: `d2e7e68e7bd5`; change: `20260921-fix-issue-163-name-postgresql-semantic-plan-repa-d2e7e6`. Inspected worktree: `fix/issue-163-repair-plan-rejections`, HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`. This is static analysis, not an implementation review or verification receipt. No tests, imports of product code, compilation, Docker, database access or operational mutation were performed.

The issue body was read from the coordinator's cached GitHub inventory, entry `163`, and checked against current source. The prior design packet is `engineering/changes/20260921-research-open-backlog-map-each-item-to-its-sourc-d54d3a/plans/design-163-semantic-plan-rejections.md` in the separate backlog worktree. The current worktree already contains the #155 prerequisite. Its inherited bootstrap still names that older delivery; the coordinator should update the active #163 handoff without rewriting the dated #155 observations. The route's recorded base `90078959ff816068af374ad42f4bb80fdbaec866` is not the inspected stacked HEAD and should not be silently replaced.

Before implementation the coordinator has selected a fast-forward to verified #166 HEAD `23eb62dc21a090e6bf086cbc2a568d83417b0a2e`, with the new PR stacked on #166. That prerequisite includes #155 and provides the current-prefix migration test. This report's line references and extracted function hash describe the inspected 1f7 base; the writer must retain and extend the inherited #166 proof when applying 022. No route replacement is implied.

## Outcome and separate issues

The required behavior is to distinguish a planning refusal, an unreadable stored/result document, and a valid lifecycle outcome. A refusal must identify a bounded allowlisted reason without relaxing any planning predicate, lock, privilege or result binding.

| Scope | Existing producer/consumer | Required distinction |
| --- | --- | --- |
| #155, prerequisite | `semantic_bind_repair_child(char,text)` and `store.bind_repair_child` | Already uses migration 021 and `repair_child_rejection`; nine former NULL paths have twelve named reasons. Its child-binding schema, vocabulary and fixtures remain unchanged by #163. |
| #163, this route | `semantic_plan_repair(char,char,text,uuid)` and `store.request_repair` | Fifteen anonymous refusals need a separate `repair_plan_rejection` channel and parser. The prior design proposes fourteen SQL reasons because idempotency conflict appears twice. |
| #164, separate fixture repair | Deadline/authority timing in disposable PostgreSQL fixtures | Do not equate a fixture clock repair with naming plan refusals, or broaden #163 into production timeout changes. |

Static reading of `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql:1527` through its first closing `$$;` independently confirmed thirteen `RETURN NULL` statements and two `ELSE NULL` arms. The extracted function SHA-256 is `5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32`, matching the prior design packet. The current resource inventory ends at 021; 022 is available at this observation.

The issue's examples are descriptive, not authority to introduce a new wrong-task-state guard. Name the refusal sites that actually exist. The existing exception arm catches input/conversion failures as well as write constraints; its proposed `store_operation_rejected` name is more accurate than a write-only name.

## Current and proposed error contracts

The producer is the coordinator-only PostgreSQL SECURITY DEFINER function (`018:1527–1531`, revoke at `2118`, grant at `2147–2148`). Its consumer is `PostgresSemanticCoordinatorStore.request_repair` (`store.py:665–729`), called by the authenticated coordinator service (`service.py:326–349`). The service requires the operator actor and repository-scoped `semantic:repair` capability; no new actor or capability is needed.

Current `store.py:689–694` decodes JSON strings, then passes every value to `RepairLifecycleResult.from_dict`. SQL NULL consequently becomes `ContractError("invalid_object", "repair_lifecycle_result")` and then `StoreError("stored semantic repair result is corrupt")`. JSON decoding is currently outside that corruption handler, so malformed string JSON can escape as a decoder error; the proposed bounded classification should cover that wire-shape failure too.

| Received value | Proposed store classification | Compatibility obligation |
| --- | --- | --- |
| Exact one-key envelope with known plan reason | `StoreError("semantic repair plan rejected: <allowlisted reason>")` | Classify before the lifecycle parser; no synthetic contract-parser cause. |
| Exact one-key envelope with unknown or non-string reason | Fixed local fallback `planning_rejected` | Never interpolate raw reason text, JSON, identifiers or SQLERRM. |
| SQL NULL or JSON `null` | Fixed local sentinel `store_returned_null` in the plan-refusal error | Allows the new reader to diagnose a pre-022 database; this sentinel is not a SQL-emitted vocabulary member. |
| Extra keys, a lifecycle body with a smuggled channel key, malformed JSON, invalid lifecycle shape/digests | Existing bounded corruption error | Do not accept an envelope plus extra keys, or weaken closed result parsing. Preserve the actual parse/contract cause where applicable. |
| Valid lifecycle result with mismatched request bindings | Existing binding-specific errors | Preserve subject/verdict/cycle checks at `store.py:695–700`, child/directive checks at `701–723`, and escalation request-digest check at `724–728`. |
| Valid `repair` or `needs_human` result | Existing `RepairLifecycleResult` | Preserve all success and escalation payloads, digests, persistence and replay. |

`RepairLifecycleResult.from_dict` closes its field set at `semantic_repair.py:347–350`, then validates nested digests, decision-specific fields and bindings. `RepairEscalationV1` restricts reasons to `ESCALATION_REASONS` (`304–329`). Neither is an error-envelope schema and neither should be changed. The plan allowlist belongs alongside, but separate from, the existing strict child reader at `semantic_repair.py:44–80`.

The six paths in `factory/contracts/openapi/factory-semantic.v1.json` cover subjects, assignments, evidence, adjudications and verdict reads; they do not expose a repair-planning route. The generic `StoreError` HTTP handler at `api.py:384–388` emits bounded HTTP 409 / `store_conflict`. This route should not add an endpoint, change HTTP status/error schemas or expose detailed internal reasons through HTTP. No new telemetry system is needed: the fixed local error reason supplies the requested diagnostic signal without raw data or high-cardinality metric labels.

## Semantics the documentation must preserve

1. **Deadline exhaustion is a valid outcome.** At `018:1875–1876`, a missing/expired deadline sets `deadline_exhausted`; `1906–1935` persists an escalation and command result with `decision="needs_human"`. It is not an anonymous refusal and must not become a rejection envelope. Preserve the ordering of the entire escalation chain so earlier reasons remain authoritative.
2. **Idempotency has two lookups.** Both matching digest arms must return the previously stored response unchanged; only the conflict arms change from NULL to the same named refusal. A previously recorded success must still replay after deadline expiry because the first lookup precedes deadline policy.
3. **A refusal is not a guarantee of zero writes.** The child-proposal conflict at `018:2005–2012` can follow a directive INSERT at `1996–2002`. `request_repair` exits the transaction context before interpreting the returned value. Preserve that existing behavior; do not move classification into the transaction and thereby introduce a rollback, or add cleanup under a diagnostics-only repair. The existing PL/pgSQL exception block has separate subtransaction behavior and an explicit unchanged exception list (`2040–2042`).
4. **No new migration or runtime authority.** The existing migrator validates a contiguous immutable `(version, name, sha256)` prefix (`migrations.py:48–79`), uses a transaction plus advisory lock and five-second lock/statement timeouts (`189–204`), and records each applied resource in that transaction (`218–235`). Replacing 018 in place would break existing databases. Add 022; retain 001–021 byte-for-byte, roles, function identity, owner, SECURITY DEFINER/search_path and effective ACL. No table, index, bulk row rewrite, backfill or new query shape is required.

## Acceptance evidence to record

| Obligation | Necessary evidence after implementation |
| --- | --- |
| Refusals differ from corruption | Failing-then-passing unit cases for every known reason, unknown/non-string fallback, legacy NULL/JSON null, malformed JSON and malformed/extra-key bodies; assert the lifecycle parser is not called on refusals. Keep genuine corruption causes and binding-specific errors. |
| Exactly the intended SQL changed | Pin the original function hash above; reverse only the new return-expression substitutions and `CREATE OR REPLACE` marker, then require exact equality to 018. Check fifteen sites, fourteen distinct names, both idempotency arms, SQL↔Python vocabulary equality with the documented local fallback/sentinel excluded, and absence of anonymous refusal returns. Do not weaken existing 021 evidence. |
| Success and escalation stay intact | Unit and disposable PostgreSQL coverage for success, matching/conflicting replay, unchanged bindings, expired-deadline persisted escalation and replay, and recorded success replay after expiry. Fixtures must reach the intended branch without stale authority or earlier budget/context conditions masking it. |
| Database guards behave as named | Exercise reachable early/input/subject/verdict/material/lineage/conflict paths and an existing exception path. Record constraint-unreachable cases explicitly and use the immutable complete-body parity proof for them; do not disable real guards to manufacture coverage. |
| Both replay races are preserved | Use bounded, observed PostgreSQL blocking to reach the second lookup and verify matching response bytes versus conflicting digest. Avoid scheduling assumptions or arbitrary sleeps. This is distinct from migration advisory-lock contention. |
| Migration is additive and retry-safe | Real populated 001–021 ledger upgrade through the migrator to 022, immutable ledger digests/timestamps/data, retained function OID/owner/ACL, empty replay and bounded timeout/retry evidence. Coordinate with #166, whose current-prefix contract needs to inspect `semantic_plan_repair` when latest becomes 022; retain historical 021 child-function coverage. Update count assertions that still expect 21 without altering historical-prefix semantics. |
| Final source is deliverable | Full `grok_verify --mode pr`, then selected independent `code_review`, `test_review`, `data_review` reports and current fingerprint-bound receipts. This route selects no separate security review agent. Final merge authority remains the exact-head, current-base App-owned Trust CI check and any externally required signed approval scopes. |

No item in this table is claimed to have passed by this analysis. The coordinator reserves the CPU lane for execution; this report supplies static acceptance obligations only.

## Rollout and handoff wording

Ship the reader and additive resource in one source PR stacked on #166, which includes the #155/#170 prerequisite. At the parser level, the new code against a pre-022 database returns the bounded legacy-NULL refusal. An older reader encountering a post-022 refusal remains fail-closed but may still report the former corruption diagnosis; successful response shapes remain unchanged.

This parser compatibility does not mean mixed-version service readiness. `store.py:1315–1328` requires the maximum applied migration version to equal the packaged migration count, and `api.py:465` returns HTTP 503 when readiness is not ready. Both new package/old database and old package/new database therefore fail that version check. A later authorized rollout must coordinate draining/stopping the old composition, migrating and starting the matching package, and restoring readiness after validation. Do not claim zero downtime, independent rolling compatibility or loosen readiness as part of this repair.

Actual migration/deployment requires its own exact operational authorization. On migration failure, preserve the existing ledger and retry only after the blocking cause is removed. Once 022 is applied, recovery is a reviewed forward migration restoring the prior body if needed, with compatible readers retained; never edit/delete a shipped resource or ledger row. No downgrade, recovery SQL or deployment is authorized by this source-analysis task.

The active brief, acceptance criteria, test plan, rollback notes and fresh-agent handoff should state this boundary. Update current README claims when the candidate exists, leaving historical release/runtime records intact and retaining architecture links. Do not mark #163 fixed merely because #155 is delivered; closure needs the separately delivered planning change and final evidence.

Shared-memory fact for the coordinator to retain: separate diagnostic rejection channels preserve closed success schemas and make failures useful without changing policy. Full reversible function-body comparison is valuable here because it catches changes to predicates, replay ordering, escalation and persistence that a guard-line-only comparison can miss.
