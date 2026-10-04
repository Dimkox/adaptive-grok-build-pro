# Independent test review — final repair addendum

PASS for the focused90cc→5e2abf addendum. Both new stat-fault regressions and five neighboring controls passed; the cleanup-disabled mutant was killed. No new test-review finding.

## Identity and isolation

- HEAD before/after: `5e2abf58bceb57c270ad7ddd650945c89c7b650a`.
- Fingerprint before/after: `c0036e075dc15c5f8b983bcd9c4eec5af79c1f6e8d63192323238ab4ff19db74`.
- Candidate and exact private clone remained clean.
- Scratch relative to candidate: `../adaptive-grok-build-pro/.review-scratch/test-review-receipt-final-0CjaSP/`.
- Scratch/TMPDIR reviewer-owned0700, nonsticky, locally ignored.
- Capacity recorded before inspection at `2026-10-04T17:46:09Z`: 14 physical/28 logical; child-only widening verified28, cpuset0-27, no finite quota observed. Allocated CPUs6-11/max6 workers; every invocation limited175s.
- reviewed-tree-modified: no

## Executed claims

- First post-link stat failure preserves foreign in-place bytes, including valid same-length foreign JSON.
- Second stat failure after temporary-hardlink unlink removes unchanged owned bytes despite the ctime transition.
- Aborted reused/referenced artifacts and foreign-inode replacements remain preserved.
- Closed report-reference/envelope bindings and source-change refusal remain effective.
- Cleanup requires owned device/inode, original byte count/hash, and stable metadata across its bounded no-follow read.

Command, from the private clone, with `GIT_OPTIONAL_LOCKS=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=.grok-stack`, private TMPDIR, `GROK_TEST_WORKERS=6`, and `taskset -c 6-11 timeout 175s`:

```bash
python3 -B -m unittest -q \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_first_post_link_stat_fault_preserves_in_place_foreign_bytes \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_second_post_link_stat_fault_cleans_unchanged_bytes_across_ctime_boundary \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_aborted_reused_report_preserves_preexisting_referenced_digest \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_helper_abort_preserves_a_referenced_reused_artifact \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_helper_does_not_adopt_replacement_between_link_and_stat \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_publication_rechecks_source_before_receipt
```

```text
Ran 7 tests in 4.205s
OK
```

Private mutation command, with the same environment and bound:

```bash
python3 -B ../cleanup_mutation.py
```

```text
M1-cleanup-disabled: KILLED
tests=1 failures=1 errors=0 cleanup_calls=1
```

The second-stat/ctime regression failed because the unchanged owned report remained. Injection was exercised exactly once. No survivor or inconclusive result occurred.

Read-only checks:

```text
git diff --stat 90cc6cd6f475ac6486d762aadec99a37ea9ef9cf..HEAD
git diff 90cc6cd6f475ac6486d762aadec99a37ea9ef9cf..HEAD
git diff --check 90cc6cd6f475ac6486d762aadec99a37ea9ef9cf..HEAD
git rev-parse HEAD
git status --porcelain=v1
```

Inspected all five changed files and surrounding cleanup/publication/hydration code. Whitespace check passed. An explicit `git diff --exit-code` over installer, shared template, all nine launchers, installer tests, handoff/docs, QG/tests and architecture returned0, confirming those earlier repair bytes are unchanged.

Fingerprint command, run before/after in candidate and clone:

```bash
GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys,pathlib;sys.path.insert(0,".grok-stack");from adaptive_grok.util import tree_fingerprint;print(tree_fingerprint(pathlib.Path.cwd()))'
```

Limits: the original90cc full report and its findings remain retained. Its installer/handoff tests and mutations are historical evidence for unchanged source, not fresh5e2abf full qualification. No46/86/152-test rerun, full verifier, PostgreSQL, cap-boundary rerun, external check/approval validation, GitHub write or thread resolution occurred. Caps and public schema are unchanged by inspection only. Coordinator persistence, final verification and external exact-head gates remain outstanding.
