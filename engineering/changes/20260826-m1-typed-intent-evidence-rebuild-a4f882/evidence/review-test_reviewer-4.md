# Test re-review 4 — M1 typed intent and evidence

## Verdict

**PASS**

Reviewed exact repository HEAD `ee9ed6ada12f78f808a12df311a41d7888ca9d30` against base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, the approved M1 design/plan, active package, remediation-3 claims, and all three preserved earlier test-review reports. The worktree was clean before this report was written.

No blocking test-coverage or verification-evidence finding remains for this candidate. This is local preflight evidence only; it does not replace the external App-owned exact-SHA Trust CI check or its required external approvals.

## Prior blocker closure

The re-review-3 P0 holdout mutation/digest blocker is closed without weakening `bundle_digest()`:

- `test_change_spec_holdout._load()` compiles and executes the checked-in validator in memory rather than importing it beside the measured source.
- The focused regression `test_module_loader_does_not_write_bytecode_next_to_measured_source` passed.
- Before testing, after the first default full Trust CI suite, and after a second consecutive default full suite, the bundle digest was identically `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64` and the complete regular-file set remained exactly `change_spec_validate.py` plus `validate.py`.
- Both consecutive default suites completed successfully: each ran 182 tests with 10 conditional PostgreSQL skips and no failures. No `trust-ci/holdout.example/__pycache__` or other ignored bundle file appeared.

The two oracle contradictions from re-review 2 also remain closed in the full suite: criterion IDs are spec-local with path-qualified multi-spec unmapped IDs, and malformed bytes preserve their raw provenance digest in a signed zero-coverage failure while executing no verification commands.

## Hostile-path and surrogate coverage

The new regressions exercise the required negative and compatibility boundaries rather than only helper-level happy paths:

- A real Git repository covers Unicode, embedded LF, tab, and backslash path identities end to end through NUL-delimited changed-path discovery, protected-scope matching, multi-spec selection/digest, signed attestation serialization, and signature verification. Invalid UTF-8 Git path bytes and unavailable exact base/head identities fail closed.
- Holdout contract-path tests reject control characters with controlled failures.
- Local, independent holdout, and trusted metadata validation reject unpaired surrogate values and keys.
- The runner-level surrogate test verifies a signed failure containing the deterministic raw-byte provenance digest, zero coverage, and no holdout/product command execution.

Independent focused execution of the five direct regressions passed:

```text
test_module_loader_does_not_write_bytecode_next_to_measured_source
test_unpaired_surrogates_in_values_and_keys_fail_closed
test_contract_paths_reject_control_characters_with_controlled_failure
test_real_git_paths_preserve_scope_and_signed_spec_provenance
test_unpaired_surrogate_produces_signed_failure_with_raw_provenance

Ran 5 tests in 0.220s — OK
```

## Independent exact-HEAD evidence

- Exact identity: `git rev-parse HEAD` -> `ee9ed6ada12f78f808a12df311a41d7888ca9d30`; pre-report `git status --short` was empty.
- Focused remediation tests above: PASS, 5/5.
- Default Trust CI discovery suite, first run: PASS, 182 tests run, 10 skipped, no failures.
- Default Trust CI discovery suite, immediate second run: PASS, 182 tests run, 10 skipped, no failures.
- Holdout identity after each full run: digest `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64`; files exactly `change_spec_validate.py`, `validate.py`.
- Full root discovery suite: PASS, 223/223.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src`: PASS.
- `git diff --check 0a4dd0a..HEAD`: PASS.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS; route `a4f88266a848`, active spec valid, 6/6 criteria mapped, pre-report tree fingerprint `8e38706ed5ccdc2345ac40deb64df5b83440e692adabce5330825ae67cf1c64c`.

The 10 PostgreSQL integration tests are genuine conditional tests, including legacy golden byte-for-byte replay and current signed typed-metadata round-trip, but were skipped because `TRUST_CI_TEST_DATABASE_URL` is not configured. They are not represented here as executed PostgreSQL evidence and do not invalidate the exercised source-level/default-suite gate.

## Findings

No P0/P1/P2 test finding. The candidate is locally test-review ready at the exact HEAD above. External PostgreSQL-backed and App-owned exact-SHA Trust CI evidence remains a release-gate responsibility outside this local review.
