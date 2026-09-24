# Focused verification — 2026-09-23

Candidate HEAD: `130ce4a42d9f9bbd1b56772d40b19ae530283205`

## Focused regressions

The 17 focused verifier cases, two Git-status provenance cases, and one workflow allowlist case were run together:

```text
Ran 20 tests in 6.529s

OK
```

Exit status: `0`.

## Real-tree focused verifier

Command:

```text
python3 scripts/grok_verify.py --mode focused-static-seo-landing --no-record --json
```

Observed exit status: `1` (expected fail-closed result).

- `git-diff-check`: PASS (`4/4` checks).
- `scope-selection`: FAIL with `reason_code=out-of-scope-or-invalid-paths` and profile `full-pr`.
- `source-stability`: PASS.
- No `static-seo-landing-contract` check was dispatched.
- Broad PR suites were not dispatched by the rejected focused invocation.

The current issue implementation is intentionally a mixed verifier/workflow/documentation tree, so it is not eligible for the landing-only shortcut. This confirms that callers must use full PR verification for this tree.

## Full PR verification attempt

`python3 scripts/grok_verify.py --mode pr` was started after the package update. It progressed into the factory unittest/PostgreSQL and security-scan phases, but the execution harness interrupted it after approximately 15 minutes while `_python` was waiting for a subprocess. The observed exit status was `130` with `KeyboardInterrupt`; no passing verification receipt was produced or claimed.
