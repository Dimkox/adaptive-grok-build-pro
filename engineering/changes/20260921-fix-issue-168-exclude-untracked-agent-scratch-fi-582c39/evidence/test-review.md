# Renewed independent test review — issue 168

**Recommendation: PASS for test adequacy of the corrected bounded change; final full verification is still pending.** No blocking test finding. The earlier [test review](test-review-first.md) covered ordinary paths and missed the filename-transport cases found by independent code/security review; it is historical, not evidence for this corrected tree.

Reviewer: route-selected `test_reviewer` (`fingerprint_test_reviewer`), independent of the sole implementation owner. Route `582c39d6afb6`; 2026-09-21. Reviewed HEAD `8278b2dd9b3fff69b5e408087c2e3b49a68e470c`, tree `7abf3f307f88018ac5241c627790027e3f9b1db8`, in `/home/pall/grok-projects/adaptive-grok-build-wave-fingerprint`. Inspected both the repair from `5adc4f853741ced0f1332fcdb2d5e5d95446bed4` and the complete resulting utility/test behavior relative to frozen base `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`.

Read refreshed bootstrap/state/route, approved scope/specification, design, test plan, [review repair](review-repair.md), and the preserved failed code/security reports. Reused the already-read contract, role and applicable skills. Reviewed all 17 focused utility tests, both receipt regression cases, the verifier CLI serialization change, and the existing source-mutation regression. Only this report was written. No suite, lint, compiler, Docker workload or synthetic execution was started; this is static review plus direct inspection of coordinator-owned execution records.

## Coverage and repair assessment

| Boundary | Assertions and implementation inspected | Assessment |
| --- | --- | --- |
| Exact scratch exemption | Real committed temporary Git fixtures retain the original create/edit/remove stability check for `.qwen/tmp/`, including spaces and a newline, plus existing untracked cache/runtime controls. | AC-001 and existing noise behavior remain covered. |
| Literal backslashes | All three independently discovered spellings, `.qwen\tmp\payload.py`, `.qwen/tmp\payload.py` and `.qwen\tmp/payload.py`, must appear literally in `changed_files`; creation and content edits change the fingerprint, and removal restores the prior fingerprint. | Detects conversion of legal filename characters into scratch separators. The implementation now uses actual forward-slash directory boundaries without backslash normalization. |
| Non-UTF-8 filenames | Untracked scratch with byte `0xff` remains excluded without a decoding exception; a clean committed byte-valued name permits fingerprinting. Included `0xff`, `0xfe` and carriage-return filenames are checked for exact returned identity, creation, untracked content changes and tracked content changes. | Binary Git output avoids text decoding/newline translation; `os.fsdecode` plus `os.fsencode` preserves filesystem identity and content binding. Exact-membership assertions also reject lossy replacement. |
| Symlink targets | An untracked symlink with target byte `0xff` must bind, and replacing only its target with byte `0xfe` must change its fingerprint. | Exercises target bytes without requiring a valid target file. The implementation hashes the filesystem encoding of `os.readlink`. |
| Tracked provenance | Original tests still cover nine scratch/cache path families, staged/unstaged edits and deletions, force-added ignored scratch, immediate staging, both rename endpoints, base-relative deletion, and staged deletion recreated as untracked. | AC-002 remains protected independently of the new byte transport. |
| Configuration/lookalikes | Original tracked/untracked configuration, ordinary source, nested scratch spelling, prefix lookalikes and exact `.qwen/tmp` filename controls remain. | AC-003 is now complemented by literal-backslash and byte-name controls instead of assuming every path is ordinary text. |
| Git uncertainty and no HEAD | Updated mocks target the new subprocess boundary and exercise nonzero exit, raised `TimeoutExpired`, raised `OSError`, unterminated binary records, and failed diff inspection. Real non-Git/unborn cases retain scratch and indexed missing content. | AC-004 tests the actual new exception/result handling; uncertain inventories cannot authorize filtering. |
| JSON and receipts | `dump_json` and the actual verifier CLI entry point must emit UTF-8-encodable JSON whose parsed values preserve filename surrogates and ordinary Unicode. A real synthetic receipt carries a byte-valued filename, round-trips it, validates as fresh, then becomes stale when that file's content changes. The scratch/product receipt case still checks original receipt bytes remain unchanged. | Covers the approved serialization scope and AC-005 without redefining schema or authority. The CLI test mocks verification itself and proves serialization/exit behavior only. |

The existing `test_verify_does_not_receipt_checks_from_an_older_fingerprint` still requires a failing source-stability check and no verification receipt after a product file changes during verification. It was inspected but was not part of the new 19-test command; the final full gate must rerun it on this repair. Shared `run` behavior remains unchanged: only the dedicated Git path helper uses binary subprocess output. JSON escaping changes serialized representation while the tested parsed values remain equal.

## Recorded RED/GREEN evidence

Inspected raw `/home/pall/.cache/agbp-run/issues-wave-20260921/fingerprint/review-red.log` and `review-green.log`, rather than accepting their summary alone. The committed repair record supplies this command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:.grok-stack python3 -m unittest tests.test_util_fingerprint tests.test_change_receipts.ReceiptTests.test_receipt_survives_scratch_churn_but_stales_on_product_edit tests.test_change_receipts.ReceiptTests.test_receipt_roundtrips_non_utf8_changed_file_names
```

- RED records 19 tests in 6.771 seconds, with exactly 3 assertion failures and 8 errors. The three assertions name the three literal-backslash spellings. The errors expose strict Git decoding, strict path/target encoding and unescaped JSON output.
- Evidence qualification: two errors in the `0xfe` and carriage-return subtests occur while taking their initial fingerprint because the first failed `0xff` subtest left its file behind. They are cascading errors, not independent reproductions of those two inputs. Likewise, the combined scratch/clean-tracked test stops at its scratch assertion in RED. The log proves the relevant defect classes but must not be described as eleven independent defect reproductions. Per-subtest cleanup would improve future failure isolation; this does not invalidate the fully exercised GREEN run.
- GREEN records 19 tests in 7.928 seconds, `OK`, with no skips or errors reported. It reaches all create/edit/remove, byte-name, clean-index, target, JSON and receipt assertions inspected above.
- These raw focused logs do not contain independent start/end HEAD metadata. Their association with this repair is the committed implementation record; the exact reviewed source identity is recorded below. The old 92-test run and initial full gate belong to the earlier product and are not reused as repaired-tree verification.

| Raw record | Bytes | SHA-256 |
| --- | ---: | --- |
| `review-red.log` | 17432 | `be3a059dcbd7af439dd6a97773ce46fe5889fa19e61175b90e42bc0d1b1c1e3e` |
| `review-green.log` | 118 | `9196dbc3f0e63db8abcc131a8137cdd04b2b658638592693fb06d061c4713da4` |

## Reviewed product identity and limits

All four product files had no worktree diff against the reviewed HEAD when inspected:

| File | SHA-256 |
| --- | --- |
| `.grok-stack/adaptive_grok/util.py` | `3b99030bf8c238315202f623e5969414f858f47280e31f602080ca371a85affd` |
| `scripts/grok_verify.py` | `1485a73945adf32c6ebd711640efe8c8918112a37649889601b5c2e33a0474ca` |
| `tests/test_util_fingerprint.py` | `664a52083882942aecd0db4cb9ab1d688a1a958b82672d9525bc6601dd70323f` |
| `tests/test_change_receipts.py` | `da874e190549f6d821ae55f2946ffca30577c8024a13e4ce3137e5baa3425496` |

Filesystem-byte/backslash/target cases are deliberately POSIX-specific. Timeout behavior is exercised by raising the actual exception type, not by waiting for a real process timeout. No physical index-file-removal case or complete end-to-end verifier run with exotic filenames is claimed. The repair remains bounded; it does not recover every path omitted by a pre-existing failed Git enumeration command.

The coordinator must run the mandatory final full gate and bind verification/review receipts after the remaining repository evidence changes. This report is a test-adequacy recommendation, not current final-tree verification, external Trust CI success, or merge authority. Any later product change requires review refresh.
