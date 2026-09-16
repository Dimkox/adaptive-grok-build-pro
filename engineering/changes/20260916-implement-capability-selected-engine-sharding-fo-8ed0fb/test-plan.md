# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | No-pytest interpreter: one disclosed serial pass, pass status, degraded label | `test_unimportable_parallel_engine_degrades_to_one_serial_pass` |
| P0 | Importable engine + missing/mismatched pins: fail, no silent retry | `test_importable_but_mismatched_parallel_dependency_still_fails` |
| P0 | Each method runs exactly once; child guard, caps, timeouts, output limit, SIGTERM cleanup — the degraded serial arm executes here, the xdist-only arms are mock-pinned (one explicit skip) and executed by the App check on a pytest-bearing image | engine-conditional shards/distribution tests |
| P0 | Real repo root without opt-in keeps the legacy serial commands and never reaches the runner | `test_repo_root_without_optin_keeps_legacy_verifier_path` |
| P1 | Coverage integrity serially (the xdist combine path is App-check-only) (missing/corrupt damage), parent COVERAGE_FILE isolation, verifier wiring, trust lane | coverage scenarios + `_python` tests |

Environment note: this host has no importable pytest — it IS the AC-004 condition; the App check on the PR head covers the mandatory external command.
