# Integration analysis — prepared factory and tooling repairs

Role: selected `integration_architect`. Route inspected: `8b2ee0533ba5`. Date: 2026-09-21. This is pre-implementation analysis, not a review receipt or a claim of integrated verification.

## Decision and evidence boundary

The candidates can be integrated without changing their prepared behavior, after correcting one omitted source file. The original eighteen-path manifest was incomplete: issue165 also changes `.grok/hooks/stop_gate.py`. Root accepted the finding, preserved the original manifest, and expanded the current manifest and requirements to **nineteen** exact paths. The ninth issue165 blob has SHA-256 `7be3f2be3fb9ea1e581344388a40da84c3a092945e3fb1a51a024847ad0bf48b` at `163847842ccddacd6f179c7a3ea082765530bb84`. No new source implementation is needed to correct that omission.

The original omission mattered behaviorally: the PR173 hook returns immediately when a route has no receipt obligations and otherwise checks only receipts before marking a route completed. Candidate165's tests `test_stop_warns_on_incomplete_package_even_without_receipt_obligations` and `test_stop_does_not_hide_incomplete_package_behind_current_receipts` require the new diagnostic hook. An exact import of only the original eighteen paths would preserve neither expectation. This is a static finding; no reproduction was executed during this analysis.

I read the entrypoints, contract, route, brief, requirements and candidate manifest; compared candidate source against PR173; inspected producers, consumers and relevant tests; and hashed all nineteen declared blobs using `git show <head>:<path> | sha256sum`. Every result matched the corrected manifest. Frozen inputs were:

| Input | Exact commit | Relevant scope |
| --- | --- | --- |
| PR173 source | `23984e55560c6d559a46445061f10331ca05bcf9` | Reviewed router, fingerprint, schema, installer and current-prefix fixes |
| Issue165 | `163847842ccddacd6f179c7a3ea082765530bb84` | Nine diagnostic, lifecycle, hook, CLI, test and guide blobs |
| Issue163 | `d80c5c8d8e5afe938d195401715daf5e69192a81` | Seven store, parser, additive SQL and test blobs |
| Issues62/118 source subset | `08dd467d0dc9c173af01f3b47876a9a3fa1ca639` | Three runner, quota helper and test blobs |

Observed local source HEAD remained PR173's exact head, while the inspected route and fetched-main observation still named `839d3aa26bc90417424d814ee48d8b5cd3be367e`. No source import, tests, lint, compilation, Docker, module import probes, receipts or external operations were performed. Root coordinates fetching and delivery; external CI owns the execution lane.

## Interface compatibility

### Issue165 with PR173 router, fingerprint and receipts

`change.py` adds initial/first-implementation observations and explicit evidence accounting. `package_status.py` is their bounded reader and the shared producer of findings for `grok_status.py`, the canonical Stop hook and the review preflight. `state.py` changes three read-side path helpers so merely reading absent route/change/agent state does not create runtime directories. Existing write callers retain their explicit directory creation and atomic JSON behavior.

The status JSON retains `route`, `change`, `agents` and `evidence_gaps`; package completeness and worktree observations are additive. Unsafe selected package input prevents the status/hook/review path from handing it to less restrictive legacy receipt readers. A passing review is refused for package errors before receipt creation; a failed review can still account for an incomplete package when its binding is safe. Stop remains nonblocking, but visible package warnings prevent its old unconditional completed transition. The hook must be imported together with the other eight issue165 paths.

PR173's router remains the route authority. Candidate165 neither imports an older router nor hardcodes a narrower review vocabulary: its accounting reads `RECEIPT_KINDS` from unchanged `receipts.py`, and its specification validation uses the shared `spec.py` and PR173's updated schema. The issue165 candidate changes none of `receipts.py`, `spec.py`, `architecture_diff.py` or `verification.py` relative to PR173. The import graph is compatible: lifecycle code imports diagnostics, diagnostics imports receipt kinds/spec helpers, and those dependencies do not import lifecycle code back.

The diagnostic Git snapshot and receipt fingerprint have deliberately different purposes. Diagnostics exclude package paperwork when deciding whether product work is dirty and use the immutable initial checkpoint as a named diagnostic base, falling back only for legacy packages without that checkpoint. PR173's `util.tree_fingerprint` still binds HEAD and relevant dirty bytes, including paperwork. A clean diagnostic snapshot or a `complete` package does not validate receipts. Raw filesystem names remain ordinary UTF-8 strings or distinct tagged hexadecimal identities; PR173's byte-preserving fingerprint support does not justify weakening strict canonical JSON parsing or collapsing names.

`not_run` accounts for unfinished obligations. A recorded failure accounts for a run. Neither establishes successful execution, satisfies a required receipt, nor grants merge authority. Existing receipt envelopes, delegated grants, route risk selection and external approval boundaries remain unchanged.

Lifecycle state is canonical and is written before the README mirror. Mirror failure must remain visible and retryable; publication across the two files is not atomic. All checkpoint, accounting, report and handoff writes must precede the final fingerprint-bound verifier/receipts. The combined package was created before this importer exists: do not fabricate an initial checkpoint or reinterpret its route base after import. Explicit future lifecycle commands and the existing legacy diagnostics handle that situation.

### Runner selection and its callers

`python_test_runner.py` gains one private standard-library helper, `_cpu_capacity.py`; importing it does not read cgroup files. Linux membership/mount/quota reads occur only for opted-in `auto`. Explicit worker counts, no opt-in and child-run paths avoid those reads. Auto intersects affinity/CPU availability, the existing ceiling and all applicable visible finite quotas; malformed, ambiguous, unreadable or bounded-out Linux evidence becomes one worker. A known unlimited visible hierarchy remains distinguishable from unknown capacity. Hidden ancestors and PID headroom remain unproven.

Both `run_core_tests` and `run_trust_tests` already call `select_engine`. The added cleanup-capability predicate makes unsupported positive requests choose `workers=0`, `engine=unittest-degraded` before process launch. This preserves the existing serial command, process execution/cleanup implementation, measured coverage handling and strict pins for the engine actually selected. There is no retry as serial after an actual parallel failure. `CoreTestRun`/`ProcessResult` shapes and the verifier's result consumers do not change. The Trust test CLI reports actual requested/effective workers and engine; changing this shared source is not a change to deployed Trust CI worker policy or images.

The implementation does not add dependencies, change `.grok-test-runner.json`'s schema or default, modify the verifier, alter receipt semantics or change coverage policy. Empty-collection regression tests preserve the behavior actually observed on measured interpreters; they are not evidence of a newly repaired zero-test defect or all-version Python compatibility. Native Windows execution has not been established by the POSIX-host capability seam tests.

### Issue163 SQL producer, Python adapter and public consumers

The only new SQL resource is `022_semantic_repair_plan_rejection_reasons.sql`. It replaces the existing four-argument `factory.semantic_plan_repair(char,char,text,uuid)` function with the same JSONB return type, `SECURITY DEFINER`, fixed `search_path`, public revocation and coordinator execution grant. Existing resources001–021 are not imported or rewritten. There is no table, index, external event or successful lifecycle contract migration hidden in the integration.

The declared change is the internal refusal value: SQL now emits the exact single-key `repair_plan_rejection` envelope for existing rejected branches. The parser accepts only that channel and the closed reason vocabulary, maps unknown reason values to `planning_rejected`, and lets extra-key/wrong-channel/malformed documents reach the existing corruption path. Pre022 SQL NULL remains an explicit `store_returned_null` refusal. Successful `RepairLifecycleResult` structure and binding checks are unchanged; a refusal cannot become a success or escalation merely by containing familiar fields.

`PostgresSemanticCoordinatorStore.request_repair` classifies returned values after leaving the transaction. That ordering preserves committed escalation/command-result writes and SQL exception-subtransaction behavior. JSON decoding failure stays stored-result corruption. The request contract, idempotency key/digest, capability-specific connection and five-second lock/statement limits remain intact. Existing service authorization checks still require the coordinator operator and repository scope. The API's `StoreError` handler still emits its generic HTTP409 `store_conflict` response; source delivery does not introduce a new HTTP error contract or expose arbitrary database text.

Source compatibility does not imply rolling deployment compatibility. Runtime readiness requires the installed database version to equal the number of packaged migrations. A022-capable binary against021, or an older binary against022, can be not-ready. Any later installation needs coordinated application/database rollout, bounded migration checks and forward recovery. This branch performs no database operation and provides no live rollout proof.

### PR173 overlap and external validator boundary

The three candidates are disjoint from one another. The one application/test overlap with PR173's imported scope is `factory/tests/test_execution_persistence_postgres.py`. Candidate163 intentionally extends PR173's prefix fixture to inspect both child and plan functions, retains a named historical020→021 proof using actual resources001–021, and adds the current021→022 proof. Do not restore the older PR173 blob over candidate163 or let migration022 silently replace the historical upgrade test. Fresh PostgreSQL execution must confirm OID/owner/ACL/search-path/rows/ledger preservation and replay for both suffixes.

The local schema now admits seven receipt kinds; the checked-in Trust CI runner and example holdout still list five. This integration does not repair or deploy that separate trusted-validator compatibility successor. Mandatory `data_review` remains required locally. Acceptance criteria can reference concrete tests and supported receipt evidence without claiming the external validator understands the additional receipt kinds. Do not import Trust CI source158 or modify policy/holdout to make this branch pass.

## Required combined proof

1. Wait for actual PR173 delivery. Fetch its actual merged commit and verify its tree against the frozen PR173 tree before importing the corrected nineteen blobs. Hash each imported blob and inventory all remaining changed paths; unrelated candidate-era router, installer, fingerprint, schema and handoff files must not replace PR173's versions.
2. Root accepted the other analysts' old-base budget finding: comparing the whole stacked delivery to839 would include already-delivered PR173 work and exceed the bounded change budget. Generate a legitimate fresh current-main continuation after actual delivery, preserve this route/package and adopt unchanged analyses with exact hashes. Do not hand-edit route base, fitness thresholds, rules or runtime evidence. Recheck the real final ranges; a static budget estimate is not a passing fitness result.
3. After the execution lane is free, run the complete integrated `python3 scripts/grok_verify.py --mode pr` using the authorized runner configuration. Candidate RED/GREEN, earlier full failures, individual passing runs and reviews remain source provenance, not integrated receipts. Record actual discovery, counts, skips, failures and source stability.
4. The integrated suite must cover package status/start/transition/resume/raw-byte identities/mirror recovery/safe reads, both Stop regressions and pass-review refusal before receipt replacement. Retain PR173's router alias/non-alias, schema/receipt vocabulary, ignored-versus-tracked fingerprint and installer regressions against the new lifecycle/status code.
5. Preserve runner quota fixtures for nested v2/v1/hybrid/mount roots/visible parents/fractional/unknown bounds; default-off/explicit/child paths; both core and Trust fallback seams; measured coverage; exact-once collection; wrong pins; real failure propagation; cleanup/timeouts/output limits. Linux host tests and seam simulation must retain their platform/interpreter limits in the report.
6. Execute the actual disposable PostgreSQL suite with022, including every refusal family, successful repair/escalation, malformed/unknown envelopes, replay, competing second lookup, deadline persistence, exception rollback, migration immutability and both historical/current prefix upgrades. The earlier corrected single-case pass must not be presented as a full rerun.
7. Finish all source and durable paperwork before final verification, then obtain every selected independent code/test/security/data/release review and current fingerprint-bound receipts. Resolve package errors with the one selected writer where source is involved. Zero local evidence gaps remain only preflight; exact-head/base App verification and required signed scopes still control merge.

## Truthful delivery and closure

After actual source delivery and its required evidence, the bounded implementation can close **#165, #163 and #118**. Close retained PR135 as superseded only after its successor lands and preserve its history. Root accepted keeping **#62 open** for its separate bounded App Check Run command-output successor; this source subset does not implement that output outcome. It also does not close general CI capacity159, Trust CI child-reaping158, operational qualification, native-Windows qualification or the separate trusted-validator compatibility work.

A successful source PR establishes the diagnostic/adapter/runner behavior exercised by its tests. It does not install a worker image, upgrade a production database, restart a service, alter deployed trust policy or certify live zero-zombie/capacity behavior. The source-only boundary should be explicit in the PR body and issue closure evidence.

Root owns the accepted manifest correction and shared-memory mistake record. The reusable integration lesson is that a disjoint-file candidate manifest must be checked against its actual changed entrypoints: a missing caller can invalidate behavior even when every listed blob is preserved exactly.
