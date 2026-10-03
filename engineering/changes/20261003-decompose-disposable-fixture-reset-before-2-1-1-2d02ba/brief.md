# Disposable fixture reset prerequisite

Owner explicitly ordered decomposition instead of raised code budgets. Baseline is protected main63799f8760d3a55028d83ab5ff0116ececf8f7d1. This isolated prerequisite changes only the duplicated test reset seam, not M7.1, production runtime, migrations, or release version.

Extract the identical 43-table025 TRUNCATE statement to factory/tests/postgres_fixture_reset.py::reset_fixture_tables(cursor). Replace exactly that statement in execution setUp and restart _reset_database; retain caller transactions, guards, suffix statements and synthetic observation payloads. Leave test_postgres_integration.py untouched: future F changes it independently, so extracting it now buys no later budget relief.

Use one selected data_implementer in this isolated worktree. Preserve full verification, five independent reviews, exact-head external Trust CI and signed approvals. Local workflow consent is not external approval. The goal remains the full2.1.1 release with heartbeat/watchdog; this prerequisite is not that release.

Bounded verifier-readiness repair,2026-10-03: five exact unchanged two-reconciler trials reproduced one legitimate500ms LockNotAvailable/StoreUnavailable while winner COMMIT/WalSync retained the counter lock~700ms. This same already-scoped execution test file needs narrowly cause-specific refusal handling and post-contention retry without changing production runtime/SQL/timeouts; original exact-once assertions remain mandatory. The known baseline test failure must be repaired before spending another full gate.
