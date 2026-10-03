# Test plan — Fix issue123 router intent precedence: explicit operational intent survives pull-request and review wording; exclude negated quoted and historical mentions and preserve ordinary routes.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Explicit EN/RU operation with PR/review/fix vocabulary | OperationalIntentTests affirmative matrix |
| P0 | No operational authority; preserved reviewers, evidence and human gates | OperationalIntentTests route obligation assertions |
| P0 | Negated, quoted, historical and incidental mentions | OperationalIntentTests negative matrix |
| P1 | New independent affirmative clause after context/negation | OperationalIntentTests clause matrix |
| P1 | Incident containment and ordinary PR/review/bugfix compatibility | OperationalIntentTests priority matrix and existing RouterTests |
| P0 | Current action on previously built/reviewed artifacts, EN/RU object/destination restrictions | New full release-obligation regressions |
| P1 | Descriptive coordinated plan infinitives and plural release nouns | New ordinary-intent/no-release-skill regressions |
| P1 | Marker-only historical context and raw quoted safety domains | Independent guard and raw-scanning regressions |

## Automated checks

- RED/GREEN: taskset -c 16,17 env GROK_TEST_WORKERS=2 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_repo_router.OperationalIntentTests.
- Adjacent compatibility: same bounded allocation with python3 -m unittest tests.test_repo_router tests.test_hooks tests.test_reasoning_policy.
- Static: git diff --check; typed change-spec validation in controller verifier.
- Controller owns full python3 scripts/grok_verify.py --mode pr, exact-state evidence, independent reviews and external delivery.
- Review repair: 11 operational matrix methods observed RED with 21 failing subcases before the fix; GREEN matrix and 81 adjacent tests afterward. An in-memory developer probe removing only historical-prefix scope is killed by four marker-only assertion failures; this is a self-check, not independent review. Exact commands and source identities live in evidence/writer-review-repair.json.
- Second bounded repair: six exact second-review cases first fail (two methods, six assertions); the repaired matrix passes all 13 methods and the adjacent suite passes 83 tests in 30.049 seconds on CPUs 16,17 with at most two workers. Developer in-memory reversions of numeric-version segmentation, multiword-subject grammar and Russian plan context each produce two assertion failures and zero errors. Fresh exact commands/source identities are in evidence/writer-second-repair.json.
- The approved delivery shape now uses a combined A–F/H/HB source PR and a separate G PR; the aggregate controller owns renewed full PR gate and independent final review. This repair does not rerun per-contour full verification.

## Manual checks

- Inspect product inventory for exactly router.py plus test_repo_router.py, and retain a fresh RED/GREEN record. No old passing evidence is reused.
- Initial full verification and independent failed reports at e1c7a01 are historical/stale for the repaired tree and cannot count as current passes.
- Both complete second failed reviews and the controller's full pass on 5f96f392a are retained only at that original exact identity; they are stale for this second repair.
