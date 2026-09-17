PASS

# test_review — 20260917-fix-trust-ci-a-killed-mandatory-job-command-must-688330 (route 68833064bec9)

Audited as evidence, not believed. Every added test was mutation-checked against the **real** tree (source
mutated, suite run, file restored byte-exactly; sha256 of `git diff 2f66ba6 -- <3 src files>` =
`655b1a5cef011f1b…` identical before and after the battery; `git status --porcelain` unchanged).
No test was found that passes for the wrong reason. Two stated clauses have **zero** tests (G-1, G-2 below).

## Real invocations on this host (pytest is NOT installed: `python3 -m pytest --version` → `No module named pytest`)

- `make trust-ci-test` = `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests`
  → `Ran 263 tests in 7.120s` / `OK (skipped=10)` (the 10 skips = `test_postgres_integration.py`).
- The brief's suggested `… discover -s trust-ci/tests -t trust-ci` **does not work here** — `Ran 85 tests`
  `FAILED (errors=14)`, `ModuleNotFoundError: No module named '_support'`. Invocation artifact, not a product defect.
- Focused: `PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest test_ops test_runner test_api` → `Ran 81 tests` / `OK`.
- `python3 -m ruff check <6 changed files>` → `All checks passed!`
- Base arithmetic verified: worktree copy at base `2f66ba6` src+tests → `Ran 243 tests` (+20 = 263 ✓; 9 failures
  in that scratch are `test_m0_invariants` reading repo files I did not copy — path artifact of the scratch only).

## Coverage map (criterion → test → mutation that proves the arm non-vacuous)

| Criterion | Test(s) | Mutation killed? |
| --- | --- | --- |
| AC-001 signal → `aborted-by-signal` + `result.abort{kind,signal,signal_number,exit_code,command}` | `test_ops.test_docker_propagated_sigkill/sigterm_exit_is_a_signal_abort`, `test_negative_return_code_of_the_container_client_is_a_signal_abort`, `test_abort_detail_and_stored_member_carry_the_cause`, `test_real_signalled_process_return_codes_are_interpreted_on_this_platform`; `test_runner.test_command_killed_by_external_sigkill_is_not_verification_failed` (+`…sigterm…`, `…negative_client_return_code…`, `…holdout_command_kill…`) | MU1 `_SIGNAL_BASE 128→129` → `Ran 81 … FAILED (failures=8)` (`'SIGFPE' != 'SIGKILL'`); MU5 drop the negation → `failures=8`; MU12 live site back to `verification-failed` → whole suite `FAILED (failures=5, skipped=10)` |
| AC-002 `124`+marker → `aborted-by-timeout`, bare `124` not claimed, marker survives truncation | `test_ops.test_sandbox_deadline_exit_with_its_marker_is_a_distinct_timeout_abort`, `test_bare_124_without_the_sandbox_marker_is_not_claimed_as_an_abort`, `test_sandbox_timeout_marker_survives_output_truncation`; `test_runner.test_sandbox_deadline_is_a_distinct_interrupted_class` | MU2 drop the `stderr` requirement → `FAILED (failures=1)` (`CommandAbort(kind='timeout'…) is not None`) |
| AC-003 non-abort keeps `verification-failed` (1/96/97/125/128/193/255/0, status stays `failed`) | `test_ops.test_ordinary_and_internal_failure_codes_are_never_aborts`; `test_runner.test_control_genuine_verification_failure_keeps_its_failure_code`, `test_source_integrity_failure_is_not_reported_as_an_abort` | MU14 `_SIGNAL_BASE 128→0` → control red; MU13 `→96` → source-integrity (exit 97) control red. Both controls green **pre- and post-fix** ✓ |
| AC-004 replay keeps `aborted-by-signal`, `replayed` still true | `test_runner.test_replayed_abort_attestation_keeps_the_interrupted_failure_code` | MU9 replay site ignores the attested abort → `FAILED (failures=1)` (`'verification-failed' != 'aborted-by-signal'`). "replayed pass records no failure code" → **untested (G-2)** |
| AC-005 `GET /jobs/{id}` shows `failure_code`+`result.abort`, still redacts output | `test_api.test_authorized_job_endpoint_exposes_the_interrupted_cause_without_output` | MU8 delete `'abort'` from `_public_result` allowlist → `ERROR … KeyError: 'abort'`; redaction asserted by 3 `assertNotIn` |
| AC-006 check title/summary states abort, conclusion stays `failure` | same runner tests (`assertIn('aborted'/'SIGKILL'/'SIGTERM', title)`, `assertIn('SIGKILL', summary)`, `conclusion == 'failure'`) | MU7 `_abort_check_title → None` → `FAILED (failures=2)`. Replay-path title/summary text → **untested (G-4)** |
| INV-001 pure+total, malformed/non-integer exit code yields no abort | none for the non-integer clause | MU6 delete `isinstance(exit_code, bool) or not isinstance(exit_code, int): continue` → `Ran 81 … OK` (**survivor, G-1**) |
| INV-002 001-018 + packaged copies byte-equal | inherited `test_ops.test_packaged_migrations_match_deployment_migrations` (parity only, `assertGreaterEqual(len, 2)` — does **not** freeze the 18-file set), `test_postgres_schema_has_durable_lease_and_replay_constraints` (does not assert the `status IN (…)` CHECK list) | Proven by diff instead: `git diff --name-only 2f66ba6 -- trust-ci/sql trust-ci/src/adaptive_trust_ci/resources` → empty |
| FORBID-001 an abort read as success/passed | `test_ops.test_abort_classes_can_never_read_as_success`, `conclusion=='failure'` assertions, `test_…sigkill…` asserts `payload.status=='failed'` with exit codes `[0,0,137]` | Would go red if `failure_code` regressed to `verification-failed`/contained `passed` (verified by reading the predicate: `endswith('signal') or endswith('timeout')`) |
| FORBID-002 no new status/migration/backfill/PR #102 rewrite | no test (not testable on this host) | Diff shows no SQL, no status-vocabulary change; the PR #102 row is untouched by construction (source-only fix) |

## Red-before-green reproduced (base `2f66ba6` src + new tests, in `/tmp/rbg-688330`, worktree untouched)

`PYTHONPATH=src:tests python3 -m unittest test_ops test_runner test_api` →
```
Ran 57 tests in 0.707s
FAILED (failures=6, errors=2)
ImportError: cannot import name 'classify_command_abort' from 'adaptive_trust_ci.sandbox' (…)sandbox.py
  File "/tmp/rbg-688330/trust-ci/tests/test_api.py", line 467 … self.assertEqual(payload['result']['abort']['signal'], 'SIGKILL')
AssertionError: 'verification-failed' != 'aborted-by-signal'   (x4 runner tests + one '!= aborted-by-timeout')
```
6 runner failures + 1 api error + `test_ops` import error (11 tests collapsed) = **18 red**, and the 2 controls
ran green (`Ran 34 … FAILED (failures=6)` in `test_runner` alone, controls absent from the FAIL list).
Isolation run (`/tmp/rbg2-688330`, new sandbox+api, base runner only) → `Ran 59 … FAILED (failures=6)`: all 24
`test_ops` tests green, so the classifier boundary and the runner wiring are each separately pinned.
The `success_metric` claim (20 added = 11+8+1, 18 red, 2 controls) is **accurate**.

## Gaps (severity, with the command that shows it)

- **G-1 Major — INV-001 non-integer/absent clause has no test and its guard is a survivor.** `MU6` (delete the
  `isinstance` guard in `runner._first_command_abort`) → `Ran 81 tests … OK`. Proved load-bearing by direct call:
  `classify_command_abort(name='unit', exit_code=None)` → `TypeError: '<' not supported between instances of
  'NoneType' and 'int'`, while `_first_command_abort([('unit', None, '')])` → `None` only because of the guard;
  `verify_attestation` does **not** type-check `command_results` rows, so a signed-but-malformed replay row reaches it.
  `grep -rn "exit_code=\(None\|True\|False\|'\)" trust-ci/tests/*.py` → no hits. Fix: add
  `test_malformed_exit_codes_are_never_aborts` feeding `None`/`'137'`/`True` through `_attested_command_abort`.
- **G-2 Major — AC-004 "a replayed pass still records no failure code" is untested.** `MU11` (drop
  `if status == 'passed': return None` from `_terminal_failure_code`) → `Ran 263 … OK (skipped=10)`; a passed job
  would carry `failure_code='verification-failed'`. `grep -rn "assertIsNone(.*failure_code" trust-ci/tests/` → no hits.
- **G-3 Minor — AC-001 edge values 129/130 unpinned; `_MAX_SIGNAL_NUMBER` only bounded to [33,64].** `MU3`
  (`64→33`) → `Ran 81 … OK`. Direction is fail-closed (a SIGRTMAX-range kill degrades to `verification-failed`).
- **G-4 Minor — the marker's end-of-tail anchor is unpinned.** `MU4` (`…[0-9.]+s\s*\Z` → `…[0-9.]+s`) → `OK`: a
  command that merely echoes `command timed out after 120s` mid-stderr is misread as `aborted-by-timeout`
  (wrong cause, still non-success). `MU10` (replay summary loses `detail()`) → `OK`, so AC-006's replay wording is
  unpinned even though the durable record is pinned by MU9.
- **G-5 Minor — exit 96 (synthetic spec-metadata) is pinned only at the classifier boundary**, never in a runner
  pipeline test (`grep -n 96 trust-ci/tests/test_runner.py` → only pre-existing `typed-spec-metadata` name asserts).

## What is unproven on this host (stated, not implied)

- **The PostgreSQL durable write of the new values is NOT proven here.** No test calls `PostgresStore.finish`
  with `aborted-by-signal`/`aborted-by-timeout` or an `abort` result member; `test_runner`/`test_api` use
  `MemoryStore`, and `test_postgres_integration.py` self-skips (`@unittest.skipUnless(DATABASE_URL…)`,
  `TRUST_CI_TEST_DATABASE_URL` unset here) → the 10 skips. By inspection the path is safe: `001_schema.sql:20`
  is `failure_code text` with **no** CHECK, and `store.py:416` writes `result = %s::jsonb, failure_code = %s`.
  Closing test: in `PostgresIntegrationTests`, `store.finish(job_id, worker, 'failed', {'abort': CommandAbort(…).to_result(),
  'commands': […]}, failure_code='aborted-by-signal')` then re-read through a **fresh** `PostgresStore(DATABASE_URL)`
  and assert both the column and `result->'abort'->>'signal'`; run via `make trust-ci-postgres-test`.
- The deployed Trust CI service is not updated by this commit, so no observation of real kills (137 from an OOM
  or an external `docker kill`) exists here; the classifier's platform assumption *is* observed locally by
  `test_real_signalled_process_return_codes_are_interpreted_on_this_platform` (real `Popen(['sleep','30'])` +
  `kill()`/`terminate()`), which MU5 kills. No xdist/pytest path runs on this host.
- Whether an OOM kill and an operator kill should be separable, and the already-misclassified PR #102 row, are
  out of scope by the spec and are not claimed by any test.
