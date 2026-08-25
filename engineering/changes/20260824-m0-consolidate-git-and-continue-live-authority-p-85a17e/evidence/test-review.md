# Test review — M0 consolidate git / live authority characterization

Reviewer: `test_reviewer` (read-only). Route `85a17ed2e935`. Change `20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e`.

Tree: commit `ca1e88aad3dafcfeb81583f443f67c49c1faeab6` vs parent `1fc942065a124ce75659bd082519d8ebc37774e8`.

Focus: `trust-ci/tests/test_m0_invariants.py` → `test_activation_report_operator_safe`. No secrets read; no push/merge/deploy.

## Verdict

**PASS** with residual characterization gaps (not blocking this docs/test slice). The new test matches committed operator-safe docs, does not assert “main is unprotected”, does not hit the live API, and the M0 suite is green (8 tests).

## What the new test asserts

| Requirement | How tested | Match to docs |
| --- | --- | --- |
| Activation report file exists | `REPORT.is_file()` → `engineering/runbooks/trust-ci-activation-report.md` | Report is committed and filled |
| Check Run id not `UNKNOWN` | After first `"Check Run id"` substring, markdown cell `split("\|", 2)[1]` must not contain `UNKNOWN` | Table cell is `97390635614` |
| Local HMAC (not registered public webhook) | `assertIn("local HMAC", plan)` plus `"no public HTTPS" in plan or "not done" in plan` | Plan M0.2: Check Run via **local HMAC**; webhook **not done** (no public HTTPS) |
| No PEM markers | `BEGIN RSA PRIVATE KEY` / `BEGIN OPENSSH PRIVATE KEY` absent from spec, plan, report | No `BEGIN` material in those files |
| Report exists as operator-safe artifact | Same file assertion | Template + live fields |

Does **not** assert `main` unprotected / `main protected \| false`. Plan line 5 forbids that (would fight M0.3). Tests grep clean of `unprotected`.

## Would it fail on a live-fact revert?

- Check Run id reverted to `UNKNOWN` in the table cell: **fails**. Current parse on committed report yields ` 97390635614 `.
- Entire `Check Run id` row removed: **fails** (`split` IndexError / empty).
- Plan still saying local HMAC / not a GitHub-registered public webhook: **partial**. Removing `"local HMAC"` fails. Claiming a registered webhook while leaving other M0.2 `- [ ] … not done` boxes **can still pass** because `"not done"` is an OR against any occurrence in the plan (SHA-change, Ed25519 requeue, etc.). `"no public HTTPS"` is tighter; if both phrases are edited away while HMAC remains, the OR still passes.

## Fragile markdown parsing (false-pass / false-fail)

The Check Run assertion is:

```python
report.split("Check Run id", 1)[1].split("|", 2)[1]
```

It is **not** a table parser. Residual risks:

1. **False pass:** first `"Check Run id"` is followed by a pipe-delimited cell that is non-`UNKNOWN` but not the numeric id (e.g. `see table below`, a UUID). Live revert of the real id could hide in a later row.
2. **False pass:** value cell `97390635614 (placeholder)` without the token `UNKNOWN` satisfies the test while docs lie.
3. **False fail:** prose that contains `"Check Run id"` before the table, then a later `UNKNOWN` in the same parsed slice (currently first hit is the table row; prologue says “Empty fields stay `UNKNOWN`” but does not use the exact field label).
4. **False fail:** wrapping the id in extra pipes or splitting the row across lines changes `split("|", 2)[1]`.
5. PEM list omits `BEGIN PRIVATE KEY` / `BEGIN EC PRIVATE KEY` / `BEGIN OPENSSH` variants already partially covered; PKCS#8 `BEGIN PRIVATE KEY` would not fail.

Acceptable for a characterization slice if operators keep the pipe table. Do not treat it as schema validation.

## Live network / kill-switch

- `test_m0_invariants.py` only reads repo files. The `http://127.0.0.1:8080/health/ready` string is compose **text**, not an HTTP client.
- No `requests`/`urllib`/`socket` I/O in this module. **No live-network tests added.**
- Kill-switch drill is **documented** (report field `2026-08-24 pass`; plan M0.2; `implementation.md` host STOP → ready 503/200). It is **not** unit-tested against the live API. **Acceptable** per test-plan P0 “live drill; report field” and this review’s instruction.

## Verification evidence

Re-ran (this review, no secrets):

```text
python3 -m unittest trust-ci.tests.test_m0_invariants -v
Ran 8 tests in 0.001s
OK
```

Matches `implementation.md` (“8 tests OK”). `python3 scripts/grok_verify.py --mode pr` was **not** re-run here; implementation claims PASS. Independent re-run remains operator/CI evidence, not this unit file.

## Residual test gaps

1. Webhook-absent claim is too weak (`"not done"` OR); tighten to `assertIn("no public HTTPS", plan)` **and** `assertIn("local HMAC", plan)` without the OR.
2. Check Run id should match a digit token (or the committed id) rather than “cell lacks UNKNOWN”.
3. Kill-switch, attestation 404, leftover unstaged packages, and “origin still `1fc9420` / no push” stay **manual** — correct for host-local ops; do not add live API tests to unittest.
4. Report still records `main protected | false`; tests correctly ignore it. Do not add that assertion in M0.2.

## Files in the test delta

Only `trust-ci/tests/test_m0_invariants.py` (+15 lines): `REPORT`, `PEM_MARKERS`, `test_activation_report_operator_safe`. Other M0 tests unchanged.

**Status: pass.**
