# Code review 3 — M1 typed intent/evidence

## Verdict: BLOCKED

Reviewed exact commit `1e3c5ce3cde0f60a65343e7df1764ced4e56c290` (tree `17a35ab5833f317154a230a64e5532c246e8ba81`) against `5b571b5452f9ffe1a9ee4f55374b49a9de541db8`, the earlier review reports, and the active M1 package. The second-remediation changes close the previously reported NUL/control-character, spec-local duplicate-ID, stable qualified aggregation, malformed raw-digest, aggregate-bound, and pre-M1 replay defects. One correctness/security-boundary defect remains in relevant surrounding code, so AC-005/AC-006 and INV-001 are not satisfied yet.

## Blocking finding

### P1 — Trusted changed-file discovery is not NUL-delimited, so valid Git paths can be omitted or changed before approval and provenance processing

`trust-ci/src/adaptive_trust_ci/workspace.py:74-88` obtains changed paths with `git diff --name-only`, decodes the entire result as text, calls `splitlines()`, strips each fragment, and changes every backslash to `/`. Git quotes unusual pathnames by default. A pathname containing LF, tab, quotes, or backslash therefore does not survive this pipeline: for example, Git's line-form output for the actual path `engineering/changes/line\nbreak/change-spec.yaml` is the quoted text `"engineering/changes/line\\nbreak/change-spec.yaml"`; the current parser produces two/mangled logical fragments rather than the actual pathname. A direct reproduction also showed that `git diff --name-only -z` returns the exact bytes `b'engineering/changes/line\nbreak/change-spec.yaml\x00'`.

This is observable in the M1 trust path, not merely display behavior:

- `trust-ci/src/adaptive_trust_ci/runner.py:212-248` derives `spec_digest` and `criterion_coverage` exclusively from `checkout.changed_files`, and `runner.py:366` derives protected approval scopes from the same tuple.
- Both M1 spec selectors accept a non-slash control character in the change directory (`runner.py:25,213`; `trust-ci/holdout.example/change_spec_validate.py:16,87-96`).
- The independent holdout correctly uses `git diff --name-only -z` and strict UTF-8 decoding (`change_spec_validate.py:87-93`), so it sees and validates the real changed spec while the trusted runner can omit it. A passing job can consequently sign `spec_digest=null`, `spec_count=0`, and no coverage for a changed v2 spec. The same parser also weakens approval-scope derivation for unusual protected paths.

Required remediation: make `GitWorkspace` obtain the exact path set from byte-oriented `git diff --name-only -z --no-renames`, split only on NUL, decode each pathname strictly as UTF-8, and preserve characters rather than stripping/replacing them. Then explicitly and consistently reject unsupported control/backslash spec paths in both the runner and holdout (or support them end to end), and add real `GitWorkspace` regression tests proving exact changed-file identity, protected-scope derivation, and M1 provenance for LF/tab/backslash pathnames.

## Prior findings verified closed

- **NUL/control contract paths:** `.grok-stack/adaptive_grok/spec.py:548-575` rejects Unicode control/format/surrogate/separator characters before filesystem calls and normalizes `OSError`/`ValueError` to `SpecError`; the holdout has the equivalent rule at `trust-ci/holdout.example/change_spec_validate.py:187-194`. Both focused tests passed, including the exact-SHA NUL case.
- **Spec-local duplicate IDs and stable aggregation:** `trust-ci/src/adaptive_trust_ci/runner.py:221-248` validates IDs per document, deterministically sorts selected specs, and qualifies multi-spec unmapped IDs as `<spec-path>#<AC-id>`. `trust-ci/src/adaptive_trust_ci/models.py:25-56` accepts both legacy bare IDs and bounded qualified IDs while maintaining count consistency. The focused duplicate/qualified-ID runner test passed in both input orders.
- **Malformed raw provenance:** `runner.py:221-247` records `{path, raw_digest, semantic_digest: null}` before parsing and attaches the composite digest to `SpecMetadataError`; `runner.py:422-433` preserves that digest in the signed failure path. The focused exact-raw-digest and signed-malformed tests passed.
- **Aggregate bounds and compatibility:** excess aggregate coverage now becomes a controlled signed failure, and the committed pre-M1 runner/signature replay tests pass. PostgreSQL compatibility fixtures/tests were added; those integration tests remain environment-skipped when `TRUST_CI_TEST_DATABASE_URL` is absent.

## Verification evidence

- `git diff --check 5b571b5..1e3c5ce`: PASS.
- Focused local NUL/control test: 1 passed.
- Focused Trust CI remediation tests (qualified duplicate IDs, malformed raw digest, bounded aggregate failure, pre-M1 runner replay, holdout controls): 5 passed.
- Clean archived exact-HEAD Trust CI suite with the runner's required `PYTHONDONTWRITEBYTECODE=1`: 177 passed, 10 skipped.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS; 222 root tests passed and current spec coverage was 6/6.

## Non-blocking test-isolation observation

Without `PYTHONDONTWRITEBYTECODE=1`, `test_change_spec_holdout` writes `trust-ci/holdout.example/__pycache__`; `bundle_digest()` hashes every regular file under that directory, so the later `test_example_holdout_digest_matches_example_bundle` fails (clean archived reproduction: 176 passed, 1 failed, 10 skipped). The production runner sets `PYTHONDONTWRITEBYTECODE=1` at `runner.py:635-650`, so the policy-bound suite passes, but making the source-tree test independent of ambient bytecode settings would prevent misleading local failures.
