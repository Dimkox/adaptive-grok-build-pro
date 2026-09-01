# Independent release review — M4 durable factory control plane, fix wave

## Verdict and binding

**PASS** for route-selected local `release_review`; no Critical or Important release-readiness finding remains.

- Route: `b7f288f1e81e`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior failing product head: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewed fix head: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Fix range: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Exact-head verification receipt: PASS, fingerprint `0092b4cd8152eb7919c94c610e66c7a4d71ad46382f1c5db852df41af0ac8789`.

I inspected the prior failing report, the full committed and fix ranges, active route/package state, migration 009, admin bootstrap implementation and tests, compose/environment examples, installer inventory, README/release/rollback documentation, UDS server/settings paths, disposable exit/restart harnesses, and exact-head receipt. `git diff --check` is clean for the fix range.

## Prior RR-001 closure

**Closed.** The package now supplies `adaptive-factory-admin` with two explicit interfaces: `migrate` applies the checksum-locked migrations through `FACTORY_MIGRATOR_DATABASE_URL`, while `bootstrap-local` migrates then creates or validates the bounded runtime login (`LOGIN NOINHERIT NOSUPERUSER NOCREATEROLE NOCREATEDB`), grants only `factory_runtime`, and verifies effective-role readiness using `FACTORY_DATABASE_URL` (`factory/src/adaptive_factory/admin.py`).

The shipped configuration is internally consistent: the Compose owner, owner DSN, runtime login/password, runtime DSN, and loopback port are all explicit in `factory/.env.example` and `factory/compose.yaml`. The server only receives the runtime DSN and every store connection executes `SET ROLE factory_runtime`. The disposable PostgreSQL test exercises the shipped bootstrap flow, proves `session_user=factory_service_test` with `current_user=factory_runtime`, and asserts schema version 009 (`factory/tests/test_postgres_integration.py:test_shipped_local_bootstrap_provisions_effective_runtime_login`). This establishes the previously missing reproducible owner/runtime path and the intended NOINHERIT membership boundary.

The README and release plan now require the separately authorized local sequence: distinct owner/runtime DSNs, backup restore comparison, bootstrap/migration through schema 009, runtime-only server start, readiness/metrics/capacity checks, synthetic lifecycle, actual restart, and two-pass reconciliation. They consistently prescribe forward migration `010+` after durable intake; rollback preserves state/audit/logs/evidence and prohibits down-migration or audit deletion.

## Release readiness assessment

- Nine migrations are contiguous, immutable/checksum-bound, advisory-lock protected, factory-only, and included in the installer payload. Migration 009 is a forward-only authority/audit/index addition; recovery language is correctly advanced to `010+`.
- The installer transfers the admin interface, source, SQL resources including 009, contract, lockfile, examples, and disposable verification harness, while excluding credentials, sockets, database contents, and runtime state. Installation remains non-activating and does not run migrations.
- The server binds an owned absolute `AF_UNIX` socket at mode `0660`; CLI traffic is HTTP over that Unix socket. Actor/token configuration uses absolute owner-pinned no-follow descriptor traversal and mode-`0600` leaves. Static inspection found no factory product path for provider execution, shell/repository/GitHub action, TCP listener, systemd/deployment, Trust CI mutation, or external/production write. Docker is confined to explicitly named disposable test state.
- The exact-head verification receipt records all required local checks as passed, including architecture/governance/secret/contract/SQL checks, Ruff, Bandit, root tests/coverage, factory unit tests, `factory-postgres-exit=pass`, and source stability. The exit harness runs the real PostgreSQL suite and actual restart/reconciliation; the fix-wave suite additionally covers bootstrap, effective role, UDS authentication, authority controls, bounds, and migration 009.
- The explicit `repository-sandbox` verifier capability may skip nested-container work only in that constrained environment; this exact local receipt records the PostgreSQL exit as **pass**, not skip. The capability declaration is not merge authority.

Minor hardening remains possible: a single process-level test that combines the freshly bootstrapped real store, file-loaded actors, and authenticated UDS request would join already-passing bootstrap/readiness and UDS transport tests. It is not a release blocker because the shipped bootstrap/effective-role integration and real UDS authentication coverage independently exercise those boundaries.

## Evidence and delivery boundary

This is a local preflight PASS only. It does not authorize a database migration, local rollout, activation, PR delivery, merge, tag, publication, deployment, production mutation, or Trust CI mutation. The active change remains `verifying`; AC-014 is unchecked, and the worktree contains in-progress reviewer-report updates. Thus the current verification receipt cannot bind the eventual final evidence tree.

Once the evidence set is frozen, run fresh fingerprint-bound local verification and record all route-selected reviews on the same tree. PR delivery requires separate authorization. Merge eligibility then requires the GitHub App-owned exact-head `adaptive-trust-ci/verified@<policy-sha12>` Check Run and every required independently signed scope; local receipts, reports, state values, and delegated grants do not replace those external gates.
