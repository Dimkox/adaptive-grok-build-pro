# Independent code review — issue 168

Recommendation: **FAIL; return the finding below to the selected integration_implementer.**

Reviewed 2026-09-21 at 07:49 UTC as the route-selected `code_reviewer`, independently of implementation. Route: `582c39d6afb6`. Review base: `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`; implementation HEAD: `5adc4f853741ced0f1332fcdb2d5e5d95446bed4`; HEAD tree: `2b20d05e68a86b00d87697881ec0374c169b79ba`. Product sources were unchanged during this review; the coordinator's change-state update was already uncommitted. This report is not a passing receipt or external merge authority.

## Finding CR-001 — P2: preserve filesystem bytes when reading NUL-separated Git paths

Location: `.grok-stack/adaptive_grok/util.py:150-155`, reached by the new index inventory at line 160 and each NUL-separated diff/untracked inventory.

`_git_paths()` sends raw `git ... -z` output through `run()`, whose `subprocess.run(text=True)` decodes with strict text handling. Git no longer quotes filename bytes in this mode. On this Linux host, any legal filename containing a non-UTF-8 byte makes that call raise `UnicodeDecodeError` before the inventory failure handling or scratch exclusion runs. The new complete index inventory means even an otherwise clean repository with such a committed filename can no longer obtain a fingerprint; an untracked file under the intended scratch exemption also blocks fingerprinting. Routing, receipt validation, and verification call this shared utility.

A coordinator-authorized synthetic temporary-Git A/B probe executed in 0.064 seconds, using the baseline module read with `git show` and the actual current module. Both fixtures had a committed ordinary source file. One added an untracked `.qwen/tmp/` basename containing byte `0xff`; the other committed an ordinary filename containing that byte and left a clean tree. Controlled output (no raw undecodable filename was printed):

```text
untracked_scratch baseline success sha256_length=64
untracked_scratch current exception=UnicodeDecodeError
clean_tracked_file baseline success sha256_length=64
clean_tracked_file current exception=UnicodeDecodeError
```

Use byte-preserving path enumeration/decoding and ensure included path names can be hashed and opened without lossy replacement or strict re-encoding failure. Merely changing decode errors to replacement can conflate distinct paths; merely catching the exception can drop candidates. Add regressions for the excluded untracked scratch name and the clean tracked name, plus included changed-file binding after any filesystem-byte decoding adjustment. Return the repair to the same write owner and rerun affected verification/review.

## Inspected behavior and evidence

- Inspected the actual product diff in `util.py`, the complete new `test_util_fingerprint.py`, and the receipt integration addition; read surrounding fingerprint, receipt, and verification consumers, the route, change brief/spec, architecture, acceptance, recovery, analysis reports, and implementation evidence.
- The ordinary-path implementation correctly separates tracked diff provenance from untracked filtering. `--no-renames` keeps both endpoints; staged deletion/recreation retains diff provenance even after losing index membership. Exact slash-delimited `.qwen/tmp/` checks preserve the tested configuration/prefix lookalikes. Git command failure disables exclusions for candidates returned by successful queries. The non-Git/unborn fallback retains scratch and indexed missing files.
- Directly inspected `red-clean.log`, `green.log`, and `integration.log`: 10 tests with 40 assertion failures before repair, 12 focused tests passing after repair, and 92 adjacent tests passing. This is evidence inspection, not a reviewer rerun of those suites.
- Directly inspected `verify-initial.json` and `verify-initial-meta.json`: `GROK_TEST_WORKERS=8 python3 scripts/grok_verify.py --mode pr --json` exited 0 on the named HEAD between 07:35:39 and 07:43:53 UTC; report status and source stability passed at fingerprint `f4ebf05ae78b2b60901341ecd21b7ac9ccfdbb820a1ccff72560318cf895b4cd`. The supplied verification does not exercise CR-001. Subsequent evidence/state edits require fresh final receipt binding.

Reviewed product SHA-256 identities:

```text
37b1fd4754f091761d9d4e55f1948b9a927b3cc526cdf439f546ea8999460d7a  .grok-stack/adaptive_grok/util.py
ae27d2a91f532cd1b9c2460a4cf5222ee93abf3a2779a63ac0312b1ec7c82419  tests/test_util_fingerprint.py
a4b3d0bc98689e10bc17f60c417692d651fd0abcde1207cefa5a852afdf828d5  tests/test_change_receipts.py
```

## Limits

Only the bounded synthetic path probe was executed by this reviewer. No project test suite, lint/compiler task, Docker workload, remote fetch, secret read, external write, or product modification was performed. This review does not claim that all pre-existing Git inventory failures are repaired. The selected security review independently covers lexical path identity; its findings must also be resolved before a final pass. External Trust CI and any required human scopes remain separate exact-PR-head requirements.
