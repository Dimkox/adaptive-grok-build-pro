# Local implementation evidence — issue 168

This records the initial implementation candidate. Independent review subsequently found pathname-identity regressions; see [review-repair.md](review-repair.md) for the bounded repair and its newer focused evidence. Initial measurements below remain historical, not verification of the repaired candidate.

The route-selected integration_implementer changed only `.grok-stack/adaptive_grok/util.py`, new `tests/test_util_fingerprint.py`, and one receipt integration test in `tests/test_change_receipts.py`. No receipt format, deployed policy, dependency, or external resource changed.

`changed_files` now obtains a NUL-separated index inventory and retains tracked diff provenance before filtering. Both rename endpoints remain visible through `--no-renames`; staged deletions are protected even after disappearing from the index. Existing runtime/cache exclusions and the exact top-level `.qwen/tmp/` exemption apply only to proven-untracked candidates. Index or diff uncertainty disables those exclusions. No-HEAD fallback retains scratch and indexed paths, including missing staged files. Existing lexical separator normalization is retained; classification does not resolve symlinks.

## Measured regression evidence

- Before product edits: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest tests.test_util_fingerprint tests.test_change_receipts.ReceiptTests.test_receipt_survives_scratch_churn_but_stales_on_product_edit` ran 10 tests in 4.408 s with 40 assertion failures, no errors. These reproduce scratch churn, tracked legacy-noise omissions, rename provenance, and conservative fallback failures.
- After repair and two additional characterization cases: the same command ran 12 tests in 6.163 s, all passing. It also covers a staged deletion recreated as untracked (subsequent byte changes remain bound), failed diff inspection, malformed/nonzero/timeout index results, unborn/non-Git repositories, prefix lookalikes, configuration, force-added ignored scratch, and existing untracked noise.
- `python3 -m ruff check .grok-stack/adaptive_grok/util.py tests/test_util_fingerprint.py tests/test_change_receipts.py`: pass.
- `git diff --check`: pass.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest tests.test_change_receipts tests.test_verification_doctor`: 92 tests passed in 222.691 s. This includes the existing regression that refuses to receipt verification after a genuine product mutation.

Raw logs remain host-local under `/home/pall/.cache/agbp-run/issues-wave-20260921/fingerprint/`: `red-clean.log`, `green.log`, and `integration.log`. The earlier `red.log` includes cascading fixture errors because failed subtests skipped cleanup; cleanup was moved into `finally` before the clean RED run. Coordinator owns the corresponding concise shared-memory entry.

The coordinator owns full PR verification and independent code/test/security review, then final fingerprint-bound receipts. This repair does not claim to solve all pre-existing Git enumeration failures: unsuccessful path queries still cannot contribute paths they did not return, but cannot authorize the new scratch exemption.

Rollout is source adoption and regeneration of local evidence; formerly hidden tracked cache changes may invalidate old receipts once. Recovery follows [rollback.md](../rollback.md): restore conservative inclusion, rerun tests and reviews, and regenerate receipts. Historical hashes must never be relabeled.
