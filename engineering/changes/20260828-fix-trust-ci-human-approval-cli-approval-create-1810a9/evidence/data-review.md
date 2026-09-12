# Data review — human approval CLI import repair (final rerun)

Change: `20260828-fix-trust-ci-human-approval-cli-approval-create-1810a9`
Route: `1810a99eee3c` · reviewer: `data_reviewer` (read-only)
Reviewed: 2026-08-28
Base/HEAD: `1c06299894279a88b881defa3f19b004fa742223`
Pre-report tree fingerprint: `94a15e670d843cc6f4ab7f9d8bc9d2d11f6ea0d2e5b0e2272da84d9dbeecc258`

**PASS.** The implementation changes no API, store, model, signing, SQL,
migration, query, transaction, or requeue semantics. The operator documentation
accurately describes one envelope per scope, replay rejection, ambiguous-submit
handling, and accepted approvals that produce no requeue transition.

## Concrete findings

1. `git diff --quiet` from the reviewed base reports no change in
   `api.py`, `store.py`, `models.py`, `signing.py`, `migrations.py`, or packaged
   SQL. No untracked file matches those data-sensitive surfaces and no migration
   was added.
2. Final-tree SHA-256 values match the data-architecture baseline exactly:

   | Boundary | SHA-256 |
   | --- | --- |
   | `resources/001_schema.sql` | `c03e071c1a789c856b54be23c105fd224e1f569b1662b61d46354f2212f46532` |
   | `resources/002_operational_indexes.sql` | `f46128291b765a77568be448f5ef09d37300423afd327370ee2da79d5f33487c` |
   | `resources/003_database_roles.sql` | `1ba63d44639a6cb933a31b887717b021e35b6d056aa564a25f0aaba1683c888c` |
   | `store.py` | `045e48a77a6d729583625b1f7291ebd97e4a06af8c973b90600c139d21be5773` |
   | `api.py` | `c251329172875a97ea6aa8796a48a72a42fd0c573de2170934df2637992d2939` |
   | `models.py` | `64160f82d502ae48fabf068bc6baec994e3af78b7f90b4748bb090a2fa9dc476` |
   | `signing.py` | `ae7ce6c8bd1fe7354daf151b2afac369f2082b7e227f02266935dfa0d2640dc1` |
3. The `cli.py` diff only removes eager imports and restores the same imports at
   their command branch entry. Approval payload construction, signature creation,
   API submission bytes, and every server/database command body are unchanged.
   There is therefore no indirect query or state-transition change from the import
   repair.
4. Existing durable semantics remain:
   - each accepted envelope inserts one scope-bearing approval;
   - approval ID and nonce uniqueness map replay to HTTP 409;
   - worker authorization remains bound to repository, PR, base/head SHA, policy,
     scope, and validity window;
   - requeue remains a separate update of matching `needs_approval` jobs by
     repository and head SHA, so an accepted approval can report
     `requeued_jobs: 0` when no waiting row transitions.
5. `trust-ci/README.md` matches those semantics. It requires distinct output files,
   approval IDs, and nonces for each missing scope; forbids editing or reusing a
   signed envelope; warns against automatic retry after an ambiguous timeout;
   explains HTTP 409 replay; and treats HTTP acceptance as insufficient merge
   authority. Its `requeued_jobs: 0` wording is intentionally non-exclusive and
   accurately covers the normal multi-scope race where the job is already queued or
   running.
6. The review-fix test `CommandBranchImportTests` has no data or operational
   effect. Before invoking each relocated non-human command, it replaces the API,
   worker, migrator, store, backup/restore, GitHub, settings, policy, signing, and
   `uvicorn` modules in `sys.modules` with in-memory doubles. Migration apply/status,
   PostgreSQL ping, backup/prune/restore, branch protection, worker, and API actions
   only append named events. The database URI uses the reserved `.invalid` domain,
   all paths are inside a temporary directory, and the keygen branch asserts that no
   key files were created. No real database connection, migration, backup, restore,
   GitHub mutation, service start, kill-switch mutation, or credential access occurs.
7. The runbook keeps the human private key, deployed-policy handoff, virtual
   environment, and signed envelopes outside both the source checkout and all
   agent/service workspaces. No operational key, approval, database, or deployed API
   was accessed during this review.

## Independent checks

```text
PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest -v
  trust-ci/tests/test_cli.py trust-ci/tests/test_signing.py trust-ci/tests/test_store.py
Result: 25 tests passed, including every mocked non-human command branch.

PYTHONPATH=trust-ci/src:trust-ci/tests uv run --no-project
  --with cryptography==46.0.4 --with fastapi==0.128.2
  --with psycopg[binary]==3.3.4 --with httpx==0.28.1
  python3 -m unittest -v trust-ci/tests/test_api.py
Result: 14 tests passed, including signed approval requeue and tamper rejection.

git diff --check
Result: passed.
```

No disposable PostgreSQL URL was configured, so this reviewer did not rerun the live
database nonce-constraint test. That does not block this CLI-only/test-only final tree
because the schema/store/signing bytes are identical to the reviewed base and
in-memory replay, exact-field lookup, requeue, and API contract tests passed.

## Residual unchanged behavior

The pre-existing separate approval-insert/requeue transactions, same-head job lookup,
and repository+head requeue breadth remain unchanged. They can produce accepted
approvals with zero requeues or extra non-authorizing attempts, but they cannot satisfy
the worker's exact per-scope approval lookup. They belong in a separate atomicity and
query-hardening change, not this import-boundary repair.

No data-review blocker. This report is local evidence only and is not merge authority.
