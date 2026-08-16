# Coverage baseline — 2026-08-16

- Date: 2026-08-16
- coverage version: 7.15.4
- Command:

```bash
python3 -m coverage run --rcfile=.coveragerc -m unittest discover -s tests
python3 -m coverage report
```

- Suite: 173 tests, OK
- TOTAL line coverage: 76%
- TOTAL branch coverage: see report (752 branches, 107 partial; Cover column is line %)
- Chosen `fail_under` = max(0, floor(76) - 2) = **74**

This is a ratchet, not a handbook 90. `.coveragerc` `[report] fail_under = 74` was set after this measurement.
