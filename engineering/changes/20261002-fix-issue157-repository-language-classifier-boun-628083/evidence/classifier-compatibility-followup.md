# C classifier compatibility follow-up

Sole C writer, route `6280839332b6`, source HEAD before this repair `54bf1ade68804ff340aa262094308f4d2b663878` (scoped commit `7399ba0bec2e4633272665c335d5577149e98746` plus actual main `63799f8760d3a55028d83ab5ff0116ececf8f7d1`). Product repair inventory remains only `.grok-stack/adaptive_grok/repo.py` and `tests/test_repo_language_disclosure.py`. No binding-test expectation, verifier, worker engine, timeout, pin, state/version or external resource was changed.

## Preserved failure and renewed startup

The coordinator's full verifier at source HEAD failed `python-unittest`: pinned pytest-xdist, four workers, worksteal, exit 124 after 900.112 seconds. Quiet output contains an assertion failure around 7% and stops at 98%, but does not identify the final active test. Coverage was incomplete, not passed; passing other checks cannot convert this run into a pass.

Before diagnosis, capacity was remeasured and recorded in machine-local `.grok-stack/runtime/c-classifier-diagnosis-capacity.json` at `2026-10-02T23:30:32Z`: 14 physical cores, 28 online logical CPUs (0-27), default nproc 22 and affinity 0,1,8-27; actual cgroup v2 membership `/user.slice/user-1000.slice/session-2050.scope`, inherited effective cpuset 0-27, applicable ancestor quotas all unbounded. A child-only 0-27 widening probe returned capacity 28 with identical cgroup bounds and left controller affinity unchanged. Diagnostic allocation was CPU IDs 6,7, maximum two workers.

Original `.grok-stack/runtime/final-verify.json` was copied, not rewritten, to `.grok-stack/runtime/c-failed-final-verify-54bf1ade.json`. Both remain SHA-256 `8a7bd60138ed6eac0b829c186fbb6dcd54139f0f675377c46a5fbda9a26514c0`. Runtime reports remain machine-local evidence, not tracked release bytes or merge authority.

## Exact reproduced assertion and minimal repair

Two-worker diagnostic `tests/test_demo.py` reproduced `DemoServiceTests::test_alternate_scenario_claims_match_its_computed_route`: expected domains `['api']`, actual `['php', 'api']` (1 failed, 9 passed, 2.22 seconds, exit 2). The bounded scanner observed eight readable PHP files under `examples/bitrix-module`; the legacy classifier only promoted root PHP or PHP under src/app/local/public/www. Generalizing source discovery accidentally generalized this routing predicate.

Added dedicated example-tree and legacy-location tests first. RED: example-tree kind expected generic, actual php; 1 failed, 1 passed, 6 subtests passed, 2.19 seconds, exit 2. The repair retains PHP in detected_languages/source counts anywhere scanned, but counts readable PHP toward confirmed routing only at the legacy locations. Source discovery, Swift confirmation, symlink defenses and shared budgets are unchanged.

Common diagnostic prefix:

```bash
taskset -c 6-7 env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 _GROK_TEST_CHILD=1 PYTHONPATH=.:tests:.grok-stack timeout --signal=TERM --kill-after=5s 120s python3 -m pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --import-mode=prepend --rootdir=. -o python_files=test*.py -v -n 2 --dist=worksteal --max-worker-restart=0 -x --durations=10 tests/test_repo_language_disclosure.py tests/test_repo_router.py tests/test_demo.py
```

GREEN on repaired product bytes: 84 passed, 124 subtests passed in 5.83 seconds, exit 0. This includes 38 dedicated classifier tests, 35 existing router tests and 11 existing demo tests. Ruff for the two product files passed; git diff --check passed.

Tested product SHA-256: repo.py `8f6fcd47f7373c52a5263a5d1c7f766696ea8064d75695e2a586a885a97d13ec`; classifier tests `fb716975412b7f8159b4942bac6cbbeff3253a737687eef40d9fe4f79935a8b3`.

## Timeout diagnosis: observations and limits

All diagnostics used the two-worker worksteal engine on CPUs 6,7; none reran serially to hide the failed parallel run. On unchanged source HEAD, early architecture/Bitrix/change modules passed (284 tests plus 618 subtests, 77.76 seconds), and package/structure/classifier/router modules passed (176 tests plus 189 subtests, 27.81 seconds). These are diagnostic subsets only.

A six-module verifier/workflow diagnostic reached 75% and hit its 150-second diagnostic bound, exit 124. The active nodes were `DoctorTests::test_project_doctor_has_no_failures` and `VerificationTests::test_missing_adoption_marker_cannot_disable_architecture_checks`. The exact pair was then probed, with `-o faulthandler_timeout=20`, under the same two-worker engine and a 75-second diagnostic bound: 2 tests plus 4 subtests passed in 40.92 seconds, exit 0. The 20-second stack was in `shutil._rmtree_safe_fd` during temporary project-copy cleanup, not repo scanning. Those nodes are not established as the original full-run terminal nodes or its root cause.

An additional bounded parallel/cov subset (VerificationTests, DoctorTests and python runner tests, 180-second bound, faulthandler 30 seconds, private `/tmp/c-classifier-cov-diag-xHzsu7` coverage scratch) was stopped at the coordinator's aggregate handoff instruction, exit 143 after reaching 20% with no observed assertion at that point. Its diagnostic-only coverage threshold override was not production verification; it is explicitly inconclusive and not pass evidence. No production timeout, engine, pin, fallback or coverage threshold was edited.

The original 900-second full-suite timeout remains unexplained and is not claimed fixed. The coordinator now owns fresh full verification and independent reviews on the user-approved single aggregate source PR, including every C test. No C full rerun, external push, review, publication or merge was performed here.
