# Independent code review: parallel Python verification

Status: **PASS — no open blocking code findings**. Reviewer architect acts as the user-approved independent code_reviewer substitute; root is the sole product author. Route49ad08e34053, branch perf/parallel-python-tests, base64378d28c7b78cace463d96470c1898294b8f196; review workdir `/home/pall/grok-projects/adaptive-grok-build-pro-test-parallel`. Product files were read only. This verdict covers the separated acceleration implementation and the repaired final source hashes below, excluding the runner-image bootstrap and any deployed authority.

## Closed findings and repair review

**P1, closed — SIGTERM left the owned suite running.** The initial review independently reproduced controller exit-15 with its newly created child group still alive; the reviewer removed that exact probe group afterward. In the reviewed repair, `.grok-stack/adaptive_grok/python_test_runner.py:105-159` scopes a temporary SIGTERM handler around process ownership, requires the main thread, records cancellation without abandoning cleanup, stops/reaps the owned group, restores the previous handler in finally, and exits143. Normal exception, timeout and already-exited-controller cleanup remain present. It does not claim to intercept SIGKILL or kill unrelated/detached sessions.

Independently reran only `python3 -B -m unittest tests.test_python_test_runner.PythonTestRunnerTests.test_sigterm_cancels_owned_group_and_restores_previous_handler -v`: **1 passed in0.230s**. This checks a real externally terminated controller and child, plus normal/missing-command handler restoration (`tests/test_python_test_runner.py:156-191`). A separate direct synthetic probe installed a custom prior handler, let an owned child send SIGTERM, caught cancellation, and observed `cancellation_exit=143` with `previous_handler_restored_after_cancel=True`. No pytest pool or full suite was started by this reviewer.

**Test-review configuration finding, closed in inspected code.** `_pytest_command` now selects `-c os.devnull` at lines187-192, so a discovered pytest.ini cannot supply addopts, norecursedirs or other suite-shrinking settings. Explicit cwd/rootdir, test*.py selector, required plugins and environment sanitization remain separate. This shared command covers Core worksteal and Trust loadfile. Updated fixtures exercise conflicting Core/Trust pytest.ini plus inherited PYTEST filters and a nested test; exact-once markers now use exclusive file creation so duplicate execution fails. The test reviewer owns the corresponding full synthetic revalidation; no unreported pool was run here.

## Other inspected behavior

- `verification.py:844-900` preserves generic project-marker pytest precedence, absent-opt-in legacy discovery, existing check names and other lanes. Opted-in0 selects the measured serial helper; private child capping follows opt-in selection. Legacy coverage receives an invocation-specific file instead of overwriting a parent. Present invalid/nonregular config fails before test execution.
- `python_test_runner.py:162-238` sanitizes inherited test/coverage controls; requires tested tool versions; uses one interpreter, fixed selectors and explicit plugins; rejects collection/test/worker/timeout failures without serial retry. Core owns fresh external temporary coverage files, performs a separate configured report/export, and rejects absent/corrupt/incomplete data or missing-worker diagnostics. `.coveragerc` remains unchanged with branch=True, existing sources/omits and fail_under74.
- `python_test_runner.py:241-270` separates the Trust configuration root from Trust execution/import roots, uses loadfile, preserves explicit0 serial discovery and configured DB environment semantics. Current Trust shared PostgreSQL fixture stays in one file; grouping does not promise isolation between separate concurrent DB sessions. Factory/restart code and sequencing are unchanged.
- Makefile:15-20 runs verify then trust-ci-test sequentially, including after the first failure. The initial independent fake-recursive-make probe checked all four pass/fail combinations: both targets ran in order every time; aggregate returned0 only when both succeeded. Makefile hash is unchanged by repair.
- Installer/manifest inspection confirms the helper and nested tool requirements ship through existing .grok-stack ownership, while root opt-in is absent from installer MANAGED_FILES and project_copy. Added installer assertions cover this distinction. Root project-marker files, architecture rules and Trust CI product source are unchanged.
- README describes dependencies, workers0 rollback, shared-DB limits, consumer opt-in behavior and separate runner-image provisioning. Local evidence does not activate a deployed image/policy or supply merge authority. The temporary cancellation context's main-thread requirement is compatible with the existing verifier/module CLI invocation paths; no existing shared util.run call contract was changed to require it.

## Evidence actually inspected and remaining limit

Reviewed actual tracked diff plus the untracked helper, test module, root config and requirements; surrounding verification, installer, manifest, util.run, project_copy, .coveragerc, route, requirements and user authorization. The narrow repair changes helper cancellation/config selection and the corresponding test cases; other six source hashes remain the initial reviewed values.

Read `.grok-stack/runtime/priority-final-verification.json`: all15 checks pass, verification fingerprint `b9d2ff8d171a0f0e1d50a57ba14ada7863596c303344f8e348444319a3dd3584`; Core helper workers22 reports79.061s, and its actual pytest output says **642 passed, 794 subtests passed in78.51s**. Coverage passes; Factory output reports546 tests, one existing skip, and actual two-restart recovery proof; source stability passes. The earlier chat count641 is superseded by this file's642=baseline624+18 added methods. These full results are the owner's inspected evidence, not reviewer reruns.

Final same-tree serial/parallel coverage, exact identity inventory and performance benchmark are still pending at this code-review checkpoint. This PASS asserts inspected implementation correctness and closure of the code finding; it does not claim a final speedup, final parity result, external attestation or readiness to skip remaining delivery evidence. The owner must attach those results before making the corresponding completion claim.

Reviewer commands: read-only git status/diff/diff-check, focused nl/sed/rg reads, Python SHA256/JSON summaries; initial temporary single-child cancellation reproduction and fake-make matrix; repaired single SIGTERM unittest and direct handler-restoration cancellation probe. No full suite/pool, heavy benchmark, package install, external call, credentials, deployed-state access or product edit was performed.

## Actual inspected source hashes

- `.grok-stack/adaptive_grok/python_test_runner.py`: `d78974c736bb3374ee455bb45f1989125794679941e342aa93febb3cea5307cb`
- `.grok-stack/adaptive_grok/verification.py`: `2246929a2610121ae5fb53569bebd5d771de43c8cedf07225df1a3f92a79114b`
- `.grok-stack/config/python-test-requirements.txt`: `6a1c4e61e3209e4566eb7e8a13eb2698336ed3212c21c54a0fe7568f68c0f08b`
- `.grok-test-runner.json`: `3c92821042f3b1a1b0bc1ae7e5a744abb716c163384e9deac9794f90ffd1dee0`
- `Makefile`: `68b9e159661a38d81172cdc6ae1d8a6545ab94c73b3f8d176eb32d2a8a549bad`
- `README.md`: `0472035248c0bf2de19bb3a96d2a2b28511aa82aee5ea8090ee08e5fc6b427ad`
- `tests/test_installer.py`: `4bb72f959ba75693439758bb382a3ea39b92cad6bb20faeba5d1f530e5c81e26`
- `tests/test_python_test_runner.py`: `bd25914f40ae6da4e79c8774f0d03a2825d0a28f934ea530e82fec2dcd496f89`

All entries match the refreshed source-hashes.json at report generation.

Any later source mutation requires fresh hash binding and affected verification/review. Final benchmark evidence and separately provisioned runner tools remain delivery dependencies; local reviews cannot replace the external exact-head Trust CI gate.
