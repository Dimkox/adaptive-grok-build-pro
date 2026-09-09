# Test review — M1 typed intent and evidence

## Verdict

**BLOCKED**

Reviewed repository HEAD `62b9c601de980b1e06cf78bd69e02c4847c7e2de` against base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, the approved M1 design/plan, the active red-risk typed spec, and the binding rulings in `evidence/analysis-architect.md`. The worktree was clean before this report was written. This is independent local review evidence only; it is not merge authority.

## Blocking findings

### P0 — External holdout fail-closed behavior is not regression-tested to the approved boundary

`trust-ci/tests/test_change_spec_holdout.py` has only three scenarios: one valid spec, missing SHA plus malformed JSON, and a spec-file symlink. The binding architecture ruling R6 explicitly requires behavioral temporary-git-history coverage for invalid/nonexistent or mismatched SHAs, diff failure, deletion, multiple changed specs, unchanged legacy exclusion, changed-v1 downgrade rejection, byte/depth/node/file-count limits, and unsafe inputs. Those cases exercise the independent merge-boundary implementation and cannot be replaced by source inspection or the local validator suite.

Required repair: add table-driven/fixture-based holdout tests for each named failure mode, including assertions that each case exits non-zero and that unchanged historical v1 specs are skipped while added/modified v1 specs fail. Keep the tests independent of `adaptive_grok.spec`.

### P0 — Receipt and verification traceability lacks required stale/selection regressions

`tests/test_change_receipts.py` proves sorted criterion binding and staleness after changing the spec/tree, but does not cover the other declared fingerprint inputs or compatibility rules: declared-contract content changes, route base-commit changes, Git HEAD changes, legacy receipts with missing bindings being readable but insufficient, inconsistent explicit bindings, and binding for every review receipt kind. There is also no direct test of PR/release selection of the active spec plus every changed/new spec, changed-v1 downgrade rejection through verification, or the exact docs-only micro exemption predicate.

Required repair: add focused tests for every fingerprint input and old-receipt behavior, plus verification tests covering active/multiple changed specs, missing/deleted specs, canonical-only gate parsing, fast-vs-gate behavior, and both sides of the docs-only exemption.

### P0 — New Trust CI metadata is not proven through the signed runner path

`trust-ci/tests/test_runner.py::test_spec_metadata_is_deterministic_data_only` unit-tests extraction, but the runner success test uses only `docs/x.md`. No test proves that a changed typed spec reaches the stored and signed `AttestationPayload` with the expected `spec_digest` and declaration coverage, or that a metadata extraction failure produces a failed signed outcome without running later commands. The signing regression proves a pre-M1 envelope remains valid, but it does not prove tamper rejection specifically for the new metadata fields or new-metadata store/replay.

Required repair: add runner-level tests for valid spec metadata, malformed/unsafe extraction failure, signed-field tampering, and store/replay of a new-format envelope. Assert exact digest/coverage values and that command execution stops on extraction failure.

## Important coverage gaps

### P1 — Local parser/generator/CLI boundary cases are only partially covered

The local suite checks duplicate keys, NaN, BOM, trailing data, one oversized string, one unsupported schema keyword, and one low-risk/simple route. It does not directly cover invalid UTF-8, whole-file byte limit, nesting/node/collection limits, spec symlink/non-regular input, unsafe/missing test and contract paths, unsupported keywords hidden in unused `$defs`, hostile route text with quotes/backslashes/newlines/Unicode, medium/high risk mapping, explicit positional CLI paths, default active-path resolution, or invalid CLI exit payloads.

Required repair: add compact table-driven negative tests and hostile route serialization/risk-mapping cases. Add at least one schema-preflight test where the unsupported keyword exists only in an unused `$defs` branch.

## Independent commands run

- `python3 -m unittest discover -s tests` — PASS, 207 tests.
- `PYTHONPATH=trust-ci/src /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest discover -s trust-ci/tests` — PASS, 153 tests, 8 skipped.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src` — PASS.
- `python3 scripts/grok_verify.py --mode pr --no-record --json` — PASS; all reported checks passed, active spec gate-valid, 6/6 acceptance criteria declaration-mapped, tree fingerprint `601146ac68db57e6f1e934a6679f347bf26ed43c5e6b19233f3e639e606d62a4` before this report.

The green commands show current examples pass; they do not close the missing security-boundary regression coverage above. Do not record a passing `test_review` receipt for this snapshot.
