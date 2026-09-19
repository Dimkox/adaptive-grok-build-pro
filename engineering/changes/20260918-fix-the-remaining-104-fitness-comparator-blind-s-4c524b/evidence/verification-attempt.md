# PR verification attempt

Command: `TMPDIR=/tmp python3 scripts/grok_verify.py --mode pr`

This was the only full PR verifier run for this package. Profiles `base,contracts,ai` ran against 23 changed files. Diff/spec/architecture/governance/security/contract/SQL/Ruff/Bandit/root unit/coverage/factory unit/source-stability checks passed. `factory-postgres-exit` failed after its disposable PostgreSQL run executed 767 factory tests in 364.178 seconds (2 skipped, 1 error).

The failing test was `factory.tests.test_postgres_integration.PostgresFactoryTests.test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated`. During the `lowered_budget_child` fixture setup, `_validate_capability_session` in `factory/src/adaptive_factory/store.py` received PostgreSQL `QueryCanceled: canceling statement due to statement timeout`; `_connect` translated this to `StoreUnavailable`. The harness then reported `exit=1`. The failure is outside the #104 comparator changes and is preserved as a failed verification result, not a passing receipt.

During this verifier run, a sibling worktree also ran Ruff/spec/diff checks. That violated the repository's timing-sensitive suite isolation rule in issue #40 and may have contributed host contention. No full rerun is planned for this package; determine any follow-up from the exact failure and focused evidence.
