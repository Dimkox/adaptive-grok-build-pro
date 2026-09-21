# Independent code review — repaired issue 168

Recommendation: **PASS for the inspected source; no remaining actionable code finding.** Final full verification and fingerprint-bound receipts are still pending and are not established by this report.

Reviewed 2026-09-21 at 08:06 UTC as the route-selected `code_reviewer`, independently of the sole implementation owner. Route: `582c39d6afb6`. Base: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`; repaired HEAD: `8278b2dd9b3fff69b5e408087c2e3b49a68e470c`; HEAD tree: `7abf3f307f88018ac5241c627790027e3f9b1db8`. The worktree was clean when this review began, and the four product files remained identical to HEAD before this report was written. The initial failure is preserved in [code-review-first.md](code-review-first.md).

## Finding disposition

**CR-001 resolved.** `_git_paths()` now captures Git's NUL-delimited output as bytes and uses `os.fsdecode()` for individual paths. It no longer passes those bytes through the shared strict text-mode `run()` wrapper. This removes the reproduced exception for excluded non-UTF-8 scratch names and clean tracked non-UTF-8 names. `tree_fingerprint()` uses `os.fsencode()` for path identity and symlink targets, preserving the original filesystem bytes when included names reach hashing. Binary capture also preserves literal carriage returns. Nonzero subprocess status, timeout, OS error, or an unterminated inventory returns uncertainty rather than authorizing exclusion.

The security review's literal-backslash finding is also addressed in the actual diff: no path normalization remains between Git enumeration, exact slash-delimited prefix matching, and file lookup. A POSIX filename containing a backslash cannot be moved into `.qwen/tmp/` by classification. The new regressions cover all three reported lookalike spellings through create, edit, and removal.

The approved JSON repair is consistent with the filesystem-byte handling. `dump_json()` and verifier `--json` now emit ASCII escapes, allowing surrogate-escaped filenames to round-trip through valid UTF-8 JSON text. Ordinary Unicode values remain identical after parsing. JSON field/schema definitions, shared command execution, receipt authority, and canonical digest functions are unchanged. Reviewed persistence consumers read the JSON values; canonical receipt/verification digest helpers already use their own ASCII serialization.

## Whole-change assessment

Inspected the full product diff from the frozen base, the repair delta from `5adc4f853741ced0f1332fcdb2d5e5d95446bed4`, complete utility and new regression suite, both receipt additions, verifier CLI output, and surrounding receipt/verification/routing/state consumers. Read the current route and approved brief, specification, architecture, recovery, test plan, and repair evidence.

- Tracked diff provenance is retained before applying any noise filter. Staged deletion/recreation and both rename endpoints remain bound; `--no-renames` preserves base-relative path coverage.
- The new exemption remains confined to proven-untracked paths below the literal top-level `.qwen/tmp/` boundary. Configuration, ordinary source, prefix lookalikes, and tracked legacy-noise paths remain included.
- Index or tracked-diff uncertainty disables exclusions for successfully enumerated candidates. The non-Git/unborn fallback retains scratch and indexed missing paths. Existing Git enumeration limitations are not presented as newly repaired behavior.
- The tests assert fingerprint equality for scratch churn and inequality for meaningful edits, exercise real temporary Git repositories, and verify actual receipt freshness/staleness. New byte/path tests cover the reproduced failures and downstream JSON boundaries without replacing them with a length-only assertion for changed content.

## Evidence and limits

Directly inspected the raw repair logs under `/home/pall/.cache/agbp-run/issues-wave-20260921/fingerprint/`: `review-red.log` records 19 tests in 6.771 seconds with 3 assertion failures and 8 errors; `review-green.log` records all 19 passing in 7.928 seconds. Inspected the corresponding test bodies and [review-repair.md](review-repair.md). The CLI JSON test uses a synthetic verification report and does not claim to execute the full gate.

No new probe, project test suite, lint/compiler task, Docker workload, remote fetch, external write, secret read, or product modification was performed during this renewed review. The earlier 92-test and full-gate results describe the pre-repair tree and are not reused as current verification. The coordinator must run the mandatory final full gate and bind fresh receipts after evidence changes. This source-review pass does not replace the exact-PR-head external Trust CI check or required human scopes.

Reviewed product SHA-256 identities:

```text
3b99030bf8c238315202f623e5969414f858f47280e31f602080ca371a85affd  .grok-stack/adaptive_grok/util.py
1485a73945adf32c6ebd711640efe8c8918112a37649889601b5c2e33a0474ca  scripts/grok_verify.py
664a52083882942aecd0db4cb9ab1d688a1a958b82672d9525bc6601dd70323f  tests/test_util_fingerprint.py
da874e190549f6d821ae55f2946ffca30577c8024a13e4ce3137e5baa3425496  tests/test_change_receipts.py
```
