Read-only aggregate repo analysis, route ffb3d81e031f. Analysis brief read first after startup measurement.

Base and aggregate HEAD: 63799f8760d3a55028d83ab5ff0116ececf8f7d1. Aggregate has only its untracked change package. A/B/C/D/E/HB observed clean; F/H are active dirty candidates and their inventories below are provisional. No candidate writes, tests, caches, generated artifacts, subagents, secrets or external operations.

Exact committed sources:
A 0d22521f14eb4e45aa6869aee2258e6e61379722
B cb83a0e49fc5ba5e55144137f3d59e5aed9ac62b
C 9b257246d56e4c65d268a1dd9efadd707f4298fd
D 4293a77939c9c637de486bd6066167c80b9284b2
E d46ab620b7b29a1d675ac41b2f2902c9053b16e8
F 7bc5eba38329e2e9ae5a2e5409c7f28597c4e541 (repair not committed)
H 63799f8760d3a55028d83ab5ff0116ececf8f7d1 (repair not committed)
HB dc4062bcbc1e1da95cfe07077fc9cfbf273e0312
G 3423e7d5d6f8bef96e54cbeb698c49462cb01583 excluded, reserved for second source PR.

Committed executable inventory relative to exact base:
A: .grok-stack/adaptive_grok/{python_test_runner,receipts,verification}.py; scripts/grok_verify.py; tests/test_verifier_recovery.py.
B: .grok-stack/adaptive_grok/router.py; tests/test_repo_router.py.
C: .grok-stack/adaptive_grok/repo.py; tests/test_repo_language_disclosure.py.
D: .grok-stack/adaptive_grok/{architecture,doctor,verification}.py; tests/test_architecture_model_preflight.py.
E: .grok-stack/adaptive_grok/{architecture_diff,governance}.py; scripts/grok_governance.py; tests/test_governance.py.
F: factory/contracts/jsonschema/m7-durable-lookup.v1.schema.json; factory/src/adaptive_factory/{admin,m7_preflight,shadow_lookup,shadow_sources,store}.py; factory/src/adaptive_factory/resources/026_m7_durable_evidence.sql; factory/tests/{m7_postgres_restart_probe,run_disposable_exit,test_landing_api,test_m7_integrity,test_migrations,test_postgres_integration,test_semantic_bridge,test_semantic_contracts,test_shadow_lookup,test_shadow_lookup_postgres}.py; scripts/install_into.py; tests/test_installer.py.
HB: .grok-stack/adaptive_grok/{_policy_legacy,agent_lifecycle,state}.py; .grok-stack/config/managed.json; .grok/agents/general_implementer.{md,toml}; .grok/hooks/{_lib,post_tool_use,pre_tool_use,subagent_start,subagent_stop}.py; scripts/{grok_agent,grok_status,install_into}.py; tests/{test_agent_lifecycle,test_installer,test_policy}.py.
Each source also carries a separate engineering/changes package. Shared prose overlaps: root decisions.md A/D/F/HB; mistakes.md A/D/F/HB; HB README.md and hooks README/runbook. Merge prose by preserving source facts, never replacing whole files.

Observed unfinished inventory:
H modifies architecture.py, architecture_fitness.py, tests/test_architecture_fitness.py and tests/test_architecture_model.py, plus untracked package.
F repair modifies architecture/system.yaml, factory/tests/postgres_restart_probe.py, test_execution_persistence_postgres.py, test_shadow_lookup_postgres.py, tests/test_architecture_model.py and source package/root mistakes.md. Package contents changed during observation, consistent with the active writer. Await final committed identities before import.

Overlap/import map:
A+D verification.py is a semantic integration: A moves orchestration to cancellation-aware state/report handling; D adds bounded architecture-input preflight, refusal/receipt behavior and heavy-test skip disclosure. Preserve D preflight in A's current orchestration; do not replace A's file wholesale.
D+H architecture.py: D introduces complete-input preflight/alias binding; H repairs component comparison. Integrate both, retaining D preflight and H comparison.
F+HB scripts/install_into.py adds distinct MANAGED_FILES entries (F M7 test/probe files; HB scripts/grok_agent.py). tests/test_installer.py changes occur in different areas: F managed-file expectations, HB installed watchdog command/runtime-state assertions. Preserve both sets.
F+H tests/test_architecture_model.py: F adds architecture ownership binding test, H additive-schema regressions; preserve both.
F architecture/system.yaml is required binding metadata; import final repair with F.
No committed source inventory above includes trust-ci/** or G's engineering/contracts/openapi/trust-ci.v1.json. Keep G source and metadata out of the first PR.

Minimal source commit boundaries (short names unambiguous in current object store):
A 40f754380 + 0d22521f1; B 547c7b13b + 5f96f392a + cb83a0e49, retaining e1c7a01d3 evidence; C 7399ba0be + 9b257246d; D 59f0a9cd3 + 0de557769 + 4293a7793 evidence; E d710ef6bf plus 306108261/d46ab620b evidence; F b7849b736 plus final repair commit(s); HB a21767af9 + dc4062bcb; H final repair commit(s) pending. Their intermediate merge commits all have exact base63799f876 as second parent. Importing frozen source tips retains base-integration provenance; if selecting nonmerge commits instead, compare resulting source deltas to these frozen tips so merge-resolution bytes are not lost.

Module dependencies:
A verification imports its new runner cancellation/execute APIs and receipt/state bindings, plus architecture/architecture_diff/fitness and unchanged scope selector.
D verification/doctor consume architecture input preflight APIs.
E governance imports architecture, architecture_fitness and architecture_diff; E also changes bounded Git registration/exact SHA handling in architecture_diff.
F m7_preflight imports shadow_lookup; shadow_sources imports shadow_lookup; shadow_lookup imports existing contracts and shadow_contracts; the durable store/admin and migration must travel together.
HB agent_lifecycle imports modified state bindings and util; hooks/policy/CLI/installer must travel with lifecycle.
Recommended bounded assembly order: A/B/C, then D integration, E, frozen F repair, HB installer union, frozen H checker/test union; order cannot replace resolution of named overlaps. Independent final verification/reviews apply to the assembled candidate, not inherited source evidence.

Evidence: exact git rev-parse/status/log/diff-name-only against base, bounded overlap diffs, merge-parent inspection, and import-line rg. No claims of current tests passing. reviewed-tree-modified: no.

Startup 2026-10-03T00:03:01Z: 14 physical/28 logical online CPUs; default22 and affinity0,1,8-27; actual cgroup /user.slice/user-1000.slice/session-2050.scope, ancestor effective cpuset0-27, no finite exposed quota. Child widening probe succeeds28/0-27; assignedCPU0/max1 worker. Private0700 scratch snapshot and identical report:
<local-path>
<local-path>
