# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | No-pytest interpreter: one disclosed serial pass, pass status, degraded label | `test_unimportable_parallel_engine_degrades_to_one_serial_pass` |
| P0 | Importable engine + missing/mismatched pins: fail, no silent retry | `test_importable_but_mismatched_parallel_dependency_still_fails` |
| P0 | Each method runs exactly once on both engines; child guard, caps, timeouts, output limit, SIGTERM cleanup | engine-conditional shards/distribution tests |
| P1 | Coverage integrity both backends (missing/corrupt damage), parent COVERAGE_FILE isolation, verifier wiring, trust lane | coverage scenarios + `_python` tests |

Environment note: this host has no importable pytest — it IS the AC-004 condition; the App check on the PR head covers the mandatory external command.
