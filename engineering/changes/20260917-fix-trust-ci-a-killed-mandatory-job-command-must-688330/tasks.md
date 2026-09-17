# Tasks — interrupted Trust CI commands (#103)

## Round 1

- [x] Reproduce the defect from the code, not the report: read `sandbox.ContainerExecutor.run`,
  `runner.JobRunner.process` and `store.finish`, plus `001_schema.sql`, and confirm the two flattening sites
  (`runner.py:517` live, `runner.py:345` replay) and that `status` is CHECK-constrained while `failure_code` is
  free text and `result` is `jsonb`. Ruled out a schema change before scoping, so no migration was considered.
- [x] Tests first, observed red on the base: 6 `test_runner` cases and 1 `test_api` case failed with
  `'verification-failed' != 'aborted-by-signal'`-style assertions and `test_ops` did not even import
  (`FAILED (failures=6, errors=2)`); the two controls (exit `1`, source-integrity `97`) passed and stayed passing.
- [x] Implement the smallest vertical change: `classify_command_abort` + `CommandAbort` in `sandbox.py`;
  `_first_command_abort` / `_live_command_abort` / `_attested_command_abort` / `_terminal_failure_code` /
  `_abort_check_title` in `runner.py`; optional `title` on `_complete_check`; `abort` in the `api.py`
  redaction allowlist. No new module, no new dependency, no status value, no SQL.

## Round 2 — independent review closure (code_review PASS, test_review PASS with G-1/G-2 Major + G-3/G-4 Minor)

- [x] Reproduced the reviewer's four measurements on the round-1 tree before changing anything: `MU6` and
  `MU11` and `MU4` each left `Ran 263 … OK (skipped=10)`; direct calls proved
  `classify_command_abort(exit_code=None)` and `(exit_code='137')` raised `TypeError` and
  `(exit_code=137.0)` returned `CommandAbort(signal_number=9.0)`; `grep -rn "assertIsNone(.*failure_code"
  trust-ci/tests/` was empty.
- [x] **G-1** — totality moved into `classify_command_abort` itself (`isinstance(exit_code, bool) or not
  isinstance(exit_code, int) → None`); the runner check stays as a documented second layer (so it is *not*
  claimed to protect the classifier). New tests:
  `test_ops.test_non_integer_exit_codes_yield_no_claim_instead_of_raising` (`None`, `'137'`, `''`, `True`,
  `False`, `137.0`, `[]`, `{}`, `object()`) and
  `test_runner.test_malformed_exit_codes_are_never_aborts` (through `_attested_command_abort`, plus a real 137
  later in the same attestation and an empty list). Only these two go red when **both** layers are removed.
- [x] **G-2** — `test_runner.test_passed_job_records_no_failure_code_at_all` (unit on
  `_terminal_failure_code('passed', None)`/`('passed', <live SIGKILL abort>)`/`('failed', None)`/
  `('failed', <abort>)` **and** an end-to-end passed run with `assertIsNone(job.failure_code)`), plus
  `assertIsNone(replayed_job.failure_code)` on the existing passed-replay test. The grep above now returns 4 hits.
- [x] **G-4** — `test_ops.test_timeout_marker_must_end_the_stored_tail`: the marker mid-tail (with output after
  it) is not an abort, while the marker with trailing whitespace still is.
- [x] **G-3** — `test_ops.test_signal_range_boundaries_are_pinned`: `129→SIGHUP`, `130→SIGINT`, `137→SIGKILL`,
  `143→SIGTERM`, `192→SIGRTMAX`, and `128`/`193`/`194`/`255` → no claim.
- [x] Re-measured the mutations after the fix (each applied, full suite run, byte-exact restore proven by md5):
  `MU6` delete runner guard → survives **as an equivalent mutant** (behaviour identical because the classifier is
  now total, which is the requested property); `MU6b` delete the classifier check → **KILLED**
  `FAILED (failures=1, errors=6, skipped=10)`; both layers deleted → **KILLED**
  `FAILED (failures=2, errors=9, skipped=10)` by the two new tests; `MU11` → **KILLED** `FAILED (failures=2)`;
  `MU4` → **KILLED** `FAILED (failures=1)`. `\Z→$` is genuinely equivalent (the pattern already allows `\s*`)
  and is not chased.
- [x] Reviewer-record corrections in this package (issue #117 class — no citation that one `ls` refutes):
  **F1** the "migrations `001`-`018`" wording replaced in the five places I had written it
  (`change-spec.yaml` objective + INV-002, `release.md`, `requirements.md`, `tasks.md`, `state.json` history
  row) with measured facts — `git diff --name-only 2f66ba6 -- '*.sql'` → empty,
  `ls trust-ci/sql/*.sql | wc -l` → `3`, `ls factory/src/adaptive_factory/resources/*.sql | wc -l` → `20`
  ending at `020_execution_v2_priced_usage.sql`, **18** of that factory set at tag `v2.0.13`;
  **F2** the `aborted-by-signal` operator advice rewritten to "the command reached no verdict", never "not a
  code problem", with who-signalled explicitly unknown and an OOM caused by the PR's own tests called out as a
  PR defect; **F3** the timeout-replay asymmetry disclosed in `requirements.md`, `architecture.md` and
  `test-plan.md` (fail-safe fallback to `verification-failed`, unfixed by design); **F4** the bool/`isinstance`
  claim removed from any wording that suggested it protects the classifier.
- [x] **R2-1 (round-2 code review)** — that F1 fix was itself wrong in its *source*: four lines attributed
  `001-018` to `AGENTS.md`, which contains no such number (`grep -c "018" AGENTS.md` → `0`; its data rule at
  `AGENTS.md:130` says only "All schema changes use versioned migrations"). Real bearers, each re-checked
  individually: `PROJECT_STATE.json` `current_unreleased_change.frozen.postgresql_migrations` (line 261; also
  352, 625 and `active_delivery.integrated_stack.migrations` at 889), `README.md:32`, `START_HERE.md:57`,
  `CHANGELOG.md:75`. `tasks.md` also claimed the replacement was done "everywhere", which is what the same grep
  refuted. Now reworded to the artifact-anchored form in `change-spec.yaml` INV-002, `requirements.md`
  INV-002, `release.md` and here; closure is claimed only for what the grep can refute, and the standing check
  is `grep -rn "AGENTS.md" <package> | grep -v /evidence/ | grep 018` → every remaining line, self-referential
  ones included, is a negation or a record of this correction, never a positive attribution; no count of those
  lines is quoted here, because editing this very package moves it; `grep -c "018" AGENTS.md` → `0` is the
  refutation of the original claim. No line anywhere in this
  package now asserts that `AGENTS.md` carries that range.
- [x] **R2-2 (round-2 code review)** — totality was closed for `exit_code` but not for `stderr_tail`:
  reproduced `classify_command_abort(name='u', exit_code=124, stderr_tail=None)` →
  `TypeError: expected string or bytes-like object, got 'NoneType'` (and `['x']` → `got 'list'`,
  `b'…'` → `cannot use a string pattern on a bytes-like object`, `5` → `got 'int'`; with `exit_code=137` all
  four passed silently only because `and` short-circuits). Fixed the same way: `tail = stderr_tail if
  isinstance(stderr_tail, str) else ''` before the regex, so a non-string tail removes the *corroboration*
  without suppressing an exit-status-proven kill; `stderr_tail` annotated `Any` and the docstring states both
  halves. New arm `test_ops.test_non_string_stderr_tail_yields_no_claim_instead_of_raising` (red before the
  fix: `Ran 1 test … FAILED (errors=7)`). Mutations: delete the normalization → **KILLED**
  `FAILED (errors=7, skipped=10)`; `str()` coercion → **KILLED** `FAILED (failures=1, skipped=10)`;
  accepting-and-decoding `bytes` → **KILLED** `FAILED (failures=2, skipped=10)`. Arm attribution measured: with
  the `__str__`-object arm removed the bytes arm still killed the `bytes` mutant but **survived** `str()`
  coercion, so both arms are load-bearing for different mutations.
- [x] `evidence/review-response.md` written for both rounds: disposition + proving command per finding (G-1..G-4,
  F1..F4, R2-1, R2-2), including the two mutants deliberately not chased (equivalent) and the limits of the
  evidence. Reviewer artifacts (`review-code.md`, `review-test.md`, round-2 files) untouched.
- [x] Caught by the typed gate, then fixed: a widened `objective.success_metric` broke
  `grok_spec.py validate --gate` with `$.objective.success_metric: string longer than maxLength` (512); the
  detail moved into this file and `test-plan.md`, and every string field was length-audited afterwards.

## Verification on the final tree

- `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests` → `Ran 269 tests` / `OK (skipped=10)`.
- `PYTHONPATH=trust-ci/tests python3 -m unittest test_ops test_runner test_api` → `Ran 87 tests` / `OK`.
- `python3 -m ruff check` on the six changed Python files → `All checks passed!`;
  `python3 -m compileall -q trust-ci/src trust-ci/tests` → exit 0; `git diff --check` → exit 0.
- `python3 scripts/grok_spec.py validate --gate --json change-spec.yaml` → `{'ok': True, 'errors': [], 'profile': 'gate'}`,
  6/6 ACs mapped, `unmapped_ids: []`, `success_metric` 381 chars (cap 512).
- Root: `python3 -m unittest discover -s tests -t .` → `Ran 759 tests` / `OK (skipped=1)` / exit 0 (unchanged
  count: this change adds no root test). Because `tests.test_governance`, `tests.test_governance_fitness`,
  `tests.test_structure` and `tests.test_change_spec` read `decisions.md`/`mistakes.md`/typed specs (all edited
  in this wave), those four were re-run after the source fix and after the correction of those records:
  `Ran 112 tests` / `OK`. Package Markdown keeps being edited after those runs, which is safe because no root
  test reads this package: `grep -rln "688330" tests/` → no match, and the `engineering/changes/2026…` paths
  that do appear in `tests/` name other packages or temp roots (`test_project_state.py:401,547-548`,
  `test_structure.py:65,764`, `test_verification_doctor.py:1221-1243`, `test_policy.py:102`,
  `test_manifest_package.py:1410`).
- Byte-determinism for the coordinator (md5, before the round-2 residual fixes → after):
  `sandbox.py b46520ff… → 9c530687…`, `test_ops.py 633db2b6… → 95af0130…`; unchanged: `runner.py d1089aac…`,
  `api.py 01219f9d…`, `test_runner.py 84b1f30d…`, `test_api.py 464fab12…` — i.e. only the classifier and its
  test arm moved, exactly the scope of R2-2.
- [ ] Independent round-2 `code_reviewer` / `test_reviewer` passes and `grok_verify --mode pr` (coordinator),
  then branch push + pull request and the App-owned exact-SHA check — which will likely also need a
  human-signed `governance` approval, because `trust-ci/**` is inside that approval-rule glob.
