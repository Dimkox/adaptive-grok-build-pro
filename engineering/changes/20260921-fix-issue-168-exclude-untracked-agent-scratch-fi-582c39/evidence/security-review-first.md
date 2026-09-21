# Independent security review — issue 168

Status: **FAIL — one blocking regression (P2)**. Review date: 2026-09-21. Reviewer role: route-selected `security_reviewer`; route `582c39d6afb6`.

Reviewed baseline `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48` against HEAD `5adc4f853741ced0f1332fcdb2d5e5d95446bed4`, including the actual utility, focused tests, receipt integration test, change specification, and surrounding receipt/verification consumers. No product files were changed by this reviewer. Only this report was written.

## Blocking finding

**P2 — Preserve literal Git path identity before applying the scratch exemption.** `.grok-stack/adaptive_grok/util.py:155` converts every backslash in NUL-delimited Git output to `/`; line 178 then treats the converted name as an exact `.qwen/tmp/` descendant. On POSIX, a backslash is a legal filename character, and Git `-z` returns it literally. Consequently a top-level file named `.qwen\tmp\payload.py`, a file `.qwen/tmp\payload.py`, or a directory/file `.qwen\tmp/payload.py` is outside the actual scratch subtree but is now omitted entirely from `changed_files()`. Creating any of these files leaves `tree_fingerprint()` unchanged. This violates AC-003 and INV-002 and weakens local receipt freshness and the changed-file inventory shared by verification.

An independent disposable-repository probe loaded the baseline and current utility source, committed an ordinary source file, then created and edited each filename. It completed in 0.352 seconds without executing a suite or touching repository product files. Results:

| Actual repository-relative path | Baseline creation changes fingerprint | Current creation changes fingerprint | Current changed paths |
| --- | --- | --- | --- |
| `.qwen\tmp\payload.py` | yes | **no** | `[]` |
| `.qwen/tmp\payload.py` | yes | **no** | `[]` |
| `.qwen\tmp/payload.py` | yes | **no** | `[]` |
| `.qwen/tmp/payload.py` (intended scratch control) | yes | no | `[]` |

For the first case, the real Git output was the raw path followed by NUL: Python representation `'.qwen\\tmp\\payload.py\x00'`. Baseline `changed_files()` returned `['".qwen//tmp//payload.py"']`, whereas current `changed_files()` returned `[]`.

The distinction from the pre-existing weakness matters: the baseline already quoted/misnormalized these unusual names and did not bind subsequent byte edits correctly. This change newly removes their path presence too, so creation/removal outside the approved subtree becomes invisible. The finding does not claim that the baseline provided correct byte binding for these paths.

Required repair: preserve the actual NUL-delimited Git path identity for provenance, exact subtree classification, and file lookup; add a regression for the literal-backslash lookalikes covering creation and byte edits. Do not normalize a POSIX filename into a different ownership boundary. Rerun affected verification and independent reviews after the write owner repairs it; this report must not produce a passing security receipt.

## Other reviewed boundaries

- Index membership plus diff provenance retains ordinary tracked scratch/cache edits, deletions and staged additions. Staged deletion/recreation remains bound through the staged diff after index membership disappears. `--no-renames` preserves both endpoints and base-relative provenance. The focused tests exercise these cases.
- An unsuccessful, timed-out or unterminated index/diff inventory prevents the new exclusion. No-HEAD and non-Git fallback keeps scratch conservatively. Failed untracked enumeration still cannot supply undiscovered paths; that is an acknowledged existing limitation, not introduced authority to classify them as scratch.
- An independent 0.061-second symlink-boundary probe confirmed `.qwen/tmp` and `.qwen` directory symlinks themselves remain visible and their creation changes the fingerprint. Classification does not resolve a symlink into an excluded prefix. Untracked entries genuinely below the permitted scratch path retain the intended exemption.
- Receipt schemas and validation authority are unchanged; `validate_evidence()` still compares the current fingerprint with the stored value. The product diff does not rewrite old receipts or modify Trust CI, external policy, approval scopes, keys, branch protection, or deployment state. Local review remains workflow evidence only and cannot authorize merge.

## Evidence binding and limitations

The coordinator's saved full-gate metadata records `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json`, exit 0, at 07:35:39–07:43:53 UTC for the reviewed HEAD. The JSON records `status: pass`, route PR mode, and fingerprint `f4ebf05ae78b2b60901341ecd21b7ac9ccfdbb820a1ccff72560318cf895b4cd`. I inspected that recorded result; I did not rerun the full gate or the focused/adjacent suites. Passing existing checks does not cover the reproduced filename regression.

Reviewed source SHA-256 values:

- `.grok-stack/adaptive_grok/util.py`: `37b1fd4754f091761d9d4e55f1948b9a927b3cc526cdf439f546ea8999460d7a`
- `tests/test_util_fingerprint.py`: `ae27d2a91f532cd1b9c2460a4cf5222ee93abf3a2779a63ac0312b1ec7c82419`
- `tests/test_change_receipts.py`: `a4b3d0bc98689e10bc17f60c417692d651fd0abcde1207cefa5a852afdf828d5`

The conclusion is bound to those files and the reviewed commit, not to a future repair. Writing this report also changes the repository tree; final receipts require the coordinator's normal final-tree binding.
