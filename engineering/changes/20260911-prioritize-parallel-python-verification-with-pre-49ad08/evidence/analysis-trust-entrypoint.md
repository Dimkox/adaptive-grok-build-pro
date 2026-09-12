# Bounded architecture decision: Trust CI test entrypoint

Route `49ad08e34053`, worktree `adaptive-grok-build-pro-test-parallel`, base `64378d28c7b78cace463d96470c1898294b8f196`. Read-only analysis against the current helper; this report is the only analyst write. Root remains sole product author. This is an integration recommendation, not final review or a new test result.

## Smallest coherent implementation

Keep normal Core verification and its branch-coverage74 gate unchanged. Extend the already-owned `.grok-stack/adaptive_grok/python_test_runner.py` with proposed `run_trust_tests(repo_root: Path, workers: int) -> ProcessResult` and a small module `main(argv=None) -> int` with the closed supported choice `--suite trust-ci`. Reuse `PINS`, `RunnerError`, worker selection, bounded environment preparation and `execute`; do not introduce a new standalone script, scheduler or generic suite configuration.

Change the existing Makefile:24 target to `PYTHONPATH=.grok-stack python3 -m adaptive_grok.python_test_runner --suite trust-ci`, executed from the repository root. Resolve the control root as the invocation's repository root before changing any subprocess cwd. `selected_workers(repo_root)` reads the existing root opt-in and public override; `None` means the legacy serial backend and explicit0 means serial rollback. The private child cap remains after opt-in resolution. Report suite, effective worker count, backend, elapsed time and bounded test output; return nonzero on runner/config/dependency/test/collection/crash/timeout failure.

Do not infer the control root from `trust-ci` cwd or add a second opt-in under trust-ci. Do not modify `verification._python` to execute Trust CI as part of Core coverage. The existing Make target is the requested Trust entrypoint; Factory and PostgreSQL/restart lanes retain their own entrypoints.

## Exact command and environment boundary

For positive workers use the current interpreter, subprocess cwd `<repo>/trust-ci`, and this command shape:

```text
python -m pytest -p xdist.plugin -p no:cacheprovider --import-mode=prepend --rootdir=. -o python_files=test*.py -q -n N --dist=loadfile --max-worker-restart=0 --durations=20 -ra tests
```

For absent opt-in or explicit0 use that same Trust cwd and `python -m unittest discover -s tests`. Both select the same Trust test tree. Reject a missing Trust suite/tests directory before invoking unittest, whose empty discovery could otherwise exit successfully. No arbitrary pytest arguments, selectors, shell commands or environment-controlled filtering are needed.

The helper's current `_environment` at lines137-147 is Core-specific: it prepends root, root/tests and root/.grok-stack, and preserves an inherited PYTHONPATH tail. Trust needs absolute `<repo>/trust-ci/src`, `<repo>/trust-ci/tests`, and `<repo>/trust-ci` import roots. Prepare a fresh environment using the same sanitization, then replace PYTHONPATH with these exact Trust paths; do not carry Core tests or the Make recipe's relative `.grok-stack` into the changed cwd. A small explicit path argument or a Trust-specific override of the prepared dictionary suffices; avoid broad environment refactoring.

The two suites have distinct `tests` packages and incompatible top-level `_support` modules. Trust `_support.py:6-9` can add its src path only after `_support` has been imported, so the tests path is still necessary. A separate process and cwd prevent Core `_support`/tests contamination. Rootdir affects pytest configuration/collection and does not itself set the application import path.

Preserve existing PYTEST/COVERAGE/COV_CORE sanitization, explicit plugin loading, bytecode suppression, removal of public worker fan-out override in children and the private nested cap. Trust does not request pytest-cov, does not read Core `.coveragerc`, and does not generate or combine Core coverage. If reusing `_environment` requires a data-file argument, use its own temporary path and remove COVERAGE_FILE from the final unmeasured Trust environment; never reference a parent coverage file. Trust parallel execution requires the tested pytest/xdist pins; coverage/cov pins remain available for Core but are not necessary to execute this unmeasured suite. Explicit0 requires neither pytest nor xdist.

Reuse the existing POSIX parallel cleanup restriction and `execute` timeout/output ownership exactly. This includes stopping owned descendants even after controller exit; do not duplicate subprocess logic or add an automatic serial retry after a failed parallel run. Print stdout and stderr before returning the test outcome. Normal cancellation remains failure/interruption, never an apparent passing result.

Use the existing worker policy unchanged for this narrow patch: auto retains the bounded Core policy and explicit `GROK_TEST_WORKERS=N` is honored for Trust. Earlier observed Trust timings favored4 over22; users can select4 through the existing override. A new per-suite auto cap is optional future tuning, not required to expose the requested parallel target.

## Why loadfile is the correct Trust boundary

The baseline suite has213 unittest methods in18 files. `trust-ci/tests/test_postgres_integration.py:17-32` reads `TRUST_CI_TEST_DATABASE_URL` at import, skips its10 methods when absent, applies migrations in setUpClass, and truncates the same five tables in every setUp. `loadfile` keeps that entire file on one worker; worksteal/load would permit its methods to overlap and destroy one another's database state. The remaining ordinarily discovered files do not consume that database variable. The restart probe is a separate non-discovered `postgres_restart_probe.py`.

Preserve the DB variable exactly without inspecting or logging its value: unset keeps the existing203-pass/10-skip expectation; an explicitly configured disposable DB runs the same10 methods serially within their one worker. Do not silently unset a supplied DB URL to obtain a quicker green result. File grouping isolates this one test session, not simultaneous independent sessions against the same database; existing serial disposable/restart orchestration remains responsible for exclusive database ownership.

Other Trust files use temporary workspaces, per-test in-memory stores and mocked clients. `test_workspace.py` includes owned real subprocess termination and short deadlines; file grouping preserves local method order/isolation, while excessive worker counts can still add scheduling pressure. This does not justify skipping those tests or parallelizing PostgreSQL compose/restart entrypoints.

## File touches and acceptance

| File | Bounded purpose |
| --- | --- |
| `.grok-stack/adaptive_grok/python_test_runner.py` | Add Trust function/module CLI; share selection, version validation, environment sanitization and process ownership. Existing directory ownership and recursive packaging cover the module. |
| `Makefile` | Replace only existing trust-ci-test recipe; optional trust-ci-test-serial alias merely sets GROK_TEST_WORKERS=0. No script enrollment is required. |
| `tests/test_python_test_runner.py` | Focused synthetic Trust tree proving cwd/import selection, control-root opt-in, serial0, loadfile scheduling, failure propagation and preserved skip-related env. Existing process/coverage tests continue covering shared mechanics. |
| `README.md` and/or `trust-ci/README.md` | Show parallel target, shared worker override/serial rollback, separate Trust cwd and unchanged DB/restart ownership. No external trust-policy claim. |

Required checks for the owner: compare exact Trust collection identities against the existing213-method unittest selector; run the actual Make entrypoint with positive workers and0 on the same frozen tree; preserve203 passed/10 skipped when the dedicated DB variable is absent. A synthetic fixture should deliberately contain different Core/Trust `_support` values and a Trust src import, proving the entrypoint selects only Trust. Assert loadfile and max-worker-restart0 in the invoked command, verify malformed/missing dependencies fail before tests, and ensure an injected inherited pytest filter cannot omit methods. Verify no Core coverage or repository cache artifacts are emitted by this target and preserve the existing coverage74/full-verifier proof after final code changes.

Handoff fact: the minimal safe Trust addition is a module CLI sharing runner controls while separating the repository configuration root from the Trust execution/import root; loadfile is essential because all ten PostgreSQL methods share one truncating fixture.
