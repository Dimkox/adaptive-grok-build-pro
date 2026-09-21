# Issue #163: SQL, Python and caller compatibility

Static integration analysis, 2026-09-21. Route `d2e7e68e7bd5`; selected role `integration_architect`; inspected product HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` on `fix/issue-163-repair-plan-rejections`. Read the route, engineering contract, bootstrap/state, required workflow skills, and the research packet `plans/design-163-semantic-plan-rejections.md` from change `20260921-research-open-backlog-map-each-item-to-its-sourc-d54d3a`. Remote refs were fetched. No product edits, test execution, compilation, database access or deployment occurred; external PR #170 owns the shared verification lane.

## Conclusion and design refinements

The proposed one-key `repair_plan_rejection` response can distinguish refused commands from corrupt results without weakening successful-result validation. Use the research packet's fourteen SQL reasons, local `planning_rejected` fallback and separate legacy `store_returned_null` sentinel. Preserve every success parser, request binding and service authorization check.

Two operational qualifications must enter the implementation plan:

1. Named reasons currently reach Python callers, not a repair HTTP endpoint: this tree has no such endpoint. The existing generic HTTP `StoreError` handler deliberately returns a fixed error.
2. Mixed code/database versions remain fail-closed at the parser boundary, but full API readiness requires exact migration-version equality. Parser compatibility does not establish a healthy rolling deployment or zero downtime.

Keep response classification **after** both database context managers have exited, as in the existing method. Moving rejection raising inside the transaction would change persistence behavior for an existing late refusal.

## Actual producer and consumer chain

| Boundary | Current implementation | Required behavior |
|---|---|---|
| SQL producer | `resources/018_semantic_validation_bridge.sql:1527`: coordinator-only `semantic_plan_repair(char,char,text,uuid) RETURNS jsonb` | Additive 022 replaces only the fifteen refusal expressions; keep the function signature, predicates, locks, successful JSON, exception list, ownership and execution privileges. |
| Store adapter | `store.py:665`: canonical command and digest, one SQL call, then result decoding/parsing | Inspect the exact rejection envelope and legacy null before the existing `RepairLifecycleResult.from_dict` call. |
| Successful result contract | `semantic_repair.py:348`: closed keys, typed nested objects, digests and mutual exclusion of repair/escalation | Leave this contract unchanged. A rejection is not a `RepairLifecycleResult` variant. |
| Request-specific bindings | `store.py:695–728`: subject/verdict/cycle, child/directive identity, and escalation request digest | Preserve all comparisons and diagnostic strings after successful parsing. |
| Service consumer | `service.py:326`: `request_semantic_repair` authorizes the operator and repository, calls the store, then optionally invokes the child broker | A store refusal propagates before any broker proposal or child-binding write. No extra retry or conversion into `needs_human`. |
| HTTP surface | `api.py:1190–1369` and `factory-semantic.v1.json` expose subject, assignment, evidence, adjudication and verdict operations only | No new route or OpenAPI change is needed for this bounded repair. |

The repository search found no production caller of `request_semantic_repair` outside its definition; lifecycle tests call it directly. `request_repair` is otherwise consumed by that service method and tests. This is a repository-local finding, not proof that no out-of-tree Python caller exists.

## Closed decoding and error matrix

Use a plan-specific reader beside `repair_child_rejection_reason`, rather than sharing the child reason set or `ESCALATION_REASONS`. Exact key equality is necessary; checking only whether the channel key exists would accept a smuggled success-shaped document.

| SQL/decoded value | Classification | Observable Python result |
|---|---|---|
| Exact one-key envelope, known string | Named command refusal | `StoreError("semantic repair plan rejected: <allowlisted reason>")`; no lifecycle parser call/cause |
| Exact one-key envelope, unknown string or non-string reason | Bounded unknown refusal | Same error with only `planning_rejected`; never interpolate the raw value |
| SQL `NULL`, Python `None`, or JSON text `null` | Legacy refusal | Same error with `store_returned_null`; this is not a SQL reason or corruption |
| Malformed JSON text | Corrupt wire response | Fixed `stored semantic repair result is corrupt` with the `JSONDecodeError` retained as cause |
| Empty/scalar/list/wrong-channel response, or envelope plus any extra key | Corrupt result | Existing closed lifecycle parser rejects it and remains the cause of the fixed corruption error |
| Valid lifecycle result with wrong request identity | Binding mismatch | Existing subject/verdict/cycle, child, or escalation binding error |
| Valid repair or escalation with correct identity | Existing success channel | Return the same typed lifecycle result |

Catch decoding failure narrowly. Do not wrap the new refusal raises in the existing corruption catch, suppress all errors, or broadly catch database exceptions. The current transaction timeouts and driver failures are outside this diagnostic change. The closed rejection reader itself does not create trusted success, repair authority, or a durable escalation.

The current child reader (`semantic_repair.py:73`) supplies the exact-key/allowlist precedent. An incoming child-rejection envelope must not be mistaken for a plan refusal; it is not a valid plan result either. The malformed-JSON wrapper changes the direct caller's exception type from a raw JSON decoding error to the intended store corruption error; cover that explicitly.

## Persistence, replay and authorization invariants

`store.py:682–688` leaves the connection/transaction before parsing its response. In SQL, the `semantic_directives` insert at 018:1997 can precede the child-conflict refusal at 018:2012. That normal return may retain the earlier write under the existing behavior; the new Python error must not silently introduce rollback. Conversely, the existing PL/pgSQL exception arm at 018:2040 retains its existing subtransaction rollback behavior. This report does not assert that every refusal is write-free.

Both idempotency lookups (018:1628 and 1899) must continue returning stored bytes for matching digests. Their mismatches share the bounded `idempotency_conflict` reason. Do not retry a refusal automatically or change the idempotency key to evade a conflict. Preserve the existing service retry behavior after a broker failure: replay the persisted proposal, with its existing child-proposal digest as broker idempotency key (`service.py:357–360`).

`deadline_exhausted` at 018:1875 is a persisted `needs_human` lifecycle outcome, not a precondition refusal. Keep that path, its ordering and replay after expiry intact. No new rejection reason should replace it.

Authorization remains at the existing operator kind, `semantic:repair` and repository checks (`service.py:335–341`), coordinator session boundary (`store.py:309–327`), and SQL ACL (018:2118,2147). Do not add a route, permission, SQLERRM disclosure, task identifier or arbitrary payload to a reason string.

## HTTP and operational observability

`api.py:384–388` maps a `StoreError` reaching an existing endpoint to HTTP 409 with `error=conflict`, `code=store_conflict` and fixed detail. It does not read or expose `str(error)`. Keep this behavior; neither precise API reason codes nor an HTTP 422 policy are implied by the proposed SQL envelope. There is currently no repair endpoint to exercise through an HTTP request.

The available improvement is a bounded reason in the direct Python exception, distinguishable from stored corruption and unchanged binding mismatches. No dedicated rejection metric, log sink or audit event is implemented in this path. The service accepts `correlation_id` but does not pass it to this store operation. Documentation must not claim new correlated persistence, metrics or externally visible rejection codes. These may be separate follow-up work if desired; they are not necessary to preserve the narrow contract here.

## Rollout and forward recovery

| Application package | Applied DB prefix | Adapter diagnostic behavior | Full core readiness |
|---|---|---|---|
| Existing through 021 | Through 021 | Anonymous null is currently mislabeled corruption | Version condition can pass |
| New package containing 022 | Through 021 | New reader recognizes legacy null refusal | `not_ready`: expected 22, observed 21 |
| Existing through 021 | Through 022 | Old success parser rejects a new refusal envelope as corruption | `not_ready`: expected 21, observed 22 |
| New package containing 022 | Through 022 | Named refusals and existing successes separated | Version condition can pass; other readiness checks still required |

Evidence: `PostgresStore.readiness` compares DB maximum migration version with `len(discover_migrations())` at `store.py:1315–1330`; `FactoryService.readiness` delegates to that core store (`service.py:96`); `/health/ready` returns 503 when its status is not ready (`api.py:465–472`). The semantic coordinator's own readiness check only verifies its session role (`store.py:333–337`) and cannot replace the core schema check.

Ship reader support and 022 together. Plan an independently authorized coordinated application/migration cutover with traffic drained or the affected service stopped; do not weaken readiness to allow mixed versions. Verify the exact packaged/applied version plus the unchanged capacity/accounting and role checks before resuming. There is no zero-downtime claim from this static analysis.

The migrator uses one transaction, five-second lock/statement bounds and its advisory lock (`migrations.py:200–219`); migration/ledger inserts occur together. A failed 022 attempt must preserve the old prefix for retry. After a successful migration, do not roll back by deleting 022 or reverting to a 021-only application package: that package would remain not ready. If needed, ship a later forward migration and matching package while retaining the compatible reader and immutable migration history. No deployment or recovery operation is authorized or executed by this analysis.

## Focused acceptance checks for the write owner

- Add real store-adapter tests with the existing `ProbeCoordinatorStore` for every known reason, unknown values, null forms, malformed JSON and extra-key/wrong-channel documents. Assert the refusal branches never call `RepairLifecycleResult.from_dict` and have no parser cause; retain corruption causes where applicable.
- Preserve valid-result, digest-corruption and request-binding cases, including an otherwise valid escalation with the wrong request digest.
- Add a service-level rejection case showing unchanged `StoreError` propagation, zero child-broker proposals and zero binding calls. Keep the existing denied-writer, `needs_human` and broker-retry tests.
- Use the research design's immutable-body/exact-substitution SQL proof, both idempotency sites, populated migration-prefix tests and coordinated PostgreSQL cases. No test was executed during this static analysis.

Coordinator memory handoff: record the distinction between parser compatibility and exact-version readiness in the change package and shared decisions when adopting the rollout. This report is analysis evidence, not verification, an implementation approval or merge authority.
