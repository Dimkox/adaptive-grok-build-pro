# Test review — `2865fdc`

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Reviewer: `test_reviewer` (read-only except this report). Route: `f771ecaf458d`. Write owner: none.  
Reviewed tree: `feat/trust-ci-control-plane` HEAD `2865fdc632860534c8ffc61aa9981844a0685b5d`  
Commit: `fix: enqueue draft PRs and prove live PostgreSQL Trust CI state`

Did **not** re-run unittest, compose, or `grok_verify` (would dirty receipts / coverage). Independent file review of the named characterization tests, the product sites they lock, the live Postgres class, and the restart-drill harness. Live `postgres-integration` 8/8 and restart drill PASS are taken from parent work as instructed.

**PASS.**

| ID | Required case | Test | Result |
| --- | --- | --- | --- |
| P0 | Draft PR webhooks enqueue a job so PR #2 can stay draft | `trust-ci/tests/test_webhooks_github.py::test_draft_pull_request_is_enqueued` | Covered |
| P0 | Closed draft still parses for cancellation | `test_closed_pull_request_is_parsed_for_cancellation` (`draft=True`, `action=closed`) | Covered |
| P1 | `WorkspaceMutationError` accepts a path tuple (runner FakeWorkspace raise) | `trust-ci/tests/test_runner.py::test_successful_command_that_mutates_checkout_fails_pipeline` | Covered |
| P1 | Same-size dump tamper is a digest mismatch, not a size mismatch | `trust-ci/tests/test_backup.py::test_verify_backup_rejects_tampering` | Covered |
| P0 | README K10 edge count is mermaid-only (C(10,2)=45) | `tests/test_structure.py::test_readme_local_stack_graph_is_complete_k10` | Covered |
| P0 | Restart drill uses a named volume + `compose restart`, not tmpfs | `trust-ci/tests/test_ops.py::test_postgres_restart_drill_uses_named_volume_and_container_restart` | Covered |
| P0 | Live Postgres 8 skipUnless methods exist and map to the test plan | `trust-ci/tests/test_postgres_integration.py` (8 methods) | Covered |
| P0 | Restart/recovery is a separate named-volume drill | `postgres-restart-drill.sh` + `postgres_restart_probe.py`; live PASS from parent | Covered (execution: parent) |

---

## Verdict

| Gate | Result |
| --- | --- |
| Product-test adequacy for this delta | **PASS.** Each named 2865fdc regression has a characterization that would go red if the pre-fix behavior returned. |
| Characterization coverage | **PASS.** Draft enqueue, same-size backup tamper, mermaid-only 45, named-volume restart lock, and mutation-tuple constructor are isolated and load-bearing. Nearby HMAC / no-GHA / holdout-digest / SKIP LOCKED tests were not weakened. |
| Verification evidence | **PASS with recorded parent live proof.** No fingerprint-bound receipt under `.grok-stack/runtime/receipts/f771ecaf458d/` yet (reviews write after). `scripts/grok_verify.py --mode pr` still does not discover `trust-ci/tests`; that is pre-existing. Live 8/8 + restart drill PASS accepted from parent work. |

Do not return this commit to an implementer for missing tests of the named regressions.

---

## 1. Tests inspected for `2865fdc`

### 1.1 Draft enqueue — `test_draft_pull_request_is_enqueued`

`pull_request_payload(draft=True)` (default `action=opened`) must parse to a `PullRequestEvent` with `closed=False`, `pr_number=12`, `head_sha=sha('b')`. Product `parse_pull_request_event` in `trust-ci/src/adaptive_trust_ci/webhooks.py` has **no** `draft` branch: `_SUPPORTED_ACTIONS | {"closed"}` is the only gate. Reintroducing `if pull_request.get("draft"): return None` fails `assert event is not None`.

Closed drafts stay parseable: `test_closed_pull_request_is_parsed_for_cancellation` uses `action='closed', draft=True` and asserts `event.closed`. Matches `decisions.md`: enqueue opened/synchronize/reopened drafts; keep closed-draft cancellation.

API `create_app` calls the same parser and enqueues whenever `event is not None` and not closed. There is no second draft filter in `api.py` (confirmed: `trust-ci/src` has zero `draft` matches). HMAC, synchronize, and ignore-non-PR tests remain.

### 1.2 `WorkspaceMutationError` constructor — runner mutation test

There is no standalone `test_workspace_mutation_error_*`. Characterization is the existing pipeline test:

`FakeWorkspace.assert_unchanged` does `raise WorkspaceMutationError(('production.py',))`.  
`JobRunner._run_command` catches `WorkspaceMutationError`, records `{command}:source-integrity` with `str(exc)`, and fails the job even when the command exit is 0.

Product constructor (`workspace.py`):

```python
def __init__(self, paths: tuple[str, ...]) -> None:
    self.paths = paths
    super().__init__('verification command mutated checkout: ' + ', '.join(paths[:20]))
```

A `*paths: str` constructor would TypeError on `', '.join` when passed a single tuple (the baseline constructor bug). `test_successful_command_that_mutates_checkout_fails_pipeline` asserts status `failed`, command list stops at `external-holdout`, `external-holdout:source-integrity` is present, and `production.py` appears in command details. That is enough to lock the tuple constructor and the fail-closed mutation path **through the fake**.

`GitWorkspace` still raises the same constructor with `('HEAD',)` and `tuple(sorted(set(paths)))`.

### 1.3 Same-size backup tamper — `test_verify_backup_rejects_tampering`

After `create_backup`, the dump is overwritten with `b'X' * len(original)` (same byte length, different content). Expectation is `BackupError` matching `digest mismatch`.

Product `verify_backup` checks `size_bytes` **before** SHA-256. A shorter/longer overwrite (`b'tampered'`) would raise `backup size mismatch` and this test would fail to match `digest mismatch`. Same-size overwrite is therefore the correct probe for the digest branch. Adjacent tests still lock atomic dump, `confirm-disposable`, fail-closed `pg_restore`, and no partial files on `pg_dump` failure. Retention tests (same-size vs size-changing tamper on prune) are additive.

### 1.4 Mermaid-only K10 count — `test_readme_local_stack_graph_is_complete_k10`

Pairwise `itertools.combinations` of the ten node names still searches the whole README (forward or reverse `A --- B`). Edge **count** is restricted to the first ` ```mermaid ` fence: lines matching `\S+ --- \S+` must equal 45.

That count lock is necessary. Whole-file `\S+ --- \S+` currently matches 47 lines: 45 mermaid edges plus two markdown table rules (`README.md` L120 `| --- | --- |` and L137 `| --- | --- | --- | --- | --- |`). Counting outside the fence would either over-count or force the graph test to absorb unrelated tables. Current mermaid block is the complete K10 (9+8+…+1 = 45). Missing any pair still fails `missing`; extra mermaid edge fails the length assert.

### 1.5 Named-volume restart drill — `test_postgres_restart_drill_uses_named_volume_and_container_restart`

Locks, from source text:

- `trust-ci/compose.test.yaml` contains `trust-ci-pgtest-data:/var/lib/postgresql/data`
- compose has **no** `tmpfs:`
- `postgres-restart-drill.sh` contains `compose restart postgres-test`, `postgres_restart_probe seed`, and `postgres_restart_probe verify`

This is the `decisions.md` named-volume ruling: `compose restart` on tmpfs would drop the catalog; a named volume plus trap `down --volumes` proves recovery without leaving data. The unit test does not execute Docker. Live execution is the parent restart drill PASS.

Sibling `test_postgres_integration_runner_cleans_up_after_itself` still requires `compose.test.yaml`, `trap cleanup EXIT`, and `down --volumes --remove-orphans` on the 8-test harness.

### 1.6 Live PostgreSQL class (8/8)

`PostgresIntegrationTests` is `@unittest.skipUnless(TRUST_CI_TEST_DATABASE_URL)`. Eight methods, matching the test plan and architect table:

| Scenario | Method |
| --- | --- |
| Migration registry idempotent | `test_migration_registry_is_current_and_idempotent` |
| Concurrent claim / SKIP LOCKED | `test_two_concurrent_workers_cannot_claim_same_live_job` |
| Lease expiry reclaim | `test_expired_database_lease_is_reclaimed_by_another_worker` |
| Heartbeat ownership | `test_heartbeat_requires_current_lease_owner` |
| Attempts → dead | `test_expired_lease_at_attempt_limit_becomes_dead` |
| Duplicate webhook identity | `test_duplicate_webhook_identity_returns_same_job` |
| Nonce replay | `test_approval_nonce_replay_is_rejected_by_database_constraint` |
| Attestation reconnect | `test_signed_attestation_survives_new_store_instance` |

Restart/recovery remains outside this class (`postgres-restart-drill.sh`). `postgres-integration.sh` uses `--exit-code-from postgres-integration` (service name matches compose). Parent work recorded 8/8 PASS and `postgres restart drill: PASS`; this review did not re-execute them.

---

## 2. Product sites the tests actually hit

| Product | What tests lock | Independent read |
| --- | --- | --- |
| `webhooks.parse_pull_request_event` | Draft `opened` is a job request; `closed` still cancels | No `draft` handling in `trust-ci/src`; supported actions are opened/synchronize/reopened/ready_for_review + closed |
| `api.github_webhook` | Enqueues any non-closed parsed event | No draft check; HMAC still 401 (`test_invalid_signature_is_rejected`) |
| `WorkspaceMutationError` | Tuple of paths; message includes joined paths | Constructor joins `paths[:20]`; GitWorkspace raises tuple form |
| `JobRunner._run_command` | Exit 0 + mutation → failed + `:source-integrity` | `except WorkspaceMutationError`; FakeWorkspace plants `production.py` |
| `backup.verify_backup` | Size check then SHA-256 | Same-size `X * len` hits digest branch |
| `README.md` mermaid | Exactly 45 `\S+ --- \S+` lines in first fence; all 45 pairs present | 45 mermaid edges; table `---` rows sit outside the fence |
| `compose.test.yaml` | Named volume, not tmpfs | `trust-ci-pgtest-data:/var/lib/postgresql/data`; `volumes: trust-ci-pgtest-data:` |
| `postgres-restart-drill.sh` | restart + seed/verify | `compose restart postgres-test` then `up -d --wait` then probe verify |
| `test_postgres_integration.py` | 8 live scenarios | skipUnless DSN; TRUNCATE per test; barrier for concurrent claim |

---

## 3. Surrounding suite (not weakened)

| File | Still adequate? |
| --- | --- |
| `test_webhooks_github.py` HMAC, synchronize, Checks, app-bound `app_id` | Yes. Draft case was inverted from ignore → enqueue, not deleted. |
| `test_api.py` signed webhook enqueue, kill switch, closed cancel | Yes. Helper still sends `draft: False`; parser-level draft test is the contract for #2. |
| `test_runner.py` holdout-before-checkout, needs_approval, attestation replay | Yes. Mutation test remains the fail-closed source-integrity case. |
| `test_ops.py` holdout digest, digest-pinned compose, no GHA | Yes. Named-volume test is additive; `tmpfs:` is now forbidden in the test compose. |
| `test_structure.py` no `.github/workflows`, Trust CI files, immutable sandbox | Yes. K10 count is tighter (mermaid-only), not looser. |
| `test_backup.py` restore confirm, atomic dump | Yes. Tamper test now actually reaches digest. |
| `test_store.py` MemoryStore lease/dead/replay | Complements live class; not replaced. |
| `test_example_holdout_digest_matches_example_bundle` | Still present. |

No test reintroduces `.github/workflows/`, GitHub Actions, or a JSON/SQLite store.

Additional in-tree tests not in the named 2865fdc list (`test_database_roles.py`, `test_supply_chain.py`, backup retention) are source-locks of env/SQL/scripts that exist on this tree. They do not weaken the five characterizations.

---

## 4. Verification evidence (did not re-run)

- Route receipts dir `.grok-stack/runtime/receipts/f771ecaf458d/` is empty. Writing this report would stale a later `grok_verify` receipt anyway.
- `python3 scripts/grok_verify.py --mode pr` still discovers only root `tests/`, not `trust-ci/tests`. Handoff step 1’s second unittest command remains mandatory for Trust CI.
- Live proof (parent, not re-executed here): `tests.test_postgres_integration` 8/8 executed and passed with `TRUST_CI_TEST_DATABASE_URL`; `trust-ci/scripts/postgres-restart-drill.sh` printed PASS. Change-package `tasks.md` records that checkbox. This evidence directory does not duplicate the stdout; parent work is the source.
- `__pycache__` includes `test_postgres_integration.cpython-312.pyc` and `postgres_restart_probe.cpython-312.pyc` (bytecode from a prior run, not a bound receipt).

This report is local preflight. It is not the App-owned policy-epoch check.

---

## 5. Gaps (not fail)

- **Draft HTTP path.** Parser is tested; `TestClient` still posts `draft: False`. A second draft filter in `api.py` after parse would not be caught. Residual only: `api.py` currently has none.
- **`ready_for_review` / `synchronize`+draft.** Supported in code; only default `opened`+draft is asserted. Closed+draft is covered.
- **No dedicated constructor unit test** (`WorkspaceMutationError(('a','b')).paths`, 20-path truncation). The runner mutation test is the load-bearing case.
- **`GitWorkspace` vs runner Protocol.** Runner Protocol/`_run_command` call `assert_unchanged`; `GitWorkspace` only defines `assert_unmodified`. FakeWorkspace implements the Protocol name, so the mutation test cannot see a production AttributeError. Pre-existing wiring gap; belongs to code review as much as tests. Not introduced by the tuple constructor lock.
- **Mermaid pairwise is still whole-README.** Count is mermaid-only (the actual 2865fdc fix). A prose `Route --- Skills` could theoretically satisfy a missing mermaid pair if the fence still had 45 other edges. Unlikely on this README; not a fail.
- **Restart unit test is a string lock.** It does not assert trap `--volumes` on the drill script (the integration script test does). Live PASS is parent-owned.
- **Size-mismatch branch** of `verify_backup` has no dedicated test (retention tamper uses a size-changing overwrite on `prune_backups`). Digest branch is the 2865fdc characterization.
- Live class does not cover GitHub-outage attestation replay, `cancel_pr`, or `requeue_for_approval` against PostgreSQL (MemoryStore/runner tests do). Restart probe checks job identity after restart, not lease/attempt fields.
- `grok_verify --mode pr` will not fail if Trust CI tests go red. Operators must keep the handoff unittest discover on `trust-ci/tests`.

None of these would let the named 2865fdc regressions (draft ignore, constructor TypeError, size-mismatch masquerading as digest, whole-README 47-count, tmpfs restart) return unnoticed.

---

## Verdict (repeat)

**PASS.** Tests on `2865fdc` adequately characterize draft-PR enqueue, `WorkspaceMutationError` tuple construction via the mutation pipeline, same-size backup digest mismatch, mermaid-only K10=45, and named-volume restart-drill shape. Live PostgreSQL 8/8 and restart drill PASS are accepted from parent work. Residual gaps are documented and are not return-to-implementer items for this commit.
