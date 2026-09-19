# Test-review follow-up — cancellation CLI contract

Added direct `runpy` invocation coverage for `scripts/grok_verify.py` with a controlled report. The test asserts the human-readable `RESULT: CANCELLED` label and exact `SystemExit` mappings: SIGTERM-derived cancellation exits 143, while `KeyboardInterrupt` exits 130. The service-level regression also asserts that previously collected checks remain present in the cancellation report.

Focused command:

```text
python3 -m unittest tests.test_verification_doctor.VerificationTests.test_verify_records_cancelled_run_and_replaces_pass_receipt tests.test_verification_doctor.VerificationTests.test_grok_verify_cli_reports_cancelled_and_preserves_exit_mapping tests.test_verification_doctor.VerificationTests.test_verify_does_not_mislabel_unrecognized_system_exit
```

Result: **3 tests passed**. `python3 -m py_compile .grok-stack/adaptive_grok/verification.py scripts/grok_verify.py tests/test_verification_doctor.py` passed. `git diff --check` passed. The full PR gate was not run, as directed.
