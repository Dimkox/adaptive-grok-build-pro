# Recovery test plan

Fresh controls in tests/test_verifier_recovery.py exercise the real verifier, owned Popen process session and receipt writer; only slow/external command outputs or exact failing I/O boundaries are controlled.

The 20 tests cover completed pass/fail retention; receipt binding/type/disk failures; cancellation before dispatch/spawn, during a TERM-resistant child, during coverage, after result, during receipt replacement and report output; old-pass retirement; malformed/truncated coverage and invalid UTF-8; scratch cleanup failure; completed npm failure before cancellation; stdout failure with stderr report fallback; write, replace, file/directory fsync faults; and receipt HEAD/tree/scope/check/terminal binding plus same-tree new-head invalidation. The owned-child integration control proves an unrelated process stays alive.

Commands use taskset -c 0-1 with env -u GROK_TEST_WORKERS for the unittest harness. Fixtures select their own worker counts up to two. A global GROK_TEST_WORKERS=2 was found to override three legacy controls; that contaminated command is recorded as failed, and the three controls passed with the override removed.

Focused implementation command: python3 -m unittest tests.test_python_test_runner tests.test_verification_doctor tests.test_change_receipts tests.test_verifier_recovery -q. Changed-file ruff and git diff --check are also required. Exact fresh RED/GREEN outputs and runtimes are in the implementation report.

Controller then runs python3 scripts/grok_verify.py --mode pr with the actual trusted base and selected capacity; executable changes require full scope. Initial documentation-only selector skips are historical startup evidence, not passes for this runtime. Independent code/test reviewers use private scratch mutation probes; they do not write in this candidate. External Trust CI on the exact final PR head remains separate.

## Independent-review output-close repair

The initial 20-test/172-test results above are historical, not verification of the repaired source. Both independent reviews reproduced TemporaryFile context-exit OSError replacing a completed result; the code reviewer also reproduced lost cancellation. Six new methods (16 fault cases) close real stdout/stderr files, then inject errors on stdout only, stderr only or both. They assert completed pass/fail exit codes and exact output, primary RunCancelled with result and cleanup notes, missing-command exit127, pre-result primary exception notes, fail-closed verifier status with visible exit0, and SIGTERM delivered during either output close. Both handles must close.

The recovery module now contains 26 tests. Repair commands use assigned CPUs4,5 and env -u GROK_TEST_WORKERS, with fixture-owned maximum two workers. The six-method RED/GREEN command and 30-test focused recovery/lifecycle command are recorded in evidence/output-close-repair.md. No individual full-suite rerun or push is authorized; the controller will verify and independently review the combined source PR on its exact aggregate HEAD. The artifact PR remains separate, and these contour reports remain historical workflow evidence after aggregation.
