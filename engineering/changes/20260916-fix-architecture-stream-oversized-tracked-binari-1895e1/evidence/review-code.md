PASS

Independent code review — commit `d13bf59` (`fix/architecture-stream-large-binaries`), route `1895e17ff333`,
receipt kind `code_review`, base `cfc4a5741210cc7b28431c56c92b9d549540c65d`. Reviewer read the diff, the pre-fix
`_worktree_blob`/`_git_blobs`/`_line_stats`, the change spec, and ran targeted probes. All line numbers are the
post-fix `.grok-stack/adaptive_grok/architecture_diff.py` unless prefixed with `cfc4a57:`.

## Findings

1. **Important — the new stream bypasses the module's only bounded process runner.**
   Every other git call goes through `_git` → `_run_capped` (74-157), which enforces a monotonic deadline
   (118-141), a `stdout_limit`/`stderr_limit` pair (`_git` passes `stderr_limit=65_536`, 221-222),
   `start_new_session=True` (93) and `_stop_process` = `os.killpg(SIGKILL)` + `wait()` (66-71).
   `_profile_git_blob` instead hand-rolls a `subprocess.Popen` (564) that:
   - blocks in `process.stdout.read(BLOB_STREAM_CHUNK_BYTES)` (576) with **no wall-clock bound** — the only
     timeout is `process.wait(timeout=_GIT_TIMEOUT_SECONDS)` (583), reached *after* stdout hits EOF, so a
     `git cat-file` that stalls mid-stream (promisor/partial clone, network ODB, FUSE) wedges
     `grok_verify --mode pr` indefinitely where every pre-existing call fails in 30 s;
   - reads stderr without a cap: `error = process.stderr.read()` (582) — unbounded memory and unbounded
     error string, exactly the guard `_run_capped` exists to provide;
   - on the error path does `process.kill()` (585) — direct child only, no process group, and no `wait()`,
     so a grandchild holding the pipe is not signalled and the child is left for `Popen.__del__` to reap;
   - has no `process.poll() is None → _stop_process` finally guard (compare 153-154), so a `BaseException`
     (Ctrl-C during a 10 MB stream) leaves git running.
   Blast radius is limited to objects above `MAX_ANALYZED_FILE_BYTES` — i.e. precisely the release-artifact
   PRs this change unblocks. Cannot produce a wrong verdict (fails closed or hangs), so not Critical.
   Fix: reuse `_run_capped` with a byte-consuming wrapper, or add a monotonic deadline around the read loop,
   cap stderr, and use `_stop_process(process)` instead of `process.kill()`.

2. **Minor — `assert process.stdout is not None` (573) instead of the module's own convention.**
   `_run_capped` raises `ArchitectureError("bounded process pipes are unavailable")` for the same condition
   (98-99). Under `python -O` the assert disappears and the failure mode becomes `AttributeError` on `None`.
   No gate catches it: `bandit.yaml` skips `B101` (`- B101   # assert_used`).

3. **Minor — `shell=False` is only implicit at 564.** The behaviour is compliant (`Popen` defaults to
   `shell=False`, argv list, `env=_git_environment()`, resolved `cwd=root` — `diff_architecture` resolves at
   1039, so `safe.directory` matches), but line 11 states the invariant in prose and 92 spells the keyword
   out; the new site should match so the invariant stays greppable.

4. **Minor — the incomplete-stream message loses the number it just computed.**
   `f"Git blob stream incomplete for {path}: {message or total != size}"` (594) parses as
   `message or (total != size)`, so with empty stderr it prints `True` and never reports `total` vs `size`.
   No content leak (the object goes to stdout, only stderr is interpolated), but the operator cannot tell a
   nonzero exit from a short read.

5. **Minor — per-path process/syscall inflation on the common (≤ limit) case.**
   `_profile_git_blob` now spawns an extra single-path `ls-tree -l` (503-517) and *then* calls `_git_blob` →
   `_git_blobs`, which itself spawns `ls-tree -lr` (887-893) plus `cat-file --batch` (921-929): 3 spawns per
   side where the pre-fix loop used 2. On the worktree side `_profile_worktree_blob` walks the whole
   component chain (456) and then `_worktree_blob` re-walks it from scratch (465 → 342-354). With
   `MAX_CHANGED_PATHS = 20_000` (32) that is ~40k extra spawns worst case. The metadata is already available
   inside `_git_blobs` (913-915 parses id+size) — returning it would remove the duplicate call.

6. **Minor — one new race-only hard error.** A file that disappears between the outer `fstat` and the inner
   re-walk now raises `worktree file vanished during analysis` (467) instead of returning `None` and being
   reported as a deleted artifact. Fail-closed and acceptable, but it is a semantic delta versus `cfc4a57`
   under a moving tree, so INV-001's "byte-identical at or below the limit" is true only for stable input.

7. **Minor — the tests do not cover the parts of the new code that could actually lie.**
   `test_oversized_tracked_binary_is_streamed_and_still_verified` uses `blob = b"\0" + b"z" * (limit + 8)` —
   the NUL sits in the *first* chunk, so "NUL only past the first 64 KiB" is untested; the refusal branches
   at 591-595 (bad exit / short stream) and 498-499 (worktree truncation) are not exercised. I probed the
   late-NUL case and it is handled correctly (see Evidence C), so this is coverage, not a defect.

8. **Minor — package prose overstates one claim.** `brief.md` ("Constraints → Security: **no new subprocess
   surface**") is contradicted in the strict sense: this is the second `subprocess.Popen` call site in the
   module (grep found Popen only at 89 before the fix, now also at 564) and it is *less* bounded than the
   first. `change-spec.yaml` INV-002 as written ("argument vector and shell=False, with the same restricted
   environment") **is** satisfied. Every other measured claim checked out (Evidence A/B/D).

## Judgements

1. **Security properties of `_worktree_blob` preserved.** `_profile_worktree_blob` (436-499) repeats the
   identical gate: path-component rejection of `""`/`.`/`..`, per-component `O_NOFOLLOW` + `O_DIRECTORY`
   walk with `O_NONBLOCK` only on the leaf, `O_DIRECTORY`/`O_NOFOLLOW`/`O_NONBLOCK` non-zero and
   `os.open in os.supports_dir_fd` capability check (441-455, byte-for-byte the 341-349 block), the
   `stat.S_ISREG` requirement, `FileNotFoundError → None`, and the `(st_dev, st_ino, st_size,
   st_mtime_ns)` before/after comparison (496-497). The shared walk `_open_worktree_file` (392-423) is a
   pure extraction of `cfc4a57:349-365` with the same flags and ordering, plus a new close-on-failure
   handler. **No descriptor leak on any path**: `_open_worktree_file` closes `directory` before re-raising
   (415-419), so a raising walk hands the caller nothing; in `_worktree_blob` the assignment is inside the
   `try` and both locals stay `-1`, which the existing `if descriptor >= 0 / if directory >= 0` finally
   (376-380) already handles; in `_profile_worktree_blob` the unconditional `finally` (491-493) is reached
   on every exit including the small-file early `return` (468-473), and `ArchitectureError` subclasses
   `ValueError`, not `OSError`, so the `except OSError` at 489 cannot swallow it (verified: `class
   ArchitectureError(ValueError)`, `.grok-stack/adaptive_grok/architecture.py:72`). For files at or below
   the limit `_worktree_blob` is delegated to unchanged, so content, digest and the limit/truncation
   checks are literally the pre-fix code (probe C row 5: `size`, `digest`, `content`, `binary` all equal).

2. **Streamed digest is trustworthy.** Worktree: `total` is accumulated from every `os.read` chunk and
   `if total != before.st_size: raise "... truncated ..."` (498-499) rejects a short read; mid-read
   mutation is caught by the re-`fstat` tuple check (496-497). Git: the streamed length is verified
   against the `ls-tree -l` size via `if returncode or total != size` (591), the exit status **is** checked
   and stderr **is** captured and included (582-583, 592-594). `_git_blob_entry` refuses a
   mode/type/length/path mismatch, requires `kind == b"blob"` and `mode in {100644,100755}`, validates the
   object id with `_EXACT_SHA.fullmatch` and the size with `.isdigit()` (527-539), so a non-blob or a
   garbage size cannot reach the streamer. The NUL sniff is sound across chunk boundaries — a NUL is one
   byte, cannot straddle a 64 KiB split, and `if not binary and b"\0" in chunk` is evaluated for *every*
   chunk (580-581, 484-485); probe C row 6 confirms a file whose only NUL is at offset 10,000,001 reports
   `binary=True, content=None`. `binary=False` + `content=None` cannot reach `_line_stats`: the
   `oversized_text` refusal (1094-1099) is evaluated before the `_line_stats` call (1103) on every path, and
   `_line_stats` retains its own guard (`810-813`, raises `line-stat byte limit exceeded` above the limit),
   so the two guards are independent. `test_oversized_text_file_still_refuses_analysis` asserts the refusal
   in both diff modes and passes.

3. **Popen failure modes.** See findings 1-3. Shell is not used, argv only, `object_id` is `_EXACT_SHA`
   validated *before* it is placed in the vector (536, 565), env is the same allow-listed 9-key
   `_git_environment()` as every other call (159-171, 567), `stdin=DEVNULL`, streams closed in `finally`
   (587-590). Error text carries stderr only, never object bytes.

4. **No silent drop.** The oversized file still yields a `ChangedArtifact` (1108-1118) and its real size
   still enters the aggregate via `artifact_bytes += (base_profile.size ...) + (head_profile.size ...)`
   (1086-1088), checked against the untouched `MAX_DIFF_ARTIFACT_BYTES = 50_000_000` (36, 1089-1090), so
   making a file large cannot evade the fitness byte budget — it now costs exactly its bytes. The unit test
   asserts the streamed artifact carries `head_size == len(blob)`.

5. **Behavioural equivalence.** `status` is now keyed on profile presence (1092-1093) with the same
   three-way truth table including both-`None` → `modified`; `head_side` hoisting (1078) is equivalent
   because the pre-fix conditional expression only evaluated `_required_head` in the non-worktree branch
   and `head` is always a resolved str there (1062-1064). `base_size`/`head_size`/`base_digest`/`head_digest`
   are `len()`/`sha256()` of the same bytes for every ≤limit path (probe C row 5). The only wording change
   is the new `text file exceeds analysis limit: {path}` (1099) replacing
   `worktree file exceeds analysis limit` (360, still live for direct `read_diff_file` callers) and
   `Git blob exceeds analysis limit` (913, still live via `_git_blobs`); the substring
   `exceeds analysis limit` is kept, and a repo-wide grep found no consumer that asserts the old full
   strings — the three surviving test assertions (2579, 2664, 2666) all match the retained substring.
   `read_diff_file` (867-875) and `read_diff_files` (952-973) still route to `_git_blob`/`_worktree_blob`
   and keep raising on an oversized path, so AC-003 holds.

6. **Scope discipline.** `git diff --name-only cfc4a57..d13bf59` lists exactly the module,
   `tests/test_architecture_fitness.py`, 11 files under the new change package, and `decisions.md` +
   `mistakes.md` — nothing else. The constant diff is a single added line:
   `9:+BLOB_STREAM_CHUNK_BYTES = 64 * 1024`; `MAX_ANALYZED_FILE_BYTES`, `MAX_GIT_OUTPUT_BYTES`,
   `MAX_CHANGED_PATHS`, `MAX_BATCH_INPUT_BYTES`, `MAX_DIFF_ARTIFACT_BYTES`, `MAX_LINE_STAT_LINES` are
   byte-identical between `cfc4a57:30-38` and 30-38 (FORBID-001 respected).

7. **Prose accuracy.** Checked and true: 103 tests OK (E), ruff clean on both changed files (F), the ZIP is
   10,940,676 bytes with `sha256 770f1db5725e666b…` (G), streamed digest equals the buffered digest in both
   modes (C), `Risk: medium` in `brief.md` against `tier: yellow` is this repository's existing convention
   (18 briefs use "medium", 31 specs use "yellow") — not a defect. Overstated: finding 8
   (`no new subprocess surface`) and, by extension, the commit message's "the O_NOFOLLOW component walk is
   shared with the existing reader" is accurate but omits that sharing costs a second full walk per ≤limit
   worktree file (finding 5).

## Evidence

A. `git show --stat d13bf59` / `git diff --name-only cfc4a57..d13bf59` → 15 files, module + test + package +
   two shared logs only.
B. `git diff cfc4a57..d13bf59 -- .grok-stack/adaptive_grok/architecture_diff.py | grep '^[+-]MAX\|^[+-][A-Z_]* ='`
   → only `+BLOB_STREAM_CHUNK_BYTES = 64 * 1024`.
C. Probe (module functions called directly against the real tree and a temp dir):
   ```
   wt size 10940676 match True
   wt digest match buffered: True binary True content is None: True
   git profile ok: True True True True
   git profile missing path -> None
   small file identical: True True True True
   late-NUL binary: True content: None size ok: True
   oversized text profile: binary= False content is None: True (diff loop must refuse)
   ```
   Rows: `_profile_worktree_blob` on `packages/adaptive-grok-build-pro-v2.0.17.zip` (streamed digest ==
   buffered sha256, `content=None`); `_profile_git_blob` at HEAD on the same nested path (same digest ⇒
   `-l` without `-r` does resolve nested paths, independently confirmed with
   `git ls-tree -l -z --full-tree HEAD -- architecture/rules.yaml` → one blob record);
   `_profile_git_blob` on an absent path → `None` (so `added` still works);
   `_profile_worktree_blob("README.md")` vs `_worktree_blob("README.md")` → identical
   size/digest/content/binary (≤limit equivalence); a 10,000,012-byte file whose only NUL is at offset
   10,000,001 → `binary=True` (chunk-crossing sniff sound); a 10,000,001-byte all-`x` file →
   `binary=False, content=None`, which the diff loop must and does refuse.
D. `ls -l packages/adaptive-grok-build-pro-v2.0.17.zip` → `10940676`;
   `sha256sum` → `770f1db5725e666be60c1f879d2768feacb15dd53e194a1f1f48632980f74616`.
E. `python3 -m unittest tests.test_architecture_fitness -q` → `Ran 103 tests in 73.093s` / `OK`
   (includes the two new cases; no pre-existing test was edited).
F. `python3 -m ruff check .grok-stack/adaptive_grok/architecture_diff.py tests/test_architecture_fitness.py`
   → `All checks passed!`
G. `grep -n "class ArchitectureError" -A 6 .grok-stack/adaptive_grok/architecture.py` →
   `class ArchitectureError(ValueError)` — confirms the `except OSError` handlers cannot absorb it.
H. `grep -rn "exceeds analysis limit" --include=*.py --include=*.md --include=*.json .` → old full strings
   survive only inside the module (360/913/918/970) and historical package prose; no consumer breaks.

## Not verified by this review

`scripts/grok_verify.py --mode pr` (parent owns it), the whole repository suite, the external exact-head
App-owned `adaptive-trust-ci/verified@<policy-sha12>` check, and `bandit` as invoked by the verifier
(`bandit.yaml` was read, not executed).
