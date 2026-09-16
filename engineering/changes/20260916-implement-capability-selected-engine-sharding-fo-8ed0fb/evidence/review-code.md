PASS

# Code review — capability-selected engine sharding (retake of closed defect 33)

Reviewer: route `code_reviewer` (read-only). Scope: `git diff e7d0f72bf834b75eb543d9424ee47c7829cc65c0..275b804a` on
`feature/python-test-runner-engine-select` (clean tree at start and end). Typed authority:
`change-spec.yaml` AC-001..AC-004, INV-001..INV-002, FORBID-001..FORBID-002. Host condition: Python 3.12.3 with
**no importable pytest/xdist/pytest_cov** (`find_spec` → None for all three) and `coverage` 7.15.4 — i.e. the
Trust CI image condition that killed PR #33.

Verdict rationale: no Critical. The re-take contract holds in the code the gates actually consume (pre-execution
degrade, strict pins when the engine exists, no mislabeled backend in `python-unittest` details, no-opt-in
self-verification unchanged). The Important items are a disclosure line in an unreferenced developer CLI and
overstated package docs; both are cheap `forward_fix` additions and are recommended before the check re-run.

## Findings

1. **Important — the Trust CI CLI reports the requested worker count for a degraded serial run**
   `.grok-stack/adaptive_grok/python_test_runner.py:270` (`workers, _engine = select_engine(...)`, engine discarded)
   and `:287,292` (`workers = selected_workers(root) or 0`; `print(f'Trust CI: workers={workers}; ...')`).
   `run_trust_tests` returns only `ProcessResult`, so `main()` cannot know the engine it actually used.
   Failure scenario (reproduced): on this pytest-free interpreter, a temp fixture with `trust-ci/tests` and
   `GROK_TEST_WORKERS=8` printed `Trust CI: workers=8; seconds=0.101; exit=0` while the run was one serial
   `python3 -m unittest discover -s tests` (only the degraded path can be taken here). The trust lane records no
   `engine` anywhere, so the request is masked and a parallel worker count is claimed for a pass that used none —
   the class of claim FORBID-002/AC-001 exist to prevent. This head fixed exactly this bug in the Core lane by
   adding `workers = core.workers` (absent in preserved head 6d72d4c); the trust lane was left unfixed.
   Fix: return the engine from `run_trust_tests` (or a small result dataclass) and print
   `workers={used} engine={engine}`. Blast radius is limited: nothing in `scripts/`, `trust-ci/` or
   `.grok-stack/` invokes `--suite trust-ci` (only `tests/test_python_test_runner.py:88`), and the mandatory
   `trust-ci-unittest` policy command is plain unittest argv, so no gate consumes the line.

2. **Important — AC-001/AC-002's parallel arm has no real-execution coverage on any gate this repo runs, and the
   package docs overstate what is proven.** `tests/test_python_test_runner.py:96`, `:324` relax the shard-count
   assertions to `1` when the engine is absent; `:266-267` `continue`s the `missing-worker` subTest silently (no
   `skipTest`, so `Ran 19 tests … OK` shows no skip). `test_inherited_pytest_selection_cannot_omit_tests` and
   `test_unittest_filename_pattern_is_preserved` pass through the serial path on this host. AC-002 is proven only
   with `patch('adaptive_grok.python_test_runner.parallel_engine_ready', return_value=True)` (`:149`), never with a
   real xdist run. `_pytest_command` (`-p xdist.plugin` under `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `--dist`
   worksteal/loadfile, `--max-worker-restart=0`, `--cov-config` ordering), the worker-coverage combine and the
   `pytest_testnodedown` data-loss hook are therefore unexecuted locally *and* unexecutable by the App check
   (which runs `python3 -m unittest discover -s tests`). Contradicted text:
   `architecture.md` (“the skip is explicit”, “instead of weakening coverage”) and `test-plan.md` P0
   (“each method runs exactly once on **both engines**”).
   Failure scenario: a defect confined to the xdist command shape stays green on the CI image and only breaks an
   opted-in developer host — the same dev-green/CI-red asymmetry that closed PR #33 (its own record shows the
   reverse direction, CI-green tests failing on a pytest-free image). Fix: use `self.skipTest(...)` so the gap is
   visible, and record the xdist arm in `state.json`/evidence as *not yet exercised* rather than as covered.

3. **Minor — requested workers are not recorded in the Core check details.**
   `.grok-stack/adaptive_grok/verification.py:951` overwrites `workers` with `core.workers` before the summary and
   details are built (`:952-961`), so a degraded pass reads `unittest workers=0 … backend=unittest` with
   `versions={"engine":"unittest-degraded",…}` and no trace of the request. FORBID-002 states “the requested
   workers **and** the used engine are both recorded in the check details”; only the used value survives. Label
   correctness itself is fine (a degraded run can never print `pytest-xdist`, because `core.workers == 0`).

4. **Minor — the capability probe tests spec presence, not importability.**
   `python_test_runner.py:188-192` (`importlib.util.find_spec`). Failure scenario: a venv with `pytest`+`xdist`
   dist-info present but unimportable (missing `execnet`, broken install after a Python minor upgrade, vendored
   stub) → `select_engine` keeps `workers>0`, `_tool_versions` passes (metadata is present), and the child dies on
   plugin load — a hard post-execution failure, the outcome this retake exists to remove. Bounded by opt-in.
   Suggested: probe with `importlib.import_module` inside `try/except Exception` (cheap, in-process, still no
   network/install) instead of `find_spec`.

5. **Minor (ported, opt-in only) — an escaping `TimeoutExpired` aborts the whole verify run.**
   `python_test_runner.py:103` `process.wait(timeout=10)` inside `_stop` can raise if the child sits in
   uninterruptible sleep; the exception is not a `RunnerError`, so `verification.py:945`'s handler misses it and
   `verify()` dies with a traceback instead of emitting a failed `python-unittest` check (no receipt, no per-check
   evidence). Byte-identical to preserved head 6d72d4c, so not a regression; `except subprocess.TimeoutExpired:
   pass` in `_stop` closes it.

6. **Minor — opt-in file is inert-by-default but fail-loud, and is not gitignored.**
   `.grok-test-runner.json` is not ignored (`git check-ignore` → exit 1). A stray or committed file with any
   invalid shape now hard-fails `python-unittest` (+`coverage` in pr/release) at
   `verification.py:943-949`, where before this change nothing read that path. Related spec nit: INV-002 says
   “POSIX-only parallel (otherwise serial)”, but on non-POSIX an explicit integer worker count raises
   (`python_test_runner.py:210-211`); only `auto` degrades to 0 (`:71`). Both ported verbatim from head.

7. **Minor — SIG-001 “per-run durations line” only exists on the xdist arm.**
   `--durations=20` is part of `_pytest_command` (`python_test_runner.py:214`), so a degraded/serial pass emits no
   per-test durations, and `duration_hint` is left unset on both runner-produced checks.

## Verified by running (this host, no pytest)

- `PYTHONPATH=.grok-stack python3 -m unittest tests.test_python_test_runner` → **Ran 19 tests in 6.078s, OK**.
  The module imports only `unittest`/`unittest.mock`/stdlib — no `import pytest`, no network, no installer — so it
  is satisfiable in exactly the environment that killed the original PR (AC-004). `git status --porcelain` stayed
  empty after the run (all fixtures in temp dirs).
- `PYTHONPATH=.grok-stack python3 -m unittest tests.test_change_spec` → **Ran 30 tests, OK**.
- `python3 -m ruff check` on `.grok-stack/adaptive_grok/python_test_runner.py`,
  `.grok-stack/adaptive_grok/verification.py`, `tests/test_python_test_runner.py` → **All checks passed** (ruff 0.16.3).
- `python3 -m bandit -q -c bandit.yaml .grok-stack/adaptive_grok/python_test_runner.py` → no findings.
  `python3 -m compileall -q .grok-stack/adaptive_grok scripts` → exit 0 (the mandatory `compileall` shape).
- **Mandatory no-pytest gate command, end to end:** `python3 -m unittest discover -s tests` at repo HEAD →
  **Ran 741 tests in 387.595s, OK, exit 0**, tree clean afterwards. This is the exact argv of
  `trust-ci/config/policy.example.json` `root-unittest`.
- **AC-001 ordering, by reading and by probe:** `select_engine` runs before `_tool_versions` in both
  `run_core_tests:219-220` and `run_trust_tests:270-271`. Direct probe: `select_engine(8, True) → (0,
  'unittest-degraded')`, `select_engine(0, True) → (0, 'unittest')`, `parallel_engine_ready(False|True) → False`.
  With `pytest_cov` hidden but `pytest`/`xdist` visible, `select_engine(8, measured=True) → (0,
  'unittest-degraded')` → the measured lane withholds xdist, so coverage can never be silently skipped
  (degraded measured runs `coverage run --rcfile=… -m unittest discover -s tests`, and the degraded measured arm
  still pins `coverage` exactly). Trust CLI on this interpreter exits 0 with a serial pass instead of the original
  `pytest missing; install .grok-stack/config/python-test-requirements.txt` RunnerError.
- **AC-002 strictness:** `test_importable_but_mismatched_parallel_dependency_still_fails` passes with the engine
  forced ready and `metadata.version` raising — `python-unittest` = fail, message names the pin file, and zero
  test files were produced, i.e. no silent serial retry. No retry path exists in code (one `execute()` per
  decision, `run_core_tests:245`).
- **Concern 2 (would-be Critical) is clean — the repo self-verifies without opt-in.** No
  `.grok-test-runner.json` at root and no ambient `GROK_TEST_WORKERS`: `selected_workers(real root) → None`, so
  `run_core_tests` (and every pin check) is never reached on the repo's own path. Stubbed-`_command_check` probe of
  `verification._python(root, 'pr')` emitted exactly
  `coverage run --rcfile=.coveragerc -m unittest discover -s tests` (900s) and
  `coverage report --rcfile=.coveragerc` (120s) — same commands/timeouts as base, only `COVERAGE_FILE` pointed into
  a private temp dir; `fast` mode still emits `python3 -m unittest discover -s tests`. `util.run` merges
  (`os.environ.copy()` then `update`), so the new `env=` cannot drop `PATH`/`HOME` — `_command_check`'s `env` is
  keyword-only, so no existing positional caller changed. `.coveragerc` sets no `data_file`, so both commands
  resolve to the same private file.
- **Port fidelity:** `diff` of `git show 6d72d4c:.grok-stack/adaptive_grok/python_test_runner.py` vs current shows
  **only** the intended hunks — `import importlib.util`, the new `parallel_engine_ready`/`select_engine`, the two
  inserted lines in `run_core_tests`, one in `run_trust_tests`. Config parsing, `_closed_object`, `selected_workers`
  caps (0..64, `auto` ≤ 28), `_GROK_TEST_CHILD`, `_environment` var stripping, `TIMEOUT`/`OUTPUT_LIMIT`,
  `_stop`/`_cancellation`/`execute`, `_tool_versions`, `_pytest_command` and the coverage-integrity block are
  byte-identical. `.grok-stack/config/python-test-requirements.txt` is byte-identical to head and matches `PINS`.
  `verification.py` base→HEAD is exactly the described wiring; vs head the only delta is `workers = core.workers`.
- **Process safety (#4):** `_cancellation` restores the previous SIGTERM handler in `finally` and re-raises
  `SystemExit(128+SIGTERM)`; `start_new_session=True` + `os.killpg` group kill on cancel/timeout/output-limit;
  `except BaseException: _stop(); raise`. `test_sigterm_cancels_owned_group_and_restores_previous_handler`,
  `test_timeout_stops_owned_descendant_process`, `test_controller_exit_stops_owned_descendant_process` and
  `test_output_limit_applies_even_when_process_exits_quickly` all pass here, including the handler-identity and
  exit-127 assertions.
- **INV-001 / FORBID-001 (#5):** changed-file list = runner, verification, requirements file, the 11 package docs,
  the new test module — **zero** paths under `trust-ci/`, `architecture/`,
  `.grok-stack/config/policy.json` or `.github/` (verified with `git diff --name-only` + grep). No
  `GROK_TEST_WORKERS`/`.grok-test-runner.json`/`adaptive_grok` reference exists in `trust-ci/` or `scripts/`, so
  the opt-in cannot influence the App-owned check. Nothing installs or reaches network: the diff contains no pip /
  subprocess-install / urllib / socket use; `find_spec` only probes, and the requirements file is referenced solely
  by the human-readable RunnerError message.
- **AC-004 second half:** `PROJECT_STATE.json` `work_inventory.retained_unresolved` still names the *original*
  head `6d72d4c859dded241b55e90ae9514ad428a7eb1b` (PR #33, closed_unmerged) and is untouched by this change.
- **Rollback claim:** reverting restores `_python`/`_command_check` and orphans the runner — `verification.py:25` is
  the only non-test importer of `python_test_runner` (grep), so the stated `forward_fix` holds.

## Limits

- No `pytest`/`xdist`/`pytest_cov` on this interpreter, so the xdist arm (command shape, distribution modes, worker
  coverage combine, worker data-loss hook, real pin-mismatch failure) could not be executed — only the degraded
  serial arm ran for real (see finding 2).
- The Trust CI image's actual package inventory is not observable from here; “no pytest” is taken from the
  `retained_unresolved` record and reproduced by this host's inventory.
- I did not run `scripts/grok_verify.py --mode pr` end to end (architecture fitness, receipts and the other check
  lanes were not exercised); I ran the mandatory `root-unittest` argv plus the named test modules, ruff and bandit.
- Test-suite design/quality judgments beyond the contract checks above belong to the route's `test_reviewer`.
