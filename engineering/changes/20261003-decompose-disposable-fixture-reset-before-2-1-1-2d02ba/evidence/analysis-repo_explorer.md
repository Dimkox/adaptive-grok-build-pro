Read-only fixture seam analysis, route 2d02ba9e25dc.

Identity: precursor HEAD63799f8760d3a55028d83ab5ff0116ececf8f7d1, only untracked active change package before/after inspection. F reference HEAD e3509dcf40e9b67e1ee6b51fbbaa208d5ba26a69. No tests, database connections, candidate writes, caches, generated files, external operations or subagents. reviewed-tree-modified: no.

Exact callsites:
- factory/tests/test_execution_persistence_postgres.py:321 ExecutionPersistencePostgresTests.setUp opens DATABASE_URL owner connection, truncates the explicit legacy inventory with RESTART IDENTITY, conditionally truncates kill_switch_heads and reseeds metric_counters when metric_counters_pre_012_untrusted exists, zeros capacity/execution counters, then inserts synthetic authority observation. Keep observation creation/insertion and runtime-store setup local.
- factory/tests/postgres_restart_probe.py:351 _reset_database opens database_url owner connection, performs the same table inventory and counter reset but ALWAYS truncates kill_switch_heads/reseeds metric_counters, inserts probe/repository observation and returns its tuple. Called once by main at1253 after disposable identity assertion1216 and role/migration setup. Keep wrapper, returned tuple, synthetic observation and target/version/container guards intact.
- factory/tests/test_postgres_integration.py:263 PostgresFactoryTests.setUp contains a third legacy reset matching execution setUp, including conditional singleton handling. Its environment DATABASE_URL is defined58 and imported by execution module74.

Smallest safe seam: new factory/tests/postgres_fixture_reset.py importing no caller modules. Provide a cursor-level legacy reset function with explicit singleton-reset policy preserving conditional execution/integration semantics versus unconditional restart semantics. Caller-owned connection/context manager retains atomic commit/rollback behavior and owner capability. Share table inventory, legacy singleton policy, capacity and execution counter resets; leave observation insertion to callers. Future F can extend the helper's exact table inventory behind bounded schema/version handling without touching large callers. Do not put feature026 tables into this precursor.

Import/installer boundaries:
Execution already imports factory.tests.test_postgres_integration for DATABASE_URL/NOW/actors. New helper must not import that module or postgres_restart_probe, preventing a new cycle.
Restart already imports factory.tests.decision_fixtures and can use the same factory.tests helper import style. run_disposable_exit.py146 adds repository root and factory directory to PYTHONPATH; retain that runner/import setup.
scripts/install_into.py26 MANAGED_FILES explicitly installs restart/integration tests; the helper requires its own exact entry. tests/test_installer.py500 asserts the closed installed factory/tests inventory and must gain that entry. Execution test is currently NOT in that installed inventory; adding the helper does not imply adding all execution tests.
test_migrations.py21 imports restart probe; numerous bounded restart guard tests depend on its existing wrappers. A helper import must remain available in installed trees and must not move target guard APIs.

Recommended product inventory: new helper; execution persistence caller; restart caller; focused new helper characterization test; scripts/install_into.py; tests/test_installer.py. Add test_postgres_integration.py only after quantitative whole-artifact accounting if removing its duplicated reset is required now. A focused test under factory/tests also needs an installer decision; installing it requires matching closed inventory update. Existing test_migrations.py changes are optional if the new focused module covers seam characterization without changing its guarded APIs.

Budget evidence from brief and unchanged rules:
Execution277395bytes/196AST + restart66536/69 =343931bytes/265AST before edits/new helper/tests. Adding integration411151/296 yields755082bytes/561AST before edits, leaving44918bytes/39AST under factory-test800000bytes/600AST. This is not proven sufficient for helper and meaningful characterization; two-caller scope has materially more room. Full final metrics must be remeasured, and remaining integration duplication should be explicitly tracked if deferred.
F reference modifies ONLY the two initial callers' TRUNCATE prefixes to prepend six tables: m7_command_results, m7_contexts, m7_checks, m7_outcomes, m7_bundles, m7_source_bindings. Restacking F must replace those prefix edits with helper extension; retain unrelated F feature/tests. No F migration/feature bytes belong to precursor.

Unexecuted claims: SQL equivalence, FK behavior, real rollback, disposed target rejection and final AST/byte metrics require writer characterization and later verification. No fresh pass or inherited approval asserted.

Evidence commands: exact git HEAD/status, bounded sed of three reset blocks and installer inventory, rg for reset callsites/imports/runner PYTHONPATH, exact base..F diff restricted to two callers, existing rule limits.

Startup2026-10-03T00:18:36Z:14physical/28logical CPUs0-27; default22/affinity0,1,8-27; actualcgroup/user.slice/user-1000.slice/session-2050.scope, root/user.slice cpuset0-27 and no finite ancestor quota. Child widening succeeded28/0-27; assignedCPU0/max1 worker. Private0700 snapshot/report:
 <local-path>
 <local-path>
