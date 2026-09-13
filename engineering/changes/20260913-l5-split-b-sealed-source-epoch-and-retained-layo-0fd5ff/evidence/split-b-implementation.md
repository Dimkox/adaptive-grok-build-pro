# L5 delivery slice B implementation

Route: 0fd5ffd2100f. Worktree: /home/pall/grok-projects/adaptive-grok-build-pro-l5-split-b.
Branch: feat/l5-split-b-source-epoch.
Genuine predecessor and observed pre-commit HEAD: fb582c91cd80c042d26b7467679d27a295a2396b.
Immutable reconstruction source: f31406e970d67f7cd59694da5de88915adb0fa68.

## Implemented selection

Exactly nine existing product/test files changed. Whole frozen renderer/evaluator/artifact modules refresh the sealed source tuple to fde60e040167c10975b00d11f578c4da6763069a / 21817e70e079b772e1f3114a80dfc0320d1ada91, preserve approved analytics/privacy facts, retain the exact two-file write scope and select 22 deployment members. The source-owned ASSETS.md and SERVER-SETUP.md remain outside deployment inventory. Historical 20-member and 19-member layouts are selected only by their exact known SHA/tree tuples; unknown/crossed tuples reject.

Retention contains exactly three approved source-layout changes: import deploy_members_for_source; select membership with the sealed artifact source SHA/tree; validate manifest count from the selected member_names. V1 type, decoder, dispositions and envelope are unchanged. Whole frozen renderer/artifact/API/live/SQLite test fixtures accompany the source change. No architecture/model/schema/package/lock/runtime/HTTP/V2/publication/backup files changed.

The eight whole-file selections match frozen Git blob content exactly. Retention was independently compared byte-for-byte to its actual predecessor after applying only the three named replacements. Exact paths, Git blob IDs and SHA256s are recorded in split-b-source-sha256.json.

## Evidence

Baseline, before any port: 415 Factory tests passed, 143 PostgreSQL-dependent skips, 28 workers, 15.73s. Log: /tmp/agbp-sweep/split-b-factory-baseline.out.

Fixture-first RED: the source-identity regression fails because the old renderer still binds 699010... instead of fde60e... (split-b-epoch-red.out); the new source fixture is rejected with source_active_content before the production port (split-b-analytics-red.out). These are observed expected failures, not inferred failures.

Focused GREEN after implementation: 59 tests passed with 28 workers in 6.55s. The five changed modules plus dependent coordinator/runtime/legacy-executor suites passed. Log: split-b-focused-green.out.

Genuine predecessor fitness: PASS, exact base fb582c91cd80c042d26b7467679d27a295a2396b. All applicable code budgets, change separation, module boundary and production import checks pass without changing limits. Other categories are truthfully not_applicable for this slice. JSON: split-b-fitness.json.

All nine changed Python files pass Ruff (split-b-ruff.out); git diff --check passes. Supplemental local characterization compares prior inventory against the actual predecessor source, confirms 20/19/22 member layouts, rejects crossed/unknown identities and accepts approved analytics (split-b-layout-characterization.out). Reproducible script: split-b-layout-characterization.py. No new coverage percentage was measured.

## Commands

Run from the B worktree with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:factory/src:delivery/src:.grok-stack`:

```sh
taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -n 28 --dist loadfile factory/tests
/tmp/agbp-venv/bin/python -m unittest factory.tests.test_landing_renderer.LandingRendererTests.test_current_source_identity_and_external_stylesheet_contract_are_exact
taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -n 28 --dist loadfile factory/tests/test_landing_renderer.py factory/tests/test_landing_artifact.py factory/tests/test_landing_api.py factory/tests/test_landing_live.py factory/tests/test_landing_sqlite_store.py factory/tests/test_landing_coordinator.py factory/tests/test_landing_runtime.py factory/tests/test_landing_live_executors.py
/tmp/agbp-venv/bin/python scripts/grok_architecture.py fitness --base fb582c91cd80c042d26b7467679d27a295a2396b --worktree --pre-risk yellow --json
/tmp/agbp-venv/bin/python /tmp/agbp-sweep/split-b-layout-characterization.py
```

The first command is the pre-port baseline; the second is the observed pre-port RED. Final full verification and independent reviews belong to root and remain required. Historical monolith or slice-A verification is not B evidence.

## Limits and handoff

B performs source reconstruction only: no provider calls, credentials/approval reads, external writes, installation, activation, migration or commits. Matching retained artifact identities must be preserved during rollback; use a matching old source epoch/layout or forward-fix the source-policy tuple. Do not roll back by relabeling retained artifacts. B keeps readers V1 until C, and no future helper or package was pulled forward.

Shared-memory fact for root: fixture and retention layout-symbol introduction are indivisible; synthetic Git fixtures patch the new selector but production retains exact supported-source matching. Frozen deployment inventory is22, not24; the two extra source-owned documentation files are not deployment members.

## Exact source selection hashes

- `factory/src/adaptive_factory/landing_artifact.py` (whole_frozen): `2452174a5d1e7188e3de0902534a0f9599583d6def0b673b2e2100850f5c42e3`; Git blob `e7aad41d1f2f4aee8fa4163e6f6fbfddacb11b77`.
- `factory/src/adaptive_factory/landing_artifact_retention.py` (three_source_layout_hunks): `19d138896f5f64b517468b4a575883f51f277950a92964143a273a3c62c04cc5`; Git blob `d05d435c2edb1008f60825eb80709e5d8592e8f2`.
- `factory/src/adaptive_factory/landing_evaluation.py` (whole_frozen): `677d4d59e23731e912d89b6214b3d75dca9b98e343d4cf284ab21affea141741`; Git blob `7535e4d10fc2d6cdfd4ebd4aeb4c8912cbe61994`.
- `factory/src/adaptive_factory/landing_renderer.py` (whole_frozen): `270b623ae19a01a9c97f6a1ea3874a02eac5fa1832ebf55a3d3f73facc48b8bf`; Git blob `bcf35122a71274093f48e599bc086a0d83b6dd3b`.
- `factory/tests/test_landing_api.py` (whole_frozen): `41fdce38d6643d6a24bb505d513a5720079cea0263ad8424e8ca369110db49f5`; Git blob `e2bd51971fa55fd5d7021837382732deb9bf322f`.
- `factory/tests/test_landing_artifact.py` (whole_frozen): `7ca401cbb66c6a63bcd9c4e797d6b5f214709aa0b5a50a58d2512c464ec747c4`; Git blob `63e470577fbaa17fc58b86b0d61303a583edb1f4`.
- `factory/tests/test_landing_live.py` (whole_frozen): `3795a2ba99c2f00f6d84f14beb67f67639848711c50334e4a11a647db005de0f`; Git blob `fc0c5df5bfb32cd18f7fb6652e4dd1abdcffaaf4`.
- `factory/tests/test_landing_renderer.py` (whole_frozen): `ecb087b7a38fa2c3d9432e1dd203c0abdd21ce5a493ba478524dd406b28da005`; Git blob `722a966ea75a8d32a60b2f4d759d6f5ad4834f56`.
- `factory/tests/test_landing_sqlite_store.py` (whole_frozen): `07217325095ab1ea293b768a830a0acc125bf89d63cc05d1743617c56380c4ea`; Git blob `15e0f33d9fbd18f9368c20d34d274dee0d62bc77`.
