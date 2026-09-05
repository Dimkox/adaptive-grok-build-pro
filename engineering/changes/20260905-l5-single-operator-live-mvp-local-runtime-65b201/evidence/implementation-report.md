# Focused implementation evidence

This report is local source evidence only. It claims no full verifier, review,
live model, network, publisher, cPanel, hosting, release, or deployment action.

## Native-Codex normalizer seam

- RED: `PYTHONPATH=factory/src:. python3 -m unittest -v factory.tests.test_landing_normalizer` — expected `ModuleNotFoundError` for the missing module.
- GREEN: the same focused module passed `5/5`; the existing provider module passed `7/7`, and the three affected API methods passed `3/3` with the factory virtual environment.
- Static checks: targeted Ruff and Bandit passed after replacing the one test-only assertion flagged by Bandit.

## Durable SQLite state

- RED: `PYTHONPATH=factory/src:. python3 -m unittest -v factory.tests.test_landing_sqlite_store` — expected `ModuleNotFoundError` for the missing store.
- GREEN: all four methods passed across the initial run and one exact failed-method rerun; the only intermediate error was invalid test setup attempting to skip legal state transitions.
- Compatibility: the three affected API idempotency/cancel/provider-failure methods passed; targeted Ruff, Bandit, and diff checks passed.

## Coordinator-to-artifact runtime

- RED: `PYTHONPATH=factory/src:. python3 -m unittest -v factory.tests.test_landing_runtime` — expected `ModuleNotFoundError` for the missing runtime builder.
- GREEN: the focused method passed `1/1`, producing an offline deterministic 20-member `SiteArtifactV1` plus retained ZIP, sidecar, manifest, attempt, evaluation, and run metadata.
- Compatibility/static: the affected injected-artifact API method, targeted Ruff, Bandit, and diff checks passed.

## Architecture

- RED: the focused seed-model method reported the three new source files as undeclared.
- GREEN: the focused model method, architecture validate, drift, generated-diagram check, and exact worktree fitness against `f3f8d7375a153393ffba3906165e8d625e45d4a1` passed. Fitness truthfully escalates risk to red for the new local datastore and edge and requires the selected architecture/data review scopes.

The optional reversible publisher was not required for the finite Stage 3/5 MVP
and was deferred. Final exact-head verification and four selected reviews remain
pending after the tracked source checkpoint is frozen.
