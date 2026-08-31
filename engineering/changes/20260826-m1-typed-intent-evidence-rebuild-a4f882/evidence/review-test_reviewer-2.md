# Test re-review 2 — M1 typed intent and evidence

## Verdict

**BLOCKED**

Reviewed exact repository HEAD `5b571b5452f9ffe1a9ee4f55374b49a9de541db8` against base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, the preserved first review, approved M1 plan, active package, and binding architecture analysis. The worktree was clean before this report was written.

The remediation closes every coverage gap named in the first test review: holdout exact-SHA/deletion/diff/multi-spec/downgrade/limit cases, receipt binding and staleness inputs, verification selection/profiles/exemption, signed runner metadata, tampering/replay, parser limits, hostile generation, schema preflight, and CLI path/default/error behavior are now directly exercised. Two new tests, however, encode behavior that contradicts the approved multi-spec/provenance contract.

## Blocking findings

### P0 — The Trust CI test oracle rejects valid multiple-spec changes with package-local criterion IDs

`trust-ci/tests/test_change_spec_holdout.py:173-181` correctly proves that two changed packages are allowed even though both fixtures use the normal package-local `AC-001`. In conflict, `trust-ci/tests/test_runner.py:207-216` and `:308-322` require the trusted metadata path to fail when two changed specs reuse `AC-001`; `trust-ci/src/adaptive_trust_ci/runner.py:218-230` implements that global rejection.

Neither the v2 schema nor local/holdout validation makes `AC-*` globally unique across packages, and every generated package naturally starts at `AC-001`. The approved plan requires multiple specs to be processed deterministically, not rejected based on cross-package bare-ID collision. Under the current tests, an ordinary PR updating two valid change packages can pass the holdout but is forced into a failed signed attestation before commands run.

Required repair: represent declaration identities unambiguously by package/path (or another explicitly versioned namespace) while still allowing each valid spec to contain its local `AC-001`. Replace the duplicate-rejection tests with a runner-level test where two changed valid specs both contain `AC-001` and the signed result remains deterministic with `spec_count=2` and correct totals. The holdout and runner must agree on this case.

### P1 — Malformed-spec tests require loss of the raw provenance digest

The approved plan at `docs/superpowers/plans/2026-08-26-m1-typed-intent-evidence.md:206-208` requires malformed JSON to retain a byte digest with zero/explicit unmapped coverage; architecture ruling R7 recommends sorted entries containing `raw_digest` and nullable semantic digest. Instead, `trust-ci/src/adaptive_trust_ci/runner.py:410-420` discards all spec provenance on any metadata error (`spec_digest=None`) and hashes only the error message. `trust-ci/tests/test_runner.py:294-306` explicitly asserts that loss.

Failing the signed outcome and stopping commands is correct, but the bounded raw bytes must still be bound into deterministic signed provenance and must never count as mapped evidence.

Required repair: preserve the composite raw-byte digest on parse/semantic failure, return or carry an explicit invalid/error state separately, and assert runner-level signed failure with non-null deterministic provenance plus zero/explicit invalid coverage. Keep the existing no-command assertion.

## Independent exact-HEAD evidence

- Focused root remediation suites: `python3 -m unittest tests.test_change_spec tests.test_change_receipts tests.test_verification_doctor tests.test_installer -v` — PASS, 87 tests.
- Focused Trust CI suites: `PYTHONPATH=../src:. /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest -v test_change_spec_holdout test_runner test_signing` — PASS, 44 tests.
- Full root suite: `python3 -m unittest discover -s tests` — PASS, 221 tests.
- Full Trust CI suite: `PYTHONPATH=trust-ci/src /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest discover -s trust-ci/tests` — PASS, 169 tests, 8 skipped because PostgreSQL was not configured.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src` — PASS.
- `python3 scripts/grok_verify.py --mode pr --no-record --json` — PASS; all checks pass, active spec gate-valid with 6/6 declaration-mapped criteria; pre-report tree fingerprint `489364bc8206c0ee6fd93541d4fe6b9c004cf5110706116b5a19e3fa7986fa22`.

The commands are current and green, but the contradictory assertions above make green insufficient. Do not record a passing `test_review` receipt for this HEAD.
