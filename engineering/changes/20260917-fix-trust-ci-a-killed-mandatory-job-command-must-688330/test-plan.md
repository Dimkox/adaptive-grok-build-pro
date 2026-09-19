# Test plan — interrupted Trust CI commands (#103)

`pytest` is not installed on this host; every run below is `python3 -m unittest`, and `pytest`/`pytest-xdist`
appear only inside the pinned runner image (irrelevant here: no test added needs them). 26 tests were added in
total — 20 in round 1, 6 across the two review rounds below (`test_ops` 14→29, `test_runner` 26→36,
`test_api` 21→22 test functions, counted with `grep -c "    def test_"` against `git show 2f66ba6:…`).

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Command killed by an outside SIGKILL records `aborted-by-signal` + `result.abort{signal:SIGKILL, signal_number:9, exit_code:137, command:'unit'}`, `status` still `failed`, attestation still `status='failed'` with exit codes `[0, 0, 137]` | `test_runner.RunnerTests.test_command_killed_by_external_sigkill_is_not_verification_failed` (red before the fix) |
| P0 | **Control:** a genuine verification failure (exit `1`) still records `verification-failed`, has no `result.abort`, and its check title does not say "aborted" | `test_control_genuine_verification_failure_keeps_its_failure_code` (green before and after) |
| P0 | Both finish sites classify, not just the main one: attestation replay on a re-claimed job keeps `aborted-by-signal` instead of rewriting it | `test_replayed_abort_attestation_keeps_the_interrupted_failure_code` |
| P0 | Every interpreted exit class is tested at the pure-function boundary and in the job record: `137`/`143` (docker-propagated), `-9`/`-15`/`-2`/`-1` (`subprocess` negative), `124`+marker → `aborted-by-timeout` | `test_ops.CommandAbortClassificationTests` + `test_negative_client_return_code_is_recorded_as_interrupted`, `test_sandbox_deadline_is_a_distinct_interrupted_class`, `test_holdout_command_kill_is_recorded_as_interrupted` |
| P0 | Timeout is claimed only on positive evidence: a bare `124` (a command's own exit code) stays `verification-failed`; the sandbox marker is proven to survive output truncation | `test_bare_124_without_the_sandbox_marker_is_not_claimed_as_an_abort`, `test_sandbox_timeout_marker_survives_output_truncation` |
| P0 | Nothing an abort class can read as success: `0/1/96/97/125/126/127/128/193/255/-65/-1000` → no abort | `test_abort_classes_can_never_read_as_success`, `test_ordinary_and_internal_failure_codes_are_never_aborts` |
| P1 | The platform contract itself is pinned by signalling a real child process (`Popen(['sleep','30'])` + `kill()` / `terminate()`), so the negative-return-code assumption is observed, not believed | `test_real_signalled_process_return_codes_are_interpreted_on_this_platform` |
| P1 | Synthetic internal codes stay non-abort in the pipeline (exit `97` source-integrity path) | `test_source_integrity_failure_is_not_reported_as_an_abort` |
| P1 | The cause reaches a reader without leaking output: `GET /jobs/{id}` returns `failure_code` + `result.abort` and still omits `stdout_tail`/`stderr_tail` content | `test_api.ApiTests.test_authorized_job_endpoint_exposes_the_interrupted_cause_without_output` |
| P1 | Migrations stay frozen and the packaged copies stay byte-equal | inherited `test_ops.OperationsTests.test_packaged_migrations_match_deployment_migrations`, `test_postgres_schema_has_durable_lease_and_replay_constraints` |

## Round-2 review closure (mutation-tested, not asserted)

The reviewer's findings were reproduced on the round-1 tree before being fixed. Measured "before" (each
mutation applied to the round-1 source, full suite `PYTHONPATH=trust-ci/src python3 -m unittest discover -s
trust-ci/tests`, then byte-exact restore verified by md5): `MU6` delete the runner `isinstance` guard →
`Ran 263 … OK (skipped=10)` survivor; `MU11` delete `if status == 'passed': return None` → `Ran 263 … OK`
survivor; `MU4` delete the marker's `\s*\Z` anchor → `Ran 263 … OK` survivor; and the classifier was not total
(`classify_command_abort(exit_code=None)` → `TypeError`, `exit_code='137'` → `TypeError`,
`exit_code=137.0` → `CommandAbort(signal_number=9.0)`).

| Finding | Fix | New test | Mutation state after the fix |
| --- | --- | --- | --- |
| **G-1 Major** — `classify_command_abort` was not total; totality depended on one caller-side guard, so `MU6` survived while a signed-but-malformed replay row reached the classifier (`verify_attestation` does not type-check `command_results`) | Type rejection moved **into** `classify_command_abort` (`isinstance(exit_code, bool) or not isinstance(exit_code, int) → None`); the runner check stays as a documented second layer | `test_ops.test_non_integer_exit_codes_yield_no_claim_instead_of_raising` (`None`, `'137'`, `''`, `True`, `False`, `137.0`, `[]`, `{}`, `object()`) and `test_runner.test_malformed_exit_codes_are_never_aborts` (through `_attested_command_abort`, incl. "a malformed row must not blind the loop to a real 137 later") | `MU6` (delete runner guard) → **survives as an equivalent mutant** — behaviour is identical because the classifier is total, which is exactly the requested property; `MU6b` (delete the classifier check) → **KILLED** `FAILED (failures=1, errors=6)`; deleting **both** layers → **KILLED** `FAILED (failures=2, errors=9)` by `test_malformed_exit_codes_are_never_aborts` + `test_non_integer_exit_codes_yield_no_claim_instead_of_raising` |
| **G-2 Major** — "a replayed pass records no failure code" was untested; `MU11` survived, so a passed job could be stored with `failure_code='verification-failed'` | (no behaviour change needed; `_terminal_failure_code` already returns `None` for `passed`) — the gap was coverage | `test_runner.test_passed_job_records_no_failure_code_at_all` (`assertIsNone(_terminal_failure_code('passed', None))`, the same with a live `aborted` argument, the two non-pass branches, plus an end-to-end passed run asserting `assertIsNone(job.failure_code)`), and `assertIsNone(replayed_job.failure_code)` added to the existing `test_signed_attestation_is_replayed_after_check_publication_failure` | `MU11` → **KILLED** `FAILED (failures=2)` by exactly those two tests. `grep -rn "assertIsNone(.*failure_code" trust-ci/tests/` now returns 4 hits (it was empty in round 1) |
| **G-4 Minor** — the `\Z` anchor was unpinned: a command that merely printed `command timed out after 120s` mid-output, exited `124`, would be misread as a sandbox timeout | (no behaviour change; the anchor was already correct) — the gap was coverage | `test_ops.test_timeout_marker_must_end_the_stored_tail` (marker first/mid-tail followed by output → no claim; marker with trailing newline or spaces → still `timeout`) | `MU4` → **KILLED** `FAILED (failures=1)` by that test. Note: `\Z` → `$` is a genuinely **equivalent** mutant here because the pattern already allows `\s*` before the end, so it is not chased |
| **G-3 Minor** — 129/130 and the `_MAX_SIGNAL_NUMBER` edge were unpinned (fail-closed direction, non-blocker) | (no behaviour change) | `test_ops.test_signal_range_boundaries_are_pinned` — `129→SIGHUP`, `130→SIGINT`, `137→SIGKILL`, `143→SIGTERM`, `192→SIGRTMAX(64)`, and `128`/`193`/`194`/`255` → no claim | Range-narrowing mutants (e.g. `_MAX_SIGNAL_NUMBER 64→63`) now surface at the boundary tests instead of silently dropping `SIGRTMAX` |
| **R2-2 Minor (round-2 code review)** — totality covered `exit_code` only; `classify_command_abort(exit_code=124, stderr_tail=None)` raised `TypeError` (`['x']`, `b'…'`, `5` likewise), the same asymmetry the G-1 fix had just removed | Non-string `stderr_tail` normalises to `''` before the regex: it loses the timeout *corroboration* but never suppresses an exit-status-proven kill | `test_ops.test_non_string_stderr_tail_yields_no_claim_instead_of_raising` — six non-string tails × `124` and `137`, a bytes tail spelling the marker, and an object whose `__str__` **is** the marker (so `str()` coercion is refused too) | MT1 delete the normalization → **KILLED** `FAILED (errors=7, skipped=10)`; MT2 `str(stderr_tail)` → **KILLED** `FAILED (failures=1, skipped=10)`; MT3 accept+decode `bytes` → **KILLED** `FAILED (failures=2, skipped=10)` |

## Automated checks

- Unit: `cd /home/pall/grok-projects/adaptive-grok-build-kill && PYTHONPATH=trust-ci/src timeout 900 python3 -m unittest discover -s trust-ci/tests` → `Ran 269 tests` / `OK (skipped=10)` (base `2f66ba6` was `Ran 243 tests` / `OK (skipped=10)`; +26 tests, the 10 skips are the PostgreSQL-integration module, which needs the live container this host does not provide).
- Red-before-green on the round-2 additions: the same discover command on the round-1 source with only those tests
  present reported `Ran 268 tests … FAILED (failures=1, errors=6, skipped=10)` (268 collected at that point — the
  `stderr_tail` arm arrived in the next round, taking the suite to 269). All seven lines came from
  `test_non_integer_exit_codes_yield_no_claim_instead_of_raising`, the one test that exercises totality directly
  against the classifier. The other four were green immediately by design: they are pins whose job
  is to turn red under the corresponding mutation (measured in the table above). The R2-2 arm ran in the reverse
  order — written against the already-total-`exit_code` code, red there (`Ran 1 test … FAILED (errors=7)`), green
  only after the `tail = stderr_tail if isinstance(stderr_tail, str) else ''` fix.
- Focused: `PYTHONPATH=trust-ci/tests python3 -m unittest test_ops test_runner test_api` → `Ran 87 tests` / `OK`.
- Integration: not executed here — `trust-ci/tests/test_postgres_integration.py` self-skips without `TRUST_CI_TEST_DATABASE_URL` (it runs in `make trust-ci-postgres-test`/the runner image, so the durable `PostgresStore.finish` write of the new column value is exercised only there and in the App check).
- Contract: `python3 scripts/grok_spec.py validate --gate engineering/changes/20260917-fix-trust-ci-a-killed-mandatory-job-command-must-688330/change-spec.yaml` → `"ok": true`, `"errors": []`, `"profile": "gate"`, 6 mapped ACs, `unmapped_ids: []`; `python3 -m unittest tests.test_change_spec -q` → `Ran 30 tests … OK`.
- Frozen-SQL proof (INV-002): `git diff --name-only 2f66ba6 -- '*.sql'` → empty; `ls trust-ci/sql/*.sql | wc -l`
  → `3`; `ls factory/src/adaptive_factory/resources/*.sql | wc -l` → `20`, last
  `020_execution_v2_priced_usage.sql`; `git ls-tree -r --name-only v2.0.13 | grep -c
  'factory/src/adaptive_factory/resources/.*\.sql'` → `18` (the referent of the `"001-018"` string, which lives
  in `PROJECT_STATE.json`/`README.md`/`START_HERE.md`/`CHANGELOG.md`, not in `AGENTS.md`:
  `grep -c "018" AGENTS.md` → `0`).
- E2E: none (no deployed service is updated by this commit).
- Static analysis: `python3 -m ruff check` on every changed file → `All checks passed!`; `python3 -m compileall -q trust-ci/src trust-ci/tests` → exit 0. `ruff format` is deliberately not applied: the repo pins lint rules `E4/E7/E9/F` only and the tree uses single quotes.
- Root suite (the other mandatory CI command, re-run after the round-2 source change): `timeout 1500 python3 -m unittest discover -s tests -t .` → `Ran 759 tests` / `OK (skipped=1)` / exit 0, unchanged from round 1 (this change adds no root test).

## Manual checks and disclosed limits

- Vocabulary audit: `grep -rn "'verification-failed'" trust-ci/src` now returns exactly one hit — the
  `_VERIFICATION_FAILED` constant at `runner.py:263` — because both finish sites go through
  `_terminal_failure_code`; `grep -rn "aborted-by" trust-ci/src` returns exactly one source hit, the
  `CommandAbort.failure_code` mapping at `sandbox.py:47`, so the two new values have one minting site.
- Operator distinction after the fix, on the same query the issue used:
  `select status, failure_code, result->'abort' from trust_ci_jobs where pr_number = <n>;` → the kill row reads
  `failed | aborted-by-signal | {"kind":"signal","command":"repository-verification","exit_code":137,"signal":"SIGKILL","signal_number":9,"failure_code":"aborted-by-signal"}`
  while a real failure reads `failed | verification-failed | NULL`.
- **Disclosed asymmetry (review F3):** an `aborted-by-timeout` classification cannot be recovered on the
  attestation-replay path, because the signed `command_results` rows carry no stderr and the marker is the
  timeout's only evidence; a replayed timeout therefore falls back to `verification-failed` (fail-safe: still
  non-success, never a certification), while a signal kill keeps its class on both paths. Recorded in
  `requirements.md` and `architecture.md`; not fixed, because fixing it means widening the signed attestation
  format.
- Not verified (stated, not implied): the misclassified PR #102 row is unchanged; no OOM-vs-external-kill
  separation is delivered; the durable write through `PostgresStore.finish` is not exercised on this host.
