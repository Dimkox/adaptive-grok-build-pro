# Issue #163 repository exploration

Route `d2e7e68e7bd5`; selected role `repo_explorer`; inspected source HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` on `fix/issue-163-repair-plan-rejections`, 2026-09-21. This is static analysis, not implementation or verification. Read the entrypoints, active route and adaptive-delivery/bugfix/API/data skills. The coordinator owns route transitions and fetched refs; this agent made no product edits, ran no tests, compilation or Docker, and did not delegate. All source paths below are repository-relative; line numbers describe the inspected HEAD.

**Baseline handoff:** while this report was being completed, the coordinator fast-forwarded this branch to verified #166 prerequisite `23eb62dc21a090e6bf086cbc2a568d83417b0a2e`, keeping route `d2e7e68e7bd5` and planning the new PR on #166. Read-only `git rev-parse HEAD` confirmed that new HEAD. The factory-source/test diff between the two baselines contains only `factory/tests/test_execution_persistence_postgres.py`; the source code and001–021 migration findings/hashes below are unchanged. Line references to that test file in the general update checklist describe the original1f7 baseline; the #166 subsection gives the new helper locations.

The defect is confirmed by the direct source chain: `semantic_plan_repair` still returns unnamed SQL NULL refusals in resource 018; `PostgresSemanticCoordinatorStore.request_repair` immediately sends that value into the closed lifecycle parser. `_object(None, "repair_lifecycle_result")` raises `ContractError("invalid_object", ...)`, which the store recasts as corruption. The already delivered child-binding fix in resource 021 does not change this function.

## Complete SQL refusal map

Source: `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql`, function lines 1527–2044. Static extraction measured **13 `RETURN NULL` statements plus two `ELSE NULL` arms**, totaling fifteen refusal sites. Proposed labels below match the coordinator's existing bounded design; there are fourteen distinct labels because the two idempotency sites share a reason. These names describe the existing branch groups and do not authorize new predicates or finer regrouping.

| Site | Return line | Existing branch, in execution order | Proposed fixed reason |
|---|---:|---|---|
| G01 | 1576 | Isolation is not read committed; null/invalid idempotency key or request digest; null/over-262144-byte canonical command; null task UUID. | `command_input_invalid` |
| G02 | 1621 | Canonical hash mismatch; wrong four-key command shape, contract, key or task binding; wrong fifteen-key repair request shape/version; invalid cycle/fence/digests/SHAs/writer/risk/previous-proposal representation. The existing cast/JSON expressions can also throw into G15; preserve that evaluation. | `repair_payload_invalid` |
| G03 | 1626 | Cycle 1 carries a previous proposal, or cycle >=2 lacks one. | `cycle_lineage_invalid` |
| G04 | 1632 | First `semantic_command_results` lookup finds `plan_repair` with this idempotency key but a different request digest. The matching CASE arm returns the stored body. | `idempotency_conflict` |
| G05 | 1639 | No subject matches both task UUID and subject digest in the `FOR UPDATE` lookup. | `subject_not_found` |
| G06 | 1645 | Verdict absent or its body differs from `semantic_expected_verdict(subject_digest)`. | `verdict_mismatch` |
| G07 | 1660 | Missing workspace result, execution packet, execution manifest, current task or accepted intent. | `execution_material_missing` |
| G08 | 1689 | For cycles 2–3: prior proposal absent; wrong predecessor cycle, pending state, writer, base or architecture; no previous subject/packet with matching authority excluding head; or cross-subject original context mismatch. | `previous_proposal_mismatch` |
| G09 | 1724 | Cross-subject proposal handoff missing or mismatched; child task/intent/repository/API source/digest/base/architecture/head/authority bindings differ; task accepted before proposal. | `child_handoff_mismatch` |
| G10 | 1761 | Recursive lineage length differs from cycle minus one; inconsistent/out-of-set baseline risk, parent head or subject authority linkage. | `lineage_mismatch` |
| G11 | 1779 | Chosen baseline risk satisfies the existing `NOT IN ('low','medium','high','critical')` predicate. Do not add a NULL check or change SQL three-valued behavior. | `baseline_risk_invalid` |
| G12 | 1903 | Second idempotency lookup finds a conflicting request digest after the subject lock and policy evaluation. Matching arm still returns the stored body. | `idempotency_conflict` |
| G13 | 1995 | Existing directive, selected by directive digest or verdict digest, has a different digest, subject or body. | `directive_conflict` |
| G14 | 2012 | Existing child proposal, selected by digest or subject/cycle, has a different digest, directive or body. This site follows the conditional directive INSERT. | `child_proposal_conflict` |
| G15 | 2042 | Existing exception arm catches unique/check/FK violation, invalid text representation, numeric range error or data exception. | `store_operation_rejected` |

Measured SHA-256 of the exact extracted function, from `CREATE FUNCTION` through its first closing `\n$$;`, is **`5ceffc2373c2cb7849f3accc79ed9b6b9b51024ce7b36f975c50ca71530e7d32`**. This matches the prior design packet. A parity test should normalize only `CREATE OR REPLACE` and the fifteen named envelope expressions back to the old NULL expressions, then require exact equality against this frozen original. `_guard_lines` in the existing 021 tests discards whole return lines and is weaker than needed here. Require the ordered site labels and multiplicities as well as set equality.

## Behavior that must remain distinct

- Lines 1806–1897 choose valid persisted escalation reasons in first-match order. Writer/cycle/head/risk/diff/architecture/authority/base/workspace/fence/disposition/budget/context/verdict policy outcomes remain lifecycle results, not new refusal envelopes.
- In particular, **lines 1875–1876** set `v_reason='deadline_exhausted'` when the deadline is NULL or expired. Lines 1906–1935 persist the escalation and command response and return `needs_human`. Do not relabel that as a planning refusal.
- The first idempotency lookup precedes subject locking and deadline evaluation; the second precedes escalation persistence. A matching recorded result still replays when the current deadline is expired. Both successful CASE arms must remain unchanged.
- `FOR UPDATE` at 1638 serializes planning for a subject. Keep both lookups, recursive lineage queries, all successful canonicalization and INSERT order intact. No new locks, retries, timeout changes, indexes or table changes are needed for diagnostics.
- A normal G14 return can retain an earlier directive INSERT; Python currently leaves its transaction context before parsing. Therefore the change cannot claim that all refusals are write-free or use new exception placement to force rollback. G15 retains its existing exception-block rollback behavior and exception list.
- Storage constraints explain why some guards are defensive: subjects reference results, packets and manifests with `ON DELETE RESTRICT` (018:55–80); child proposals constrain cycle/state and reference prior proposals (018:136–150). Do not disable constraints or broaden production behavior to make every guard executable in a test.

## Python call and parse path

`factory/src/adaptive_factory/service.py:326–374` is the production caller found by source search. It requires operator `semantic:repair` authority and repository scope, builds `SemanticRepairRequestV1`, calls `request_repair`, checks the result type, and only invokes the child broker for a `repair` result. There is no other product caller found by `rg`.

`factory/src/adaptive_factory/store.py:665–729` currently:

1. Rejects non-`SemanticRepairRequestV1` input, builds the four-key `adaptive-factory.semantic-repair-command/v1` envelope, then computes canonical digest and JSON.
2. Opens a connection/transaction/cursor, sets both local lock and statement timeouts to five seconds, calls `SELECT factory.semantic_plan_repair(%s,%s,%s,%s)`, reads the first cell, and exits the transaction contexts.
3. Runs `json.loads` for string responses **outside** its current parser try/except. Malformed JSON currently escapes as `JSONDecodeError`; treating it as stored corruption requires an explicit bounded catch, without treating it as a refusal.
4. Calls `RepairLifecycleResult.from_dict`; TypeError/ValueError become `StoreError("stored semantic repair result is corrupt")` with the original cause. SQL NULL and JSON `null` currently reach `_object` and produce `invalid_object: repair_lifecycle_result`.
5. Checks subject/verdict/cycle request bindings; on `repair`, checks child task/workspace/fence/head/writer/context/base/architecture/authority/diff/previous-proposal and directive head; on escalation, checks request digest. Preserve all checks and their existing messages.

`factory/src/adaptive_factory/semantic_repair.py:334–424` implements an eleven-key closed success/escalation result. It validates decision, digests, nested directive/child/escalation bindings and `ESCALATION_REASONS`. Do not extend this success schema with rejection fields. `ContractError` is a ValueError (`contracts.py:18`); `_object` is in `semantic_contracts.py:33`, and closed-key validation is in `contracts.py:44`.

The nearby child pattern is `semantic_repair.py:52–80` and `store.py:731–767`: only an exact one-key Mapping is a rejection channel, unknown/non-string values fold to a fixed local fallback, and old database NULL gets a separate `store_returned_null` diagnostic. Mirror that shape for a distinct `repair_plan_rejection` channel and `planning_rejected` fallback before the lifecycle parser. Extra-key envelopes must remain corruption. Keep the local legacy NULL sentinel outside the SQL reason-set equality.

The existing HTTP `StoreError` handler (`api.py:384–388`) returns the bounded generic 409 `store_conflict` response and does not expose the exception text. No HTTP policy change is implied by this diagnostic fix.

## Existing fixtures and regression insertion points

| File and location | Reusable facility or existing coverage | Needed care |
|---|---|---|
| `factory/tests/test_semantic_repair_lifecycle.py:24–127` | `repair_fixture`, `request`, `repair_result` create typed subject/verdict/request and a fully bound successful result. | Exercise exact refusal envelope, fallback values, legacy NULL/JSON null, corruption and success without PostgreSQL. |
| Same file:189–213 | `ProbeCoordinatorStore`, `result_wire`; `FakeCursor`/`FakeConnection` come from `test_semantic_persistence.py:28–60`. | Fake cursor yields one cell and captures SQL/parameters; no fabricated live connection is needed. |
| Same file:384–404 | Existing canonical command/success test and tampered child-digest corruption. | Keep success and binding checks; add explicit no-lifecycle-parser calls/no parser cause for refusal arms. |
| `factory/tests/test_semantic_repair.py:105` | Python policy test for `deadline_remaining_seconds=0` -> deadline exhaustion. | It does not establish PostgreSQL persistence, SQL NULL deadlines or replay-after-expiry. |
| `factory/tests/test_migrations.py:383–621` | Function extractor, additive 021/closed vocabulary/channel separation/store traceback tests, guard mapping and frozen child-body hash. | Keep 021 coverage intact; add separate 022 exact-body and ordered fifteen-site assertions. |
| `factory/tests/test_postgres_integration.py:5344–5682` | `semantic_repair_fixture` creates real task/execution/subject/evidence/verdict, supports parent/child, bounds, hooks and an injected server intake clock. | Reuse the server-clock behavior from #164; independently maintain authority freshness for deadline tests. Returned keys include task/result/published/verdict/intake. |
| Same file:5685–6800 | Large semantic test covers successful concurrent planning, replay, escalation policies, cycles, child binding and capability separation. | Existing concurrency at6026 uses two **different** keys; it does not force the second same-key lookup. Add synchronized blocking-state coverage for G12 rather than claiming this covers it. |
| Same file:6756–6783 | Effective EXECUTE privileges: only coordinator may call plan/bind; validator, adjudicator and runtime denied. | Keep the exact role matrix after 022; add OID/owner/ACL before/after migration evidence. |

Three existing PostgreSQL assertions expect the obsolete generic `"repair result"` substring and need the exact new reason instead:

- `test_postgres_integration.py:6061`: same idempotency key, changed context -> G04 `idempotency_conflict`.
- `:6104`: cycle 3 points at absent previous digest -> G08 `previous_proposal_mismatch`.
- `:6352`: cycle 3 points at cycle-1 proposal -> G08 `previous_proposal_mismatch`, before the recursive-lineage check.

Runtime reachability and new test outcomes are unmeasured in this report. The byte-for-byte body proof is necessary but does not replace executable cases, current-prefix migration evidence, or external verification.

## Migration interactions and full-suite update checklist

At inspection there are **21** packaged SQL resources and no `022_*.sql`; 022 is available. Discovery (`migrations.py:48–66`) hashes exact bytes, sorts numeric versions and demands contiguous versions from001. Prefix planning (`:69–79`) rejects any name/hash/history drift and applies only the suffix. `PostgresMigrator.apply` (`:189–249`) takes its existing transaction advisory lock under five-second limits, applies SQL and ledger INSERTs in one transaction. No migrator behavior changes are needed.

Use an additive function-only 022 with the exact `semantic_plan_repair(char,char,text,uuid)` identity, `SECURITY DEFINER SET search_path=pg_catalog,factory`, PUBLIC revoke and coordinator-only EXECUTE grant already present at018:2118/2147. Preserve every byte of001–021. Relevant measured full-resource hashes:

| Resource | SHA-256 |
|---|---|
| 018 | `33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70` |
| 019 | `e0cf573b2bd183f5bf6291f02d330e98edf7d4e00d34944daba5719eee91c790` |
| 020 | `524c94bf95f38f8a339c3f5b1165d7f7b7fffc81eb7fd8a2faff4362f33d2ae3` |
| 021 | `868bc21f47351f92b79acb8bd8e9390c62b43803c0b5761400e32c7143d56d5e` |

Adding 022 also requires adjusting existing **current-tree** migration expectations; these are not reasons to edit historical resources:

- `test_migrations.py:372–373`: contiguous versions and distinct hash count become001–022/22. The historical `migrations[21]` child test at574 remains21.
- `test_postgres_integration.py:4108`: suffix list after historical012; `:4399`: suffix after008 and current readiness schema; `:5094`: fresh runtime schema version.
- `test_execution_persistence_postgres.py:1659,1890,2000,5793`: append actual022 migration tuple to historical014→current upgrade lists.
- Same file`:1677,1905,2025,5854`: current max-version assertions become22; `:1832`: historical014 upgrade version list gains22; `:5722–5723`: fresh-cluster packaged-resource guard becomes001–022.
- Unrelated capacity references to21 in `test_postgres_integration.py:2858,2876,4551` must remain unchanged.

The #166 worktree was inspected read-only, and its verified commit is now this branch's baseline. Its `create_populated_current_prefix` (`test_execution_persistence_postgres.py:1849`) dynamically applies `packaged[14:-1]` with real ledger digests and checks `packaged[:-1]`; its upgrade assertion expects exactly `packaged[-1:]`, preserved prior timestamps/data, and empty replay. However `current_prefix_snapshot` at1885 currently snapshots only `semantic_bind_repair_child(character,text)`, and behavior transitions at1876/1935 are conditional on latest=021. For the new tree with022, extend the target metadata/behavior checks to **semantic_plan_repair** and preserve historical021 evidence. Otherwise its dynamic ledger test can pass while checking the wrong function's unchanged metadata. Its new helper/test are available to the sole #163 writer after the coordinator's fast-forward.

## Handoff facts

Implementation belongs to the route's sole `data_implementer`. The bounded design packet is consistent with the inspected SQL/Python sources and requires no product-path scope expansion. This change lives in **`factory/`**; the deployed Trust CI service and policy remain separate.

For shared memory, record that the closed rejection channel belongs outside lifecycle payloads, both idempotency branches must be mapped, deadline exhaustion remains persisted escalation, and the newest-resource migration test must inspect the function actually replaced. Those facts prevent repeating the #155 diagnosis and false migration evidence. The coordinator owns `decisions.md` and bootstrap updates, so this agent writes only this selected report.
