# F successor preparation report — Task1

Status: prepared source handoff only; acceptance pending. Branch `feat/v211-f-after-core`; worktree `.worktrees/v211-f-evidence`; route `c34622ec1ccf`; sole writer data_implementer. Starting retained F HEAD `e3509dcf40e9b67e1ee6b51fbbaa208d5ba26a69` remains preserved on `feat/v211-durable-evidence`. Frozen predecessor `c50e083cc7980c3bb049af0f9382721a0f957417` is a provisional preparation parent, not accepted main. Original route comparison base `63799f8760d3a55028d83ab5ff0116ececf8f7d1` remains unchanged. Product check snapshot: rebased HEAD `09ebd352d3476a0abd9ca60ae7f91e428616b4f1` plus the final helper/tests diff. The subsequent prepared commit includes these source bytes, scope mapping, local gate refresh and this report; the controller must record its final exact HEAD independently.

## Resources and dependencies

CPU snapshot preceded every repository/route/task inspection. Host14physical/28online logical, default22allowed CPUs; actual cgroup ancestors impose no finite quota and effective cpuset0-27. Verified child16-19 exposes4; focused tests one worker, at most two bounded diagnostics concurrently. Full verifier and sole PostgreSQL fixture stay controller-owned; no agents, database fixture, secrets, deployed systems or external writes used. Existing six route-selected analyses were read and retained, not repeated. Fetch completed. See successor-startup-capacity.md for commands, timestamp and bounds.

## Additive implementation and fresh RED/GREEN

Restacked the two original nonmerge F commits onto frozen c50 (e27792e69 and09ebd352d), retained both decisions/mistakes histories and core preflight/fitness/source-state/heartbeat-watchdog installer changes. The two large reset callers are now byte-identical to c50. Test-only helper selects only schema025/026; its default uses the existing cursor's bounded `SELECT version FROM factory.schema_migrations ORDER BY version DESC LIMIT 1`. Existing migration contract declares version `integer PRIMARY KEY`; exact-int validation rejects boolean/string/float and absent/unsupported installed versions before TRUNCATE. No schema-discovery cleanup or CASCADE. Explicit025 retains its exact original reset statement, SHA256a67d8339b86d2af81a72d3f8e953cf29ce8bb81067f1cefe4921555a0c075de9. Explicit026 adds exactly the six immutable M7 tables, with single reset statement and unchanged caller transaction/suffix controls. test_postgres_integration remains its distinct actual binding.

Fresh RED1: new026 inventory/version control failed with unexpected schema_version keyword before dispatch existed. Fresh RED2: installed-version default control failed because the prior default chose025 without reading the actual ledger. GREEN proves025/026 installed and explicit dispatch, immutable six-table inventory, unknown/type-confused refusal, both real wrappers' suffix/observation behavior, original SQL exception propagation and rollback both on version-read and reset faults. No current PostgreSQL behavior is claimed from recording-cursor controls.

All checks were `taskset -c 16-19`, with `PYTHONPATH=factory/src:.` for unittest:
- `python3 -m unittest factory.tests.test_postgres_fixture_reset.FixtureResetTests factory.tests.test_m7_integrity factory.tests.test_shadow_lookup factory.tests.test_migrations tests.test_architecture_model tests.test_installer factory.tests.test_execution_persistence_postgres.RecoveryContentionAcceptanceTests factory.tests.test_landing_api factory.tests.test_semantic_bridge factory.tests.test_semantic_contracts -q`:210tests,28.017s,OK.
- `ruff check factory/tests/postgres_fixture_reset.py factory/tests/test_postgres_fixture_reset.py`:all checks passed. Earlier scoped caller lint passed too; final callers are unchanged.
- `python3 scripts/grok_architecture.py drift --json`:OK,no findings. `diagram --check --json`:OK,no mismatches,all five views unchanged.
- `git diff --exit-code c50e083... -- factory/tests/postgres_restart_probe.py factory/tests/test_execution_persistence_postgres.py`:exit0.
- `git diff --exit-code e3509dcf... -- factory/src/adaptive_factory/resources`:exit0,all001-026 unchanged. 026SHA256a8f68bcabe2b7b4e28ad7f974b48f9eb9bce7152aee0e159b4b6fb5bbf0fb5ca.
- `git diff --check`:clean.

## Fitness distinction and retained failure evidence

Focused commands: `python3 scripts/grok_architecture.py fitness --base <base> --worktree --pre-risk red --json`, same CPU allocation. Whole-file policy, limits and accounting unchanged.
- Initial hypothetical c50 projection with explicit keywords in large callers FAILED: governed1480096>1300000bytes;Factory1334005>1150000;tests948341>800000bytes/AST775>600. That failure was preserved and repaired by restoring callers exactly and moving actual installed-state dispatch into helper.
- Final hypothetical c50 projection PASS,exit0,all fitness categories; diff_digest e9435e78f4fc1d8b2582ec1d4a6368a2e9e0a4b3eda4b34455208cb5c4f5580f. It proves preparation against that frozen predecessor only.
- Final actual original63799f full-range fitness FAIL,exit1:governedAST6356>5000/2190246>1300000bytes;Factory1337838>1150000bytes;testsAST784>600/952174>800000bytes. diff_digest e302346a7d1eed7e9b633e376e627e2b170816577a18f4cd7f7b2ed384299f39. This is the actual unchanged route range, not an accepted-base successor gate.

Structured evidence: successor-fitness-evidence.json retains the initial failure and final provisional report plus an explicitly labelled earlier actual diagnostic; successor-final-actual-fitness.json contains the final actual original-range diagnostic. Diagnostics precede report/evidence persistence and are not fingerprint receipts for the later commit. A truncated first actual output was not used; full diagnostic was recaptured. No skip/pass/completion or external-approval claim follows from these focused results.

## Scope, delivery and remaining obligations

Five bound scope files add only the approved fixture decomposition/version mapping and pending acceptance distinction. Final digest `15ece4f5073588754116f3a73bca59c7c21e20709c2431970b4f0c08114063f1` was sent before commit for transparent local scope/migration-plan gate refresh. Earlier55daaaa5mapping and gates were explicitly superseded. These are workflow approvals of authorized source preparation, not live mutation or external security approval.

Durable integration-addendum.md and the release-wide release-scope-ledger retain original F CR001/TR001/SEC001/SEC002 and F1-7. Controller must obtain actual accepted core merge, restack to that agreed base, rerun exact-base scope selector/full verifier, actual025→026 upgrade/mixed fixtures/restart/replay/Unicode/role/privilege/index/bounds/drift controls, all five independent reviews with private mutation probes, final persisted evidence/receipts and exact-head App Trust CI/required approvals. No database tests, full verifier or reviews were executed under this assignment. G and artifact/release remain separate. Source rollback uses PR revert; additive durable rows are retained with forward recovery. Writes stop at the prepared commit and handoff.

Controller confirmed final local scope/migration-plan refresh against15ece4f5. Controller also reported core full verifier exit1: actual factory-postgres-exit passed, but unit/coverage, source-drift runtime probe and synthetic test-secret scan failed. This is controller-reported predecessor status, not writer-executed evidence; core acceptance is still pending and no F review or database/full verification slot is granted.

## Current provisional restack followup

Supersedes the provisional predecessor only: original F e3509dcf and prepared08c7f6ea392814f951a3dc7c31b939d31c888146 are preserved; current F source was restacked onto frozen Core e8a4cd02cdc8ae047c3d8e2b88146856fc5c17c0 with tested source HEAD de72b5514b3e2f3fcee948dffdb62d15863cbe77. Scope digest15ece4f5 and original agreed route base63799f are unchanged. Both huge callers and all.grok-stack bytes match exact Core; UUID and.txt fixes retained. Focused79tests pass and actual whole-file fitness against exact provisional e8a4 passes. Core acceptance is still pending. See durable evidence/successor-restack-e8a4.md for exact commands/identities; previous reports remain historical and supply no accepted-base completion authority.
