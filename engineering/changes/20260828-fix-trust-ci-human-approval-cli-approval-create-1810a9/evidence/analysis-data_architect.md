# Data architecture analysis — human approval CLI import repair

Route: `1810a99eee3c`
Role: `data_architect` (read-only)
Reviewed base: `1c06299894279a88b881defa3f19b004fa742223`

## Verdict

The proposed command-local/lazy-import repair needs **no database schema, migration,
index, query, role-grant, backfill, or durable-state change**. The failure occurs before
CLI argument dispatch; moving imports in `cli.py` and documenting a source-checkout
operator invocation does not change the approval envelope or any API/store behavior.

The data boundary for this hotfix should remain strict: permitted product changes are
`trust-ci/src/adaptive_trust_ci/cli.py`, an isolated CLI regression test, and operator
documentation. Any change to `api.py`, `store.py`, `models.py`, `signing.py`, packaged
SQL, deployed policy/trust-store state, or PostgreSQL contents is scope expansion and
must block this hotfix pending separate design/review.

## Existing durable approval contract

The current schema already stores every value needed for exact approval lookup:
`repository`, PR number, base SHA, head SHA, policy digest, scope, actor/key identity,
reason, issued/expiry times, canonical payload, and signature. `approval_id` is the
primary key and `nonce` is independently unique. The lookup index follows the worker's
exact authorization dimensions: repository, PR, base/head, policy, scope, and expiry.

The server-side sequence is currently:

1. `POST /approvals` parses the versioned envelope and rejects scopes absent from the
   deployed policy.
2. The API resolves a job, verifies trusted key, actor, scope, exact PR/base/head,
   policy digest, TTL, validity window, and Ed25519 signature.
3. `record_approval` inserts the envelope; PostgreSQL uniqueness SQLSTATE `23505` is
   mapped to `ReplayError` and HTTP `409`.
4. `requeue_for_approval` changes waiting jobs from `needs_approval` to `queued` and
   clears the prior approval-required result.
5. On execution, the worker authorizes each required scope using a query bound to all
   exact fields and the current time window. Requeue alone therefore cannot make a
   mismatched approval valid.

The CLI repair changes none of these semantics. The existing table, index, and grants
are sufficient; there is no data conversion, dual read/write, or deployment ordering
requirement.

## Schema and state evidence

Baseline hashes captured at the reviewed commit:

| Boundary | SHA-256 |
| --- | --- |
| `resources/001_schema.sql` | `c03e071c1a789c856b54be23c105fd224e1f569b1662b61d46354f2212f46532` |
| `resources/002_operational_indexes.sql` | `f46128291b765a77568be448f5ef09d37300423afd327370ee2da79d5f33487c` |
| `resources/003_database_roles.sql` | `1ba63d44639a6cb933a31b887717b021e35b6d056aa564a25f0aaba1683c888c` |
| `store.py` | `045e48a77a6d729583625b1f7291ebd97e4a06af8c973b90600c139d21be5773` |
| `api.py` | `c251329172875a97ea6aa8796a48a72a42fd0c573de2170934df2637992d2939` |
| `models.py` | `64160f82d502ae48fabf068bc6baec994e3af78b7f90b4748bb090a2fa9dc476` |
| `signing.py` | `ae7ce6c8bd1fe7354daf151b2afac369f2082b7e227f02266935dfa0d2640dc1` |

Final data review should compare these boundaries to the final tree. No migration
should be added and `migration-status` should remain unchanged. This analysis did not
connect to or mutate PostgreSQL, inspect credentials, or access a human private key.

## Required regression evidence

For this CLI-only slice:

- Add the failing fresh-process import-boundary test for `approval-create` and
  `approval-submit`; it must block API, worker, PostgreSQL, migration, backup, GitHub,
  and server-settings imports.
- Create an envelope only with a disposable test signer and assert it parses/verifies
  through the unchanged version-1 model/signing implementation with exact repository,
  PR, base/head, policy digest, scope, TTL, and signature.
- Keep and run `test_signed_approval_requeues_matching_waiting_job` and
  `test_tampered_approval_is_rejected` in `test_api.py`.
- Keep and run `test_store_rejects_approval_replay` plus exact-field lookup and
  waiting-job requeue tests in `test_signing.py`/`test_store.py`.
- When the configured disposable PostgreSQL test service is available, run
  `test_approval_nonce_replay_is_rejected_by_database_constraint` and migration
  registry idempotency in `test_postgres_integration.py`.
- Add no test that reaches the deployed `/approvals` endpoint or reads an operational
  PEM. Test keys must be ephemeral fixtures only.

Focused baseline evidence on this commit:

```text
$ PYTHONPATH=src:tests python3 -m unittest tests/test_signing.py tests/test_store.py
.....................
Ran 21 tests in 0.083s
OK
```

The final fingerprint still requires the route's full verification and independent
data review; this baseline result is not a completion receipt.

## Existing record/requeue/replay risks (unchanged by this repair)

These are residual properties to preserve and monitor, not reasons to add data work to
the CLI hotfix:

| Risk | Current effect | Hotfix treatment |
| --- | --- | --- |
| Insert and requeue use separate transactions | A process failure after committed insert but before requeue leaves a valid approval stored while the job remains `needs_approval`; replaying the same envelope returns `409`. | Do not change here. Document that a fresh approval may be required; consider a separate transactional/idempotent API design. |
| Approval arrives after worker checks but before it finishes `needs_approval` | API may persist the approval while `requeued_jobs=0`; the later state transition can leave a job waiting despite a valid approval. | Do not change here. A follow-up should serialize/reconcile approval arrival and the waiting transition. |
| Requeue predicate is only repository + head SHA + waiting status | Jobs for different PRs that share the same head commit may also be awakened. | No authorization bypass: the worker's approval lookup is still exact PR/base/head/policy/scope/time. It can cause extra attempts/noise; a separate hardening change could use exact job identity. |
| API job lookup chooses the latest repository/head match | Same-head jobs in multiple PRs can make an otherwise correctly signed older-PR envelope fail against the latest job context. | Preserve behavior in this minimal repair; evaluate exact payload-bound lookup separately. |
| Approval expires before the worker consumes it | Worker rejects it and returns to `needs_approval`; a new approval is required. | Expected fail-closed behavior; keep short TTL operationally visible. |
| Two distinct scope approvals race | One request may report `requeued_jobs=1` and the other `0`; both durable approvals can still satisfy the worker. | Treat zero requeues as accepted-but-no-state-change, not signature failure. Preserve response semantics. |

The first three race/atomicity items deserve a separate data/API hardening change with
PostgreSQL concurrency tests. Combining them with the import repair would expand the
blast radius, require new query/state semantics, and make rollback less reliable.

## Rollout and rollback

Rollout is source code/tests/docs only. Existing API and worker services do not need a
database migration, restart, reindex, backfill, or state repair for the operator CLI to
work from a reviewed checkout. Previously stored approvals remain valid according to
their original exact fields and expiry.

Rollback is a commit revert of the CLI/test/docs change. It has no data rollback or
forward-recovery step. A new commit or policy epoch still requires a newly human-signed
approval; an existing envelope must never be rewritten or replayed for another target.

## Final data-review gate

Pass only if the final diff proves all of the following:

1. No packaged SQL, store query, API approval handler, model, signer, policy, or role
   grant changed.
2. No migration was added and no database command was required for rollout.
3. The CLI-produced envelope still verifies with the unchanged exact-field verifier.
4. Replay remains rejected in memory and PostgreSQL, and matching waiting-job requeue
   remains covered.
5. Documentation never tells an agent, API, worker, or container to access the human
   private key and never embeds a real path, key, token, or credential.
