# Integration architect backlog analysis

Date: 2026-09-21. Route `d54d3afd1c92`; analysis only, no product changes.
Repository: `/home/pall/grok-projects/adaptive-grok-build-issues-wave`.
Inspected HEAD: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` (frozen PR #170 candidate), based on fetched main `90078959ff816068af374ad42f4bb80fdbaec866`. Coordinator confirmed remote refs were fetched. Source issue snapshot: `/home/pall/.cache/agbp-run/issues-wave-20260921/factory_contracts.json`.

Read bootstrap, state, AGENTS, route, and adaptive-delivery/task-triage/api-event-change skills. Exactly this assigned analysis role; no extra agents, commits, provider/production calls, full verifier, Docker, or external writes. The six issues have no dedicated open implementation PR in the supplied open-PR snapshot; #163 builds on the sibling repair implementation in PR #170. Git diff shows no main-to-HEAD changes to either architecture module or the artifact inventory implementation/tests, so those findings apply to main too.

## Priority and disposition

| Issue | Disposition | Next bounded action | Risk / dependency |
|---|---|---|---|
| #148 | Current, directly reproduced | Deduplicate emitted unattributed details across inventories and cap per referrer with a deterministic overflow summary; focused tests | Low implementation risk; preserve head abort/base degradation and scope; coordinate schema test edits with #147/#137 |
| #147 | Current, directly reproduced | Path-first comparator resolution for declared paths, named collision validation if required by final scope, regression arms | High consequence: false compatibility certification; merged #133/#149 are starting point, PR #137 touches comparator nearby |
| #163 | Current, 15 refusal sites confirmed | Separate repair-plan rejection channel, closed parser, additive migration after 021 | Medium/high: SECURITY DEFINER SQL and persisted migrations; stack after #170, coordinate #166 current-prefix test |
| #61 | Already fixed in source | Closure evidence; no implementation needed | Production guard landed #77; no deployed-site state claimed |
| #56 | Historical regression fixed in current tested scope | Closure evidence linking focused result; keep gate omission tracked separately | Original #49 obsolete; coverage/merge-gate gap remains under #51/#63 |
| #63 | Partly fixed; current residual | Measure module coverage with pinned parser, define/enforce landing coverage lane, add only measured missing boundary tests | Cross-cutting verification; deployed Trust CI adoption is external; do not re-add existing tests |

## #148: unbounded duplicate unattributed-reference diagnostics

Source: `.grok-stack/adaptive_grok/architecture_fitness.py:898-910` emits every accumulated detail; `:928` caps only carriers within one detail; `:957-969` appends each repeated reference and extends the referrer list; `:995-999` accumulates both inventory passes.

Executed a pure in-memory probe using real `ContractRecord` and `_contract_dependency_closure`. Both inventories contained `referrer.json`, a real `dir/target.json` path, and two distinct claimants declaring `$id=dir/target.json`. One reference yielded **2 findings, 1 unique string, 228 bytes**; 1,000 references yielded **2,000 findings, 1 unique string, 228,000 detail bytes**. Presence of the declared path keeps this case nonfatal and demonstrates duplicate aggregation; no repository/model edits or network were required.

Smallest safe scope is presentation in `_contract_compatibility`: for each in-scope identity sort unique detail strings, emit a named maximum, then one `(+N more unattributed references)` summary. Keep full edge traversal and its head-side abort before that transformation. This avoids choosing base versus head authority and leaves comparator reason tuples untouched. If memory boundedness during collection is desired, explicitly widen scope and define exact unique omitted-count semantics; output bounding alone does not bound temporary lists.

Tests: one repeated collision in both inventories emits one detail; more distinct collision details than the limit emit limit+summary; deterministic ordering and exact omitted unique count; unrelated referrers remain excluded; head-only shared-ID without path still aborts; base-only ambiguity remains nonfatal. Existing regression neighborhoods are `tests/test_architecture_fitness.py:4623-4719,4827-4881`. No migrations/contracts/policy/rules changes. Independent of #163 and landing work; coordinate shared test ownership with #147 and open PR #137. Rollback is a byte-local code/test revert.

## #147: declared ID shadows real path

Source: `.grok-stack/adaptive_grok/architecture.py:1283-1289` explicitly documents the preserved shadowing defect; `:1403-1409` passes `SCHEMA_REFERENCE_ID_FIRST` from `_SchemaResolver.resolve`. Shared helper supports `SCHEMA_REFERENCE_PATH_FIRST` already. Closure intentionally unions both lookup identities at `architecture_fitness.py:1083-1092`; existing tests at `tests/test_architecture_fitness.py:4321-4410` encode this compatibility-dependent behavior.

Executed the issue's exact shape on current code: real target minLength 1→9, unchanged referrer with `$ref=dir/target.json`, unchanged claimant `$id=dir/target.json` whose minLength is 9. With claimant: `CompatibilityResult(status='compatible', reasons=())`. Control without claimant: `CompatibilityResult(status='incompatible', reasons=('narrowed_constraint',))`. This is a current comparator false certification, not a deployed contract incident.

Minimal scope: resolve an actually declared path first, retain declared-ID lookup where no path exists; reject authoring-time ID/path disagreement with a named error if that part is included in the approved scope. Preserve pure URN/HTTPS IDs, fragment behavior, bounds and fail-closed duplicate IDs when the ID route is needed. Do not mechanically remove closure edges until tests establish correspondence with the revised comparator; current conservative union cannot miss a dependency. Review/update tests that explicitly pin old ID-first shadow behavior.

Tests: reproducer plus control, same-target path/ID agreement, different claimant, nested relative path, pure URN and HTTPS ID, ambiguous ID-only references, graph identity and closure. Existing ID ambiguity test: `tests/test_architecture_model.py:2997-3011`. Recheck shipped inventory after any validation rule; do not change contracts to make tests pass. Dependencies: #133 merged as `d871ea6d`, #146 closure fix merged through **PR #149** as `b51b1175`; both are already beneath the observed main associated with PR #151. Open PR #137 (`fix/schema-metadata-contract-compatibility`) touches the same subsystem and should be reconciled before independent deliveries. No runtime, migration, or policy change is needed. Full exact-head verification and external Trust CI remain delivery requirements, not performed here.

## #163: semantic plan refusals misreported as stored corruption

Source: `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql:1527-2044`; static extraction of `semantic_plan_repair` counted **13 `RETURN NULL` + 2 `ELSE NULL`** sites. `factory/src/adaptive_factory/store.py:685-697` feeds its response directly to `RepairLifecycleResult.from_dict` and translates TypeError/ValueError to `stored semantic repair result is corrupt` before binding checks. No `repair_plan_rejection` channel exists in current source.

PR #170 includes `021_semantic_repair_child_rejection_reasons.sql`, replacing only `semantic_bind_repair_child`; it does not fix planning. Reuse its strict one-key closed-vocabulary reader pattern from `semantic_repair.py:52-79`, including the later #155 correction that legacy NULL refusals must not reach the success parser. Implement the plan-specific channel before `RepairLifecycleResult.from_dict`; retain all subject/verdict/cycle/child binding checks and success schema. Malformed stored documents must retain their own corruption handling. Taxonomy needs an explicit per-guard map, including idempotency conflicts and write exceptions, without exposing unbounded database text.

Migration must be a **new version after 021**, normally 022 if still free at implementation time; never modify shipped 018 or overwrite PR #170's 021. Preserve SECURITY DEFINER signature/search_path, ownership/ACL and all original guard predicates. The refusal envelope changes no successful persisted payload contract. No production application of migration is authorized by this research.

Tests: offline SQL/Python vocabulary equality and normalized predicate/body equivalence to superseded function; closed-parser malformed/unknown/success arms; mocked store NULL and named rejection versus genuinely corrupt result; unchanged binding mismatch checks; PostgreSQL isolated rejection causes, successful/idempotent replay, conflicting key, constraint exception, transaction rollback, current-prefix migration and ACL/OID preservation. Coordinate with #166's separate incremental-migration test so it does not freeze latest=021. Real PostgreSQL cases were not executed in this Docker-free analysis. Risk is higher than #148: roughly 500 lines of privileged SQL must remain behaviorally equivalent except diagnostics. Start after #170 has a stable delivery/base, or explicitly stack a separately routed branch on it.

## #61: internal documentation deployment

Fixed by production hardening commit `1a8c8917` / PR #77. `factory/src/adaptive_factory/landing_artifact.py:69-90` defines `PROHIBITED_DEPLOY_MEMBERS` and rejects any forbidden path component with a named `prohibited_deploy_member` error. `deploy_members_for_source` guards every supported epoch (`:99-109`); import-time current inventory check is at `:124`. Neither SERVER-SETUP.md nor ASSETS.md is in DEPLOY_MEMBERS. Nested `docs/...`/`research/...` is also refused.

`factory/tests/test_landing_artifact.py:292-313` checks production/test denylist equality, each epoch's disjointness, and injected top-level/nested prohibited members. This module passed in the focused run below. The proposed extra architecture fitness rule is not present as a dedicated invariant, but the underlying production leak and requested production guard are fixed. Treat adding a second enforcement mechanism as a separately justified improvement, not evidence the original bug persists. Next action is a closure proposal referencing #77 and current test result; no issue write performed.

## #56: original PR #49's 41 test failures

Historical baseline report, not current behavior. L5 landed as split/assembled source through #75 (`eb9df64b`), with later #77/#83 and runtime fixes. All nine modules enumerated by the issue were included in the focused run and passed on current HEAD. No product diff is warranted just to resolve this old failure count. No claim that the full factory/PostgreSQL suite passed is made.

The related gating omission remains current: `.grok-stack/adaptive_grok/verification.py:990-1002` still selects only contracts/state/migrations/service for factory-unit; `:1007-1014` skips factory-postgres-exit with repository-sandbox capability. Track that once under the relevant #51/#63 gate work, rather than duplicate the historical regression implementation. Next action is closure evidence for #56 plus an explicit link to the remaining gate task.

## #63: production landing execution coverage

The headline's zero-execution/no-test-file state is obsolete. Current tests exist for all six named areas: `test_landing_backup`, `test_landing_publication_cli`, `test_landing_sse`, `test_landing_host`, `test_landing_server`, `test_landing_pdf_worker`. They cover backup restore refusal/recovery, publication tamper and symlink/hardlink/grant/lineage checks, reconciliation without replay, bounded/terminal SSE frames, host ownership/cleanup, and real isolated PDF worker execution. #77 added real PDF-worker tests; #83 (`31725f12`) decoupled backup tests from web-stack imports. The production publication CLI no longer imports adaptive_grok. Do not infer a current architecture failure merely from the old branch's import list.

Current residual: `.coveragerc` measures only `.grok-stack/adaptive_grok` and scripts, and there is no landing per-module floor; verification's factory-unit omission described above persists. This analysis did not measure current module percentages, so it does not claim full coverage. Five actual-parser PDF tests skipped here because pinned pypdf 6.18.1 was unavailable to the isolated child; parser-unavailable execution passed. The real-worker test file still lacks an encrypted-PDF execution case although production worker has `reader.is_encrypted`; intake's synthetic encrypted marker test is not equivalent coverage. Measure other requested destructive/recovery boundaries before deciding whether more tests are absent.

Minimal next slice: a separately routed offline coverage lane with explicit landing module inventory, deterministic pinned test environment and a measured floor; targeted encrypted PDF worker regression and any additional measured missing boundaries. Decide subprocess coverage collection explicitly because the worker runs `python -B -I` with an isolated environment; a parent-only coverage number is not worker-body execution evidence. Split local repository test integration from external Trust CI image/policy adoption. The latter is outside PR authority and requires operator-managed rollout; no deployed policy change here. This is a medium/high verification project, not a small independent bugfix like #148.

## Executed focused evidence

Command (run once):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack:factory/src:delivery/src python3 -m unittest factory.tests.test_landing_artifact factory.tests.test_landing_live_executors factory.tests.test_landing_coordinator factory.tests.test_landing_api factory.tests.test_landing_renderer factory.tests.test_server factory.tests.test_landing_runtime factory.tests.test_landing_live factory.tests.test_landing_sqlite_store factory.tests.test_landing_host factory.tests.test_landing_sse factory.tests.test_landing_server factory.tests.test_landing_publication_cli factory.tests.test_landing_backup factory.tests.test_landing_pdf_worker
```

Result: `Ran 237 tests in 18.929s`, `OK (skipped=5)`, exit 0. The skips are the five `PdfWorkerWithPinnedParser` cases. Tests use disposable local fixtures/synthetic grants; no production credentials or provider calls were used. This is focused analysis evidence, not full verification, review approval, or merge authority.

Reusable finding for coordinator's shared memory: backlog issue titles describe historical heads; pairing exact-head probes with delivered commit ancestry prevented reopening #61/#56 and narrowed #63 to genuine remaining coverage work. The coordinator owns shared decisions.md to avoid parallel file edits.
