# Review response — stream oversized tracked binaries

Reviewed object for both reports: `d13bf59`. Every finding below was reproduced in this worktree before
being acted on; the dispositions land in the follow-up commit, and the pull request opens on that head.

## `review-code.md` — PASS (1 Important, 6 Minor)

| # | Finding | Verified | Disposition |
| --- | --- | --- | --- |
| I-1 | Important — the first `Popen` bypassed `_run_capped`: the deadline guarded only `wait()`, not the blocking `stdout.read()`, stderr was uncapped, and `kill()` did not reap — a stalled `git cat-file` could wedge the verifier instead of failing in 30 s | read `_run_capped` (lines 73-150): non-blocking pipes + `selectors` + deadline + per-stream limits + `_stop_process` | **Fixed.** Extracted `_stream_git_blob()` on the same discipline: `start_new_session=True`, non-blocking pipes, `selectors` loop under `_GIT_TIMEOUT_SECONDS`, capped stderr (64 KiB), a hard ceiling that fails as soon as more bytes arrive than `git ls-tree -l` promised, `_stop_process` (group kill + reap) on every error path, and explicit `raise` where the pipe contract is unmet. |
| M-1 | `assert process.stdout is not None` would vanish under `python -O` while the module raises elsewhere | compared with the module's style at line 98 | **Fixed** — explicit `ArchitectureError("streamed blob pipes are unavailable", code="io")`. |
| M-2 | `f"…{message or total != size}"` could print `True` as diagnostic text | read the expression | **Fixed** — stderr detail, else `exit <returncode>`; truncation reports `"<n> of <m> bytes"`. |
| M-3 | Files at or below the limit were walked twice (profile opened, then `_worktree_blob` re-walked) — extra syscalls and a new `"vanished during analysis"` race window | reproduced by reading my own `_profile_worktree_blob` | **Fixed.** The profile now performs one O_NOFOLLOW walk and hashes while reading, retaining chunks only for `size <= MAX_ANALYZED_FILE_BYTES`; the race branch and its message are gone. Behaviour stays identical: digest still equals the buffered `sha256`. |
| M-4 | ~1.5× more git spawns per oversized path | accepted | Accepted: one extra `ls-tree -l` per oversized path, bounded by `MAX_CHANGED_PATHS`, and it replaces a whole-object read. |
| M-5 | Tests sniffed NUL only in the first chunk | reviewer's own probe showed the code is right | **Fixed** — `test_oversized_binary_marker_is_found_anywhere_in_the_stream` puts the NUL in the last byte of a >10 MB object. |
| M-6 | `brief.md` claimed "no new subprocess surface" | true by inspection — this is a second process site | **Corrected** in prose: it names the second site and states the discipline it is built to, instead of denying it. |

The reviewer's confirmations were re-checked rather than adopted: no descriptor leak on the error paths,
`_EXACT_SHA` validation before the id reaches argv, the oversized entry still present in `artifacts` and
charged to `MAX_DIFF_ARTIFACT_BYTES`, no `MAX_*` value changed, and ≤limit behaviour unchanged.

## `review-test.md` — PASS (2 Important, 3 Minor)

| # | Finding | Verified | Disposition |
| --- | --- | --- | --- |
| I-1 | Important — **measured**: patching `MAX_ANALYZED_FILE_BYTES` to 20 MB leaves the whole suite green, so `FORBID-001` had no test evidence | consistent with the design: every oversized fixture scales off the constant, so a widened constant just scales the fixtures | **Fixed.** `test_analysis_memory_constants_are_pinned` asserts the three memory constants by value (`10_000_000` / `20_000_000` / `50_000_000`) and that the stream chunk is smaller than the analysis limit. Widening the cliff now fails the suite, and AC-002 cites that test. |
| I-2 | Important — mid-stream `changed/truncated during analysis` guards were untested | `architecture_diff.py` guards confirmed unexercised | **Fixed.** `test_oversized_binary_reports_modified_and_refuses_truncated_stream` patches `os.read` to return one byte short and requires `"was truncated during analysis"`. |
| M-1 | No coverage of an oversized `modified` (only `added`) | — | **Fixed** in the same test: both digests, both sizes and `None` line counts asserted for a real base→head oversized binary change. |
| M-2 | Worktree cases lacked `base_size`/line-count symmetry | — | **Fixed** for the modified case; the added-case symmetry is implicit (`base_size == 0`). |
| M-3 | Symlink-ancestor and FIFO paths untested; symlink observed failing as `worktree file read failed: … Too many levels of symbolic links` | accepted as recorded | **Deferred, stated.** The pre-fix code reaches the same message through the same walk, so this is not a regression introduced here; the existing symlink test still covers the direct-component case. |

## After the follow-up

- `python3 -m unittest tests.test_architecture_fitness` → **Ran 106 tests, OK**
- `tests.test_architecture_model`, `tests.test_landing_architecture_boundaries`, `tests.test_change_spec`,
  `tests.test_verification_doctor` → **Ran 166 tests, OK**
- Real-tree proof re-run after the rewrite: worktree and commit modes both yield
  `status=added`, `head_size=10940676`, `head_digest=770f1db5725e666b…`, equal to the buffered `sha256` of
  `packages/adaptive-grok-build-pro-v2.0.17.zip`, with `added_lines=None`.
- `ruff` clean; `grok_verify --mode pr` and the full repository suite belong to the parent run and are
  recorded after this commit.
