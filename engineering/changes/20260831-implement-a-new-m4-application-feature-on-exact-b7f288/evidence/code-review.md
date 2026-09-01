# Code re-review — M4 durable factory control plane

## Verdict

**FAIL**

The three prior code-review findings are closed, but one new Important finding remains in their authority remediation. No Critical findings were found. AC-014 and a passing local code-review receipt are therefore not satisfied at exact HEAD.

## Review binding

- Route: `b7f288f1e81e`
- Product base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior failing HEAD: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`
- Reviewed fix HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Exact merge base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Full range inspected: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Focused fix range inspected: `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06..4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Exact-head verifier receipt before this report rewrite: **PASS**, fingerprint `0092b4cd8152eb7919c94c610e66c7a4d71ad46382f1c5db852df41af0ac8789`, created `2026-09-01T20:26:54+00:00`. It records `factory-unit`, 59-test disposable PostgreSQL/API exit with actual restart/reconciliation, and source stability as passing.

## Finding

### Important — CR-004: the M0 authority row lock does not serialize intake against revocation

Migration 009 moves authority validation into the intake transaction, but both security-definer validators select the authority row `FOR KEY SHARE` (`factory/src/adaptive_factory/resources/009_authority_audit_and_history_indexes.sql:32-60`). Revocation changes only the non-key `revoked_at` column. PostgreSQL uses a `FOR NO KEY UPDATE` row lock for an update that does not change a unique-key value, and `FOR KEY SHARE` is compatible with that lock mode. A revoker can therefore update and commit `revoked_at` while the intake transaction still holds its key-share lock and continues inserting the accepted intent/task.

The implementation ledger explicitly claims that these functions lock authority rows against concurrent revocation, but the current regression does not exercise that interleaving. It blocks intake on the source-identity advisory lock, commits revocation first, and only then allows `_verify_m0_authority` to read the row (`factory/tests/test_postgres_integration.py:165-179`). That proves a pre-validation revocation is rejected; it does not prove that revocation after a successful validation is serialized with the remaining intake transaction.

This leaves the original authority TOCTOU partially open: the validation and accepted-intent writes now share a transaction, but a revocation can become committed before the accepted intent commits. That contradicts the fail-closed stale-authority requirement and the remediation's stated transaction-bound revocation guarantee.

Required repair: acquire a row lock that conflicts with non-key revocation updates, such as `FOR SHARE` or `FOR UPDATE`, in both observation and exception validators (or use an equivalent atomic authority-consumption protocol). Add a two-connection PostgreSQL regression that pauses after successful authority validation, attempts `UPDATE ... SET revoked_at=...` concurrently, and proves there is no ordering where revocation commits before an intake based on that authority commits. The opposite ordering—revocation wins before validation—must continue to reject intake.

## Prior code-review closure

| Prior finding | Result | Evidence |
| --- | --- | --- |
| CR-001: subset intake key discarded changed frozen authority as a duplicate | **Closed** | `idempotency_key` now hashes the complete `intent_digest` (`factory/src/adaptive_factory/contracts.py:267-271`). Contract tests vary limits, producer head and evidence; real PostgreSQL proves exact replay plus head/authority/limit supersession (`factory/tests/test_contracts.py:66-81`, `factory/tests/test_postgres_integration.py:97-124`). |
| CR-002: repository-limited operator could run global reconcile/metrics | **Closed** | Both operations now require operator kind and wildcard repository authority before reaching the store (`factory/src/adaptive_factory/service.py:30-34,148-152`), with a service regression proving a scoped actor reaches neither path (`factory/tests/test_service.py:85-95`). |
| CR-003: malformed closed commands escaped as 500/database errors | **Closed** | API helpers now validate closed mappings, text/IDs, canonical UUIDs, strict integers, digests and repository arrays before store access (`factory/src/adaptive_factory/api.py:66-130`). Claim, grant, proposal, budget, usage, kill, reconcile, list/show and cancel use those parsers; malformed role/type/limit/cursor/task/reason cases return bounded 4xx responses (`factory/tests/test_api.py:131-159`). |

## Focused fix-wave review

- Intake authority is now repository/full-policy/action bound and checked inside the insertion transaction through fixed-search-path, PUBLIC-revoked security-definer functions. Wrong repository/policy/scope and pre-validation revocation fail closed. CR-004 is specifically about the row-lock strength after validation, not those bindings.
- Migration 009 is additive and retains the already-applied 001–008 bytes. It versions the audit envelope, keeps legacy version-1 verification, adds task/run/correlation to new version-2 digests, and adds predicate-compatible task-history indexes.
- Cross-attempt unresolved reservations now set `accounting_blocked` and force `needs_human`; completion checks every live task reservation plus aggregate reserved counters. This closes the reviewed accounting escape without weakening exact command replay.
- Reconciliation acquires canonical capacity locks before the task row, matching cancel/supersede/release order. Capacity arithmetic, live-allocation fencing, bounded pages and the exact five-second statement timeout remain intact.
- The new local admin boundary uses a distinct owner DSN, parameterized identifier/literal composition, bounded runtime login attributes, `NOINHERIT`, and readiness through the runtime credential. It adds no external/provider/Git/GitHub/deployment command path.
- Actor/token files now require absolute normalized paths, descriptor-walked no-follow ancestry, trusted ownership, final-parent integrity and owned mode-0600 regular files. The UDS server remains the only application listener.
- Rollout/rollback documentation consistently requires schema 009, local source-only activation, evidence preservation and forward recovery via 010+.

## Verifier and evidence review

The earlier repository-sandbox capability hotfix remains narrowly scoped: only exact `GROK_VERIFY_CAPABILITY=repository-sandbox` skips only `factory-postgres-exit`; other values execute and propagate the runner result. The current exact-head local receipt used the execution path, not a skip, and records the disposable database/API/restart suite as passing.

The receipt is credible evidence for covered behavior but does not exercise the post-validation revocation interleaving described in CR-004. Rewriting this report changes the worktree fingerprint, so the pre-review receipt must be refreshed only after remediation and all independent reviews settle.

## Reviewer checks

- Exact HEAD and merge base — matched the requested `4230dc8e73bcf4dfcf6c60d294d379d44a30c698` and route base.
- `git diff --check <base>..<head>` — PASS.
- Full cumulative diff and all eight focused fix-wave commits — inspected, including contracts, service/API, store, migration 009, settings/server/admin, tests, architecture and rollout evidence.
- Exact-head verifier receipt — PASS at supplied fingerprint; factory exit records 59 tests plus actual PostgreSQL restart, one repair, replay no-op, higher fence and late-holder rejection.
- CR-001/002/003 regression paths — inspected and matched the repaired implementation.
- CR-004 lock analysis — validator `FOR KEY SHARE` compared with the non-key `revoked_at` update and with the actual advisory-gated test ordering; the current test does not enter the vulnerable post-validation window.

## Residual risks after required repair

Reconciliation remains globally serialized by capacity locks and deliberately bounded by a five-second timeout, so high contention can produce a safe failed invocation that an operator must replay with the same command key. Migration 009 invalidates legacy authority rows whose new repository/policy fields remain null; that is a fail-closed rollout characteristic and requires explicit reprovisioning before intake. None of this local evidence replaces the App-owned exact-SHA Trust CI check or signed external approvals.
