# Independent test review — acceleration PR

Reviewer: docs_researcher, user-approved substitute test_reviewer; product author: root under the recorded capacity exception. Route 49ad08e34053, branch perf/parallel-python-tests, base 64378d28c7b78cace463d96470c1898294b8f196.

Verdict: **Final PASS; no open findings.** The repaired implementation boundaries, test adequacy, same-final-tree test inventories and coverage equivalence are supported by the inspected evidence. The measured acceleration applies to Core only.

## Final source and verification inspected

Re-read the actual runner, verifier integration, Makefile, dependency pins/root opt-in, focused tests and installer invariant. The acceleration diff contains no trust-ci product edit. All eight refreshed entries in evidence/source-hashes.json match the reviewed bytes, including:

- .grok-stack/adaptive_grok/python_test_runner.py: d78974c736bb3374ee455bb45f1989125794679941e342aa93febb3cea5307cb.
- tests/test_python_test_runner.py: bd25914f40ae6da4e79c8774f0d03a2825d0a28f934ea530e82fec2dcd496f89.

Read .grok-stack/runtime/priority-final-verification.json, created 2026-09-11T02:28:18+00:00: aggregate pass, 15 checks, recorded fingerprint b9d2ff8d171a0f0e1d50a57ba14ada7863596c303344f8e348444319a3dd3584. That fingerprint belongs to the verification snapshot; subsequent review/evidence documents need current receipts and do not change the inspected product hashes.

The actual Core summary is **642 passed, 794 subtests passed**, workers 22; runner invocation 79.061s. Coverage passes with branch measurement enabled, total 79.858989%, 43 source files, 11850 statements and 5170 branches. This corrects the earlier shorthand count of 641. Factory verification/restart lanes and source stability also pass. These are supplied verification results read by the reviewer, not a second independent full-suite execution.

The owner reports the focused 18-method suite passed in 26.259s. The final Core count is consistent with the unchanged 624-method baseline plus 18 focused methods. Read the actual Trust target log: **203 passed, 10 expected PostgreSQL skips, 63 subtests passed**. The absent optional test database remains visible rather than counted as exercised PostgreSQL coverage.

## Findings closed

| Item | Final correction and supporting regression |
| --- | --- |
| TR-1, P2: pytest.ini could silently filter a full suite | Shared _pytest_command now supplies -c os.devnull. The Core regression combines file addopts, norecursedirs, a nested unittest package and inherited pytest environment options, requiring all five markers. The Trust regression supplies its own filtering pytest.ini and requires all six methods. Both paths exercise the real command and preserve generic consumer routing. |
| Once-only fixture evidence could overwrite duplicate runs | Core and Trust fixture markers now use exclusive creation. A duplicate method invocation causes failure instead of overwriting earlier evidence. PID checks still establish two-worker distribution and per-file affinity. |
| Architect's SIGTERM cancellation concern | _cancellation is active before process creation, polls a cancellation flag, restores the previous SIGTERM handler and exits nonzero after owned-group cleanup. The regression sends SIGTERM to a real controller, checks its child has stopped, and checks handler restoration after normal completion and missing-command failure. Main-thread ownership is explicit. |

For TR-1, the original independent probe on the pre-repair helper produced exit 0 after executing only one of four methods under pytest.ini addopts=-k test_0. The regression now targets that causal failure directly. The reviewer inspected the repair and passing current full verification rather than rerunning worker probes during the owner's timing comparison.

## Test boundary assessment

| Boundary | Evidence assessed |
| --- | --- |
| Selection and distribution | Closed opt-in, absent opt-in/private-child compatibility, workers 0, auto CPU bound, inherited configuration isolation, unittest filename pattern and exclusive method markers. Existing generic project-marker precedence tests remain intact. |
| Failures before/during execution | Missing package, invalid configuration/nonregular FIFO, assertion failure, collection exception, empty collection, native worker exit, output bound, missing command, timeout and SIGTERM. No successful serial retry conceals these failures. |
| Process lifecycle | Timeout and normal-controller-exit tests observe the owned descendant; the new SIGTERM test covers controller cancellation and handler restoration. These prove the implemented owned-process-group behavior, not universal containment of deliberately detached processes. |
| Coverage integrity | Configured source set/branch mode/74 threshold remains in unchanged .coveragerc; data is invocation-owned. Tests remove or corrupt current data, remove worker acknowledgements, force under-threshold coverage, and protect pre-existing and nested parent data. |
| Partial contributions | An earlier independent two-worker probe removed only gw0's acknowledgement while gw1 produced 100% source coverage: test exit 0 still resulted in coverage failure 1. This corroborates the unchanged incomplete-worker guard separately from a below-threshold failure; it is historical probe evidence, not a new run of the repaired tree. |
| Empty collection | Earlier independent current-interpreter probes returned test exit 5 / coverage exit 1 for workers 2 and 0, even when importing the subject produced 100% coverage. The current focused parallel empty-collection case belongs to the passing final suite. |
| Trust separation | Dedicated cwd and absolute import roots, six synthetic methods split by file, serial and parallel runs, no Core collection, and collection-error propagation. All ten database-dependent Trust methods are in the single test_postgres_integration.py loadfile group. |
| Combined Make flow | Read .grok-stack/runtime/make-flow-verification.json: all four success/failure combinations invoke Trust once and succeed only when both stages succeed. This proves aggregation, not a separate full combined-suite run. |
| Consumer installation | Installer invariant confirms helper and scoped tool pins are shipped while the root opt-in is not. No new root Python project metadata changes generic detection. |

The reviewer performed no new heavy execution during this re-review. Earlier independent probes used external temporary projects and at most two workers. No product edits, dependency installations, network operations, credentials, database operations or deployed-state reads were performed by the reviewer.

## Final same-tree comparison and delivery limits

Read .grok-stack/runtime/priority-final-checks.json and /tmp/adaptive-xdist-covered-i6pd0lna/final/coverage-comparison.json: final benchmark status pass, source_unchanged true, and both Core test and coverage commands exit 0. The owner ran the benchmark; the reviewer inspected its artifacts without rerunning tests.

| Same-final-tree measurement | Verified result |
| --- | --- |
| Core serial | 642 tests, 593.204 seconds |
| Core parallel | 22 workers, 642 tests, 62.676 seconds |
| Core measured speedup | 9.4646116536x for this measured pair |
| Core inventory | unittest and pytest collection equal, each 642 unique methods; actual parallel JUnit execution equals that inventory with 642 unique methods |
| Trust inventory | unittest and pytest collection equal, each 213 unique methods |
| Coverage configuration and files | Branch measurement enabled in both; exactly the same 43 files |
| Coverage totals | Both 79.85898942420681%; 9,692 covered / 11,850 statements and 3,900 covered / 5,170 branches; 2,158 missing lines, 1,270 missing branches, 878 partial branches, 7 excluded lines |
| Per-file coverage | No differing files, missing-line sets or missing-branch sets in the comparison |
| Trust elapsed time | Serial 6.381 seconds; auto 10.336 seconds, so this target was slower with auto |

The measured speedup is Core only; no aggregate verifier or combined Make speedup is claimed. Historical 624/505s versus 638/60s runs are not used for the final factor. Direct parsing of all 653 samples in core-comparison-vmstat.log found no swap writes (so maximum 0); the combined log has swap-read maximum 2,712 and I/O-wait maximum 46, so an all-run si maximum 56 / wa 0 claim is unsupported. These host observations do not establish a universal resource or timing guarantee.

Runner image preparation/rollout is a separate bootstrap delivery. This review neither establishes deployed package availability nor replaces the App-owned exact-head policy-epoch check and applicable signed approval scopes.
