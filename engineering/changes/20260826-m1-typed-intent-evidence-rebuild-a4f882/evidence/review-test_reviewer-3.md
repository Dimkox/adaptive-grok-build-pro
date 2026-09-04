# Test re-review 3 — M1 typed intent and evidence

## Verdict

**BLOCKED**

Reviewed exact repository HEAD `1e3c5ce3cde0f60a65343e7df1764ced4e56c290` against base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, both preserved prior test reviews, the approved M1 plan, active package, and remediation-2 claims. The worktree was clean before review commands generated ignored bytecode and before this report was written.

## Prior blockers

Both oracle contradictions from re-review 2 are corrected:

- Criterion IDs are spec-local. Multi-spec coverage qualifies unmapped IDs with the stable spec path, while two valid specs may both use `AC-001`; extraction and signed runner-path tests prove deterministic passing totals.
- Malformed canonical bytes now yield a deterministic composite digest containing their raw SHA-256 and a null semantic digest. The signed runner outcome fails, coverage remains empty, and no holdout/product commands execute.

Golden signature verification and memory-store runner replay pass. The PostgreSQL tests are real conditional integration tests for legacy byte-for-byte round-trip and current typed metadata; in this environment all ten PostgreSQL tests were honestly skipped because `TRUST_CI_TEST_DATABASE_URL` is not configured. This skip is disclosed and is not simulated evidence.

## Blocking finding

### P0 — The full Trust CI suite is not repeatable and the committed holdout digest check fails

Running the focused holdout suite imports `trust-ci/holdout.example/change_spec_validate.py` in place and creates ignored file `trust-ci/holdout.example/__pycache__/change_spec_validate.cpython-312.pyc`. `adaptive_trust_ci.holdout.bundle_digest()` correctly hashes every regular file in the immutable bundle, so the subsequent full suite fails:

```text
FAIL: test_example_holdout_digest_matches_example_bundle
policy digest: 321ad704d40ea986d7de79694966d00ec28cdd9b80fa22d162cc391201d09e00
actual digest: e6b9e6f1fd51d6ad189b47f03b80074bcdf3ee511b72a6497f30b0016579ea26
```

An independent digest calculation confirms `321ad704...` is the two checked-in source files only, while `e6b9e6f...` includes the generated `.pyc`. Thus remediation-2's claims “Trust CI suite: 177 passed” and “holdout digest consistency passed” do not hold for the exact reviewed test sequence, and rerunning tests can mutate the measured bundle identity.

Required repair: execute holdout test code without writing bytecode into the source bundle (for example, load/compile source in memory or from an isolated temporary copy, with an explicit regression that the bundle tree/digest is unchanged before and after the tests). Do not weaken `bundle_digest()` by silently ignoring arbitrary files in the deployed immutable bundle. Remove the generated ignored bytecode from the worktree before final verification, then rerun focused tests followed by the full Trust CI suite and digest assertion on the same clean snapshot.

## Independent exact-HEAD evidence

- Focused root suites: `python3 -m unittest tests.test_change_spec tests.test_change_receipts tests.test_verification_doctor -v` — PASS, 73 tests.
- Focused Trust CI suites including PostgreSQL class: `PYTHONPATH=../src:. /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest -v test_change_spec_holdout test_runner test_signing test_postgres_integration` — PASS, 60 tests, 10 PostgreSQL skips.
- Full root suite: `python3 -m unittest discover -s tests` — PASS, 222 tests.
- Full Trust CI suite: `PYTHONPATH=trust-ci/src /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest discover -s trust-ci/tests` — **FAIL**, 177 tests run, 1 failure, 10 PostgreSQL skips; failure is the holdout digest mismatch above.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src` — PASS.
- `git diff --check 0a4dd0a..HEAD` — PASS before the failing Trust CI command stopped the chain.
- `python3 scripts/grok_verify.py --mode pr --no-record --json` — PASS; active spec gate-valid with 6/6 mapped criteria; pre-report tree fingerprint `a4a73bfe8969677240e94dab7d8f1fa01b5b8d72ee6780f11f50f1fea6ab50ab`.

Do not record a passing `test_review` receipt for this HEAD.
