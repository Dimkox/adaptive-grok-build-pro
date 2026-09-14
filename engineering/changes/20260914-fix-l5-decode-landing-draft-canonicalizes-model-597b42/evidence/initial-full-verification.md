# Initial full verification: failed PDF fixture

Route: `597b421e450b`. Created: `2026-09-14T01:29:42+00:00`. Fingerprint: `fbef30224c7b5e3a94ab9449832230007b19c464c4dbe6d99ab956670bc28c4c`.

Command: `UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr`. Exit 1. This failed report cannot establish local completion.

| Check | Result |
| --- | --- |
| git-diff-check | pass |
| change-spec | pass |
| architecture | pass |
| governance | pass |
| secret-scan | pass |
| contract-structure | pass |
| sql-safety | pass |
| ruff | pass |
| bandit | pass |
| pilot-unittest | pass |
| python-unittest | pass |
| coverage | pass |
| factory-unit | pass |
| factory-postgres-exit | fail |
| source-stability | pass |

Pilot: 44 tests passed (1 skip). Root: 654 tests passed. Factory: 711 tests, one failure, two skips. Source stability passed.

The only failure was the unchanged existing PDF page-limit fixture. Its byte substitution moved the xref table while retaining old offsets; a separately generated valid 101-page PDF reaches the expected limit. Preserve production parser validation and repair the fixture, then obtain focused recovery evidence, independent review and final full verification.

```text
FAIL: test_oversized_page_count_reports_page_limit (factory.tests.test_landing_pdf_worker.PdfWorkerWithPinnedParser.test_oversized_page_count_reports_page_limit)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/test_landing_pdf_worker.py", line 120, in test_oversized_page_count_reports_page_limit
    self.assertEqual(ctx.exception.code, "pdf_page_limit")
AssertionError: 'pdf_invalid' != 'pdf_page_limit'
- pdf_invalid
+ pdf_page_limit


----------------------------------------------------------------------
Ran 711 tests in 356.762s

FAILED (failures=1, skipped=2)
Traceback (most recent call last):
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/run_disposable_exit.py", line 216, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/run_disposable_exit.py", line 191, in main
    _run(
  File "/home/pall/grok-projects/adaptive-grok-build-pro-l5fix/factory/tests/run_disposable_exit.py", line 70, in _run
    subprocess.run(command, check=True, env=environment, timeout=timeout)
  File "/usr/lib/python3.12/subprocess.py", line 571, in run
    raise CalledProcessError(retcode, process.args,
subprocess.CalledProcessError: Command '['uv', 'run', '--project', 'factory', 'python', '-m', 'unittest', 'discover', '-s', 'factory/tests', '-t', '.', '-v']' returned non-zero exit status 1.
```
