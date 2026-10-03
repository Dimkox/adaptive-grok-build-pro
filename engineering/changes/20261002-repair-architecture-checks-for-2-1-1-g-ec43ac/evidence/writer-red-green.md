# Sole writer focused evidence

Route ec43ac81e712, isolated branch `fix/v211-architecture-contract-fitness`, initial HEAD/base `63799f8760d3a55028d83ab5ff0116ececf8f7d1`. Sole selected integration implementer, CPUs24/25, at most two concurrent test processes, no nested agents or external writes.

Product inventory is exactly `.grok-stack/adaptive_grok/architecture.py`, `.grok-stack/adaptive_grok/architecture_fitness.py`, `tests/test_architecture_model.py`, `tests/test_architecture_fitness.py`. No rules, schemas, deployment, secret, release bytes, database or product runtime changed.

RED command: `taskset -c 24,25 python3 -m unittest tests.test_architecture_fitness.ArchitectureFitnessTests.test_change_separation_admits_bound_trust_ci_metadata tests.test_architecture_model.ArchitectureModelTests.test_openapi_additive_components_preserve_existing_contract_constraints -v`. Before repair: 2 tests in1.116s, failures3. Separation reported real mixing for the bound source/model/API fixture; both empty-to-populated and strict-superset schema additions returned incompatible.

The repair qualifies metadata from already validated paired ArchitectureDiff states. Model envelope, all node properties except repository_paths, existing identities/roles and owner properties remain unchanged. Exact changed Trust CI Python source may be registered only without expanding an existing prefix owner; deletion/reassignment refuses except the explicitly approved store.py PostgreSQL-client correction from the existing PostgreSQL datastore node to the existing API service node. Contract qualification requires the exact unchanged registered Trust CI OpenAPI identity/role/compatibility and unchanged Trust CI API owner binding. Classified paths appear in the applicability predicate. Compatibility independently runs; no path-prefix blanket exemption, aggregate bypass or policy change exists.

OpenAPI comparison now rejects only removed base schema component names at the component inventory boundary. Every shared component retains bidirectional comparison; complete schema/ref preflight, existing operation/authentication checks, exact/versioned semantics and budgets are unchanged.

Initial GREEN targeted command additionally selected metadata negative controls and existing real mixing regression: 4 tests in11.959s, OK. Expanded negative controls also passed; an incorrect test assumption about supported anyOf was corrected as recorded in package mistakes.md.

Final focused checks ran concurrently on individually pinned CPUs with a 240s timeout each:

`timeout 240 taskset -c 24 python3 -m unittest tests.test_architecture_model -q`: 83 tests in2.658s, OK, exit0.

`timeout 240 taskset -c 25 python3 -m unittest tests.test_architecture_fitness -q`: 133 tests in85.723s, OK, exit0.

Controls cover unknown base, metadata plus local/runtime/checker code, changed node runtime/secrets/owner/edges, unauthorized source reassignment/prefix expansion, rules/schema machinery and unrelated/altered contract bindings. Additive contract controls retain removed/modified unused old schemas, dangling/cyclic refs, unsupported/malformed additions, bounded work, authentication, existing operations, exact and same-version versioned-break rejection.

Read-only actual-G illustration used `diff_architecture(Path.cwd(), base_sha="63799f8760d3a55028d83ab5ff0116ececf8f7d1", head_sha="3423e7d5d6f8bef96e54cbeb698c49462cb01583")`, then `_change_separation(diff._head_state.snapshot, diff)` and `compare_contracts` with both complete inventories. Actual-G separation PASS, qualified paths exactly `architecture/system.yaml` and `engineering/contracts/openapi/trust-ci.v1.json`; bidirectional OpenAPI compatible. Adding `.grok-stack/adaptive_grok/architecture_fitness.py` to that exact changed inventory made separation FAIL. This illustrates frozen G compatibility only; it is neither G's fresh full verification nor merge authority.

`git diff --check` passed. Final aggregate must preserve D's earlier architecture.py parsing/preflight changes, run fresh full PR verification, then independent selected reviews and final receipts. Full Core/factory profiles were deliberately not duplicated on this isolated contour under the user's approved aggregation plan. No local completion or external Trust CI pass is claimed; final delivery is combined A-F/H/HB source PR followed by separate G source PR.
