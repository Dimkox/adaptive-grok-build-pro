# Verification evidence and limitation

A single full route-selected verification was run before the final two regression tests were added:

```text
TMPDIR=/tmp python3 scripts/grok_verify.py --mode pr
RESULT: PASS | profiles=base,contracts | changed=18
```

It passed git diff, change-spec, architecture, governance, Ruff, Bandit, pilot unittest, root unittest, coverage, factory unit, factory disposable PostgreSQL exit, and source stability.

After that pass, two additional test cases were added for the reviewer-requested email/URL/Bearer/API-key/password redaction and Unicode-only/long-input behavior. The focused suite now passes 30 tests and Ruff is clean. The earlier full receipt is therefore fingerprint-stale by design. It is not being re-run: the operator constraint for this work is one full/live cycle per package, with no repeated full cycle. The stale receipt is retained as historical evidence and this package must not be claimed externally ready until an authorized future verification refresh is performed.
