# Implementation checkpoint

Root is the sole user-authorized writer. Added explicit repository opt-in, bounded logical-CPU worksteal workers, scoped pinned dev tools, same-interpreter execution, fresh isolated serial/parallel coverage, stable report names and a serial Make rollback. Existing consumers are unchanged unless they opt in; nested legacy coverage now preserves the parent data file. Other suites, contracts and database/restart scripts are unchanged.

TDD: the first three tests failed because the old runner used one process, accepted invalid settings, and overwrote inherited parent coverage. After implementation they passed. Additional regressions exposed pytest's narrower default filename pattern and a fast-exit output-limit gap; both were repaired, and all14focused tests passed in10.179s, including assertion/import/worker failures, missing worker coverage, threshold failure and owned-child timeout cleanup.

Baseline on an unchanged exact-main detached tree:624tests passed,505.238s wall, coverage79.86589235466683%, branch mode true,42measured files. Final accelerated/full verification and independent reviews remain pending. These counts differ from the earlier M7 experimental tree and are not yet a final speedup claim.

## Additional verified repairs and Trust entrypoint

The required full verifier passed15 checks with638 Core methods/789 subtests in60.138s, 79.946918% combined branch-aware coverage and unchanged Factory546/disposable2-restart evidence before these final additions. This is an intermediate receipt, not final-tree evidence.

Two added red characterizations exposed blocking FIFO config reads and an owned descendant surviving a completed controller. Reject nonregular config before read, and terminate the owned process group even after controller exit; both passed after repair. Descendant assertions allow bounded kernel termination/reaping time.

Trust CLI characterization first failed for both workers2 and0 because no suite ran; implementation now proves6 distinct methods,2 files,2 actual worker PIDs with each file kept together, serial one PID, correct Trust imports and collection-error propagation. All16 focused Core tests passed12.399s. Existing Trust operations pin test failed on missingpytest then all14 passed after source Dockerfile pins. No deployed image or policy changed.

Final focused suite:17 methods passed14.904s, including empty collection and missing/corrupt current-run coverage. The initial real Trust run exposed missing existing service dependency fastapi in the new temporary environment; installed exact existing pyproject runtime/test dependencies there, with no source or system-environment installation. Final full verification and the same-source serial/parallel comparison follow below in separate evidence.

The next full run passed all Python/coverage/Factory PostgreSQL checks on641 Core methods, but failed architecture/governance because the diff mixed local implementation and Trust CI source. Preserve that failed report; move CI-source pins to a separate bootstrap PR without changing the separation rule. The acceleration branch now excludes both Trust CI source edits.

## Final same-tree measurement

The final frozen implementation ran the identical 642 Core method inventory in both
engines. Serial unittest with branch coverage completed in 593.204 seconds; the
22-worker pytest-xdist run completed in 62.676 seconds, a 9.4646116536x Core-only
speedup. Collection and actual JUnit execution each had 642 unique identities, and
the serial/parallel coverage JSON had the same 43 files, branch mode and totals
(79.85898942420681%). See the external raw artifacts at
`/tmp/adaptive-xdist-covered-i6pd0lna/final/` and the runtime summary
`priority-final-checks.json`; both checks reported source unchanged.

Trust collection similarly matched 213 unique methods. Its serial target was 6.381
seconds and auto-worker target 10.336 seconds, so this change does not claim a
suite-wide aggregate speedup. The documented `loadfile` behavior is retained for
shared PostgreSQL fixtures. Across 653 `vmstat -y 1` samples, swap-out stayed zero;
the observed maximum swap-in was 2712 and maximum I/O wait was 46. This is a
host-specific observation, not a universal worker policy.

## Post-review local retry limitation

The earlier full verifier passed all 15 checks on the same eight product hashes. After
only evidence/report updates, two attempts to repeat the Factory disposable lane hit
its unchanged internal 480-second timeout (the second ran 544 tests in 480.770
seconds). The forced harness shutdown then explains the PostgreSQL connection errors,
the unrelated temporary-venv `httpcore` import error and the late HTTP assertion; they
are not accepted as product failures. At the time of the retry host load average was
about 14 with 3.2 GiB swap occupied, although swap-out remained zero in the immediate
sample. Do not change Factory's product timeout to accommodate this noisy local host.
The unchanged product hash map and the prior pass remain the available local product
verification evidence; the PR's exact head still requires external Trust CI.
