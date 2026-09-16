PASS

Independent TEST REVIEW — route `1895e17ff333`, kind `test_review`
Subject: commit `d13bf59` on `fix/architecture-stream-large-binaries` (base `cfc4a57`) in
`/home/pall/grok-projects/adaptive-grok-build-pro-largeblob`.
Reviewer ran read-only inspection plus in-process monkeypatch probes; no tracked file was modified.
`git status --porcelain` was empty while the tests ran and afterwards lists only this report and the
sibling `review-code.md` as untracked.

Verdict: the two new tests genuinely exercise the streamed path and the suite is green. Two coverage
claims in the change spec are not backed by any test (findings 2 and 4); neither invalidates the
shipped tests, both are cheap to close.

---

## 1. Do the new tests actually reach the streamed branch? — Yes (verified, not inferred)

Fixture sizes are derived from the constant, so they sit just past the boundary:
`tests/test_architecture_fitness.py:2629` builds `b"\0" + b"z" * (MAX_ANALYZED_FILE_BYTES + 8)`
= 10,000,008 bytes and `tests/test_architecture_fitness.py:2662` builds `MAX + 1` = 10,000,001
bytes. `MAX_ANALYZED_FILE_BYTES` is still `10_000_000`
(`.grok-stack/adaptive_grok/architecture_diff.py:34`, unchanged by the diff — the diff touches only
the readers and the loop, no constant line).

Branch reached, per assertion:
- Commit mode (`:2633` `diff_architecture(base_sha=base, head_sha=head)`): head side →
  `_profile_git_blob` → `_git_blob_entry` returns `(oid, 10000008)`, `size > MAX` so the buffered
  `_git_blob` call at `architecture_diff.py:~549` is skipped and the `git cat-file blob` pipe loop is
  used (`content=None`); base side → `_git_blob_entry` returns `None` (path absent from `base`) →
  `base_profile is None` → `status="added"`, `base_size=0`, which is exactly what `:2636-2637`
  asserts. `added_lines/deleted_lines is None` (`:2639-2640`) is only reachable via the
  `if any(profile.binary ...)` short-circuit at `architecture_diff.py:1100-1107`, because
  `_line_stats` never sees streamed content.
- Worktree mode (`:2642`): head side → `_profile_worktree_blob` → `before.st_size > MAX` →
  the `os.read(descriptor, BLOB_STREAM_CHUNK_BYTES)` loop; `content=None`.
- Text case (`:2658`): both modes hit `oversized_text` → `ArchitectureError("text file exceeds
  analysis limit: ...")` at `architecture_diff.py:1099`.

Could they pass without the fix? No for the binary test. Pre-fix commit mode raised
`"Git blob exceeds analysis limit"` from `_git_blobs` (`architecture_diff.py:913`, reached through
`_git_blob` at `:266`) and pre-fix worktree mode raised `"worktree file exceeds analysis limit"`
(`architecture_diff.py:360` inside `_worktree_blob`), so reverting `d13bf59` errors out of
`test_oversized_tracked_binary_is_streamed_and_still_verified` in its first `diff_architecture` call.
The *text* test can pass without the fix (its regex `exceeds analysis limit` matches all three
message sites), so it is a characterization test for AC-002/FORBID-002 rather than proof that
oversized text flows through the stream — acceptable, but it means only one of the two new tests is
a true fix-proof.

NUL position: the fixture carries the NUL at offset 0 only, so the marker is set from the first
64 KiB chunk in both readers. I probed the not-in-the-suite case (in-process, temp repo, same
helper): an oversized blob whose only NUL is the **last** byte (`b"z"*(MAX+7) + b"\0"`, i.e. offset
10,000,007) produced `status="added"`, `base_size=0`, `head_size=10000008`,
`head_digest == sha256(blob)` and `added_lines is None` in **both** commit and worktree mode — the
streaming loop tests every chunk (`if not binary and b"\0" in chunk`), so the implementation is
correct for a late NUL and only the *test* is missing. That asymmetry is finding 3.

## 2. Kill power (mutation reasoning)

| Hypothetical regression | Caught? | Which assertion / why |
|---|---|---|
| (a) streamed digest from a truncated read | **Yes** | `assertEqual(artifact.head_digest, expected)` at `:2638` / `:2645` compares against an independent `hashlib.sha256(blob)` computed in the test (`:2630`), and a short stream also breaks `head_size == len(blob)`. Inside the module, `total != size` (`architecture_diff.py:~580`) and `total != before.st_size` (`:498`) raise `"Git blob stream incomplete"` / `"worktree file was truncated during analysis"`; those two raises are *not* directly test-covered, but the digest/size assertions make the outcome impossible to pass silently. |
| (b) binary marker sniffed only from the first 64 KiB | **No** | The fixture NUL is at offset 0. Consequence of such a regression: an oversized file whose only NUL is later would be classified non-binary → `oversized_text` → hard `"text file exceeds analysis limit"`, i.e. the exact issue-#80 false red returns for that class of file. My probe shows current code handles it, so this is a missing regression guard, not a live defect. Also untested: `b"z"*...`-style marker logic inverted to `binary=True` unconditionally — that **is** caught, by `test_oversized_text_file_still_refuses_analysis` (no raise → failure). |
| (c) oversized files silently dropped from `artifacts` | **Yes (as an error)** | `next(item for item in ... if item.path == "packages/huge.bin")` at `:2634`, `:2643`, `:2653` raises `StopIteration` → unittest counts it as an error, so the test fails; note it fails *loudly but unhelpfully* (no message naming the dropped path). Not a vacuous pass. |
| (d) `MAX_ANALYZED_FILE_BYTES` raised to 20 MB (the forbidden shortcut, FORBID-001) | **No — measured** | I re-ran the two new tests with `DIFF.MAX_ANALYZED_FILE_BYTES = 20_000_000` patched in-process: `Ran 2 tests ... OK`, and then the **whole module**: `FULL MODULE with MAX=20MB: ran=103 errors=0 failures=0`. Every limit fixture in the file is expressed as `DIFF.MAX_ANALYZED_FILE_BYTES + N` (`:2571`, `:2629`, `:2651`, `:2662`, `:5048`), and a grep of `tests/` for `MAX_ANALYZED_FILE_BYTES`, `10_000_000` and `10000000` found no assertion pinning the numeric bound (the only `10_000_000` hits are `tests/test_governance_fitness.py:210` schema `max_changed_bytes` and the frozen fixture schema, unrelated). So the change spec's FORBID-001 lists `"test": "tests/test_architecture_fitness.py"` as its evidence, and that evidence does not exist. Finding 2. |
| (e) a file mutated mid-stream passes unverified | **Partly** | The readers re-check `(st_dev, st_ino, st_size, st_mtime_ns)` after hashing (`architecture_diff.py:494-497`, mirroring the pre-existing `:382-386`) and raise `"worktree file changed during analysis"`. No test in the module contains the strings `changed during analysis` or `truncated during analysis`, and `test_oversized_text_file...`/`tampered` cases mutate **before** the call, not during it — so AC-004's "a file whose dev/ino/size/mtime change during streaming still raises" is currently unproven by tests. It is also, strictly, a size-preserving + mtime-restoring in-place rewrite that defeats the check; that residual is inherent to the design and pre-existing, not introduced here. Finding 4. |

## 3. Determinism and cost — fine, no environment coupling

Measured on this host:
- The two new tests alone: `Ran 2 tests in 1.344s` (`real 0m1.525s`).
- Whole module: `Ran 103 tests in 72.210s` → the two additions are ≈1.9 % of module wall-clock.
- `tests/test_architecture_model tests/test_change_spec`: `Ran 97 tests in 1.925s`.
- Free disk on `/` (where `tempfile` lives): `466G 176G 271G 40%` — unchanged by the run.

Disk footprint per new test: three ~10 MB working files (10,000,008 + 10,000,009 tampered, plus
10,000,001 text). Because the payloads are single-byte runs, git's loose objects compress to
negligible size, so the temp repos stay small and `GitArchitectureRepo.__init__` registers
`testcase.addCleanup(self._temp.cleanup)` (`tests/test_architecture_fitness.py:41-43`), so nothing
is retained. Caveat worth recording: the compressible fixtures make the measured cost unrepresentative
of the real trigger (the incompressible 10,940,676-byte release ZIP must be re-zlibbed by
`git add -A`), so a future contributor who enlarges these fixtures with random bytes could push the
cost up several-fold. That is a note, not a defect.

Determinism: the fixtures build their own temp repo and never read this repository's
`packages/*.zip`; the only parent-tree input is the two JSON schemas copied from `ROOT`
(`tests/test_architecture_fitness.py:48-50`), which is pre-existing for all 103 tests. So the tests
do not become environment-dependent on whether a >10 MB artifact happens to be tracked. Both new
tests passed twice in this review (module run and standalone run) with identical output.

## 4. Assertion quality

- Good: the digest is compared against a test-local `hashlib.sha256(blob)` (`:2630`, `:2638`,
  `:2645`), so it cannot succeed "for the wrong reason" (e.g. a fixed stand-in hash). The tampered
  case at `:2651-2655` rewrites the file with the **same length** and different bytes (`y` vs `z`),
  so `assertNotEqual(tampered_artifact.head_digest, expected)` (`:2656`) can only fail-pass if the
  digest ignored content — that assertion is meaningful, not merely unequal-by-size.
- Weakness: the worktree-mode and tampered blocks assert only `head_size`/`head_digest`. They do not
  re-assert `status`, `base_size`, `added_lines`/`deleted_lines` symmetry as the commit block does,
  so a worktree-mode regression that flipped `status` to `"modified"` or produced
  `deleted_lines=0` would not be caught by this test.
- Gap (no `modified`/`deleted` coverage of an oversized binary): I probed both in-process and the
  **implementation is correct** — `modified` between two >limit blobs gave
  `status="modified"`, `base_size=10000004`, `head_size=10000004`, `added_lines=None`,
  `deleted_lines=None`, and both `base_digest`/`head_digest` equal the buffered SHA-256 of the
  respective blobs; deleting the file in the worktree gave `status="deleted"`, `base_size=10000004`,
  `head_size=0`, `head_digest=None`, `base_digest=sha256(committed)` — i.e. the *base* side of the
  diff also streams correctly through `_git_blob_entry`. Nothing in the committed suite exercises
  either shape, and every assertion in the new test is for an *added* artifact. Finding 5.
- `next(...)` over a possibly-empty generator: fails loudly as an error rather than vacuously
  passing, but see (c) above — an explicit `self.assertIn(path, paths)` or a helper that raises
  `AssertionError` would name the defect. Minor.
- `assertEqual(artifact.status, "added")` is a string literal; there is no enum to drift. Fine.

## 5. Regression safety net for the `_open_worktree_file` extraction

- Missing worktree file → `None`: still covered, by the pre-existing
  `test_exact_and_worktree_diffs_fail_when_adoption_marker_is_removed`
  (`tests/test_architecture_fitness.py:154`), which is why the initial break of that path was
  detected; it passes in the 103-test run. `_profile_worktree_blob` handles
  `except FileNotFoundError: return None` (`architecture_diff.py:455-456`) and the probe in §4
  confirms the same shape for a >limit base side.
- Not-a-regular-file / symlink: I observed a tracked **symlink** in the worktree under streaming —
  `_open_worktree_file`'s final `os.open(... O_NOFOLLOW)` (traceback `architecture_diff.py:413`)
  raised `OSError: [Errno 40] Too many levels of symbolic links`, converted at
  `architecture_diff.py:459` to `ArchitectureError: worktree file read failed: link.bin: ...`. The
  link is never followed, which is the security-relevant outcome, and the behaviour is unchanged by
  the extraction (same code, moved). But: (i) no committed test drives a symlink, FIFO, or a
  symlinked **ancestor directory** through `_profile_worktree_blob` — the existing symlink tests
  (`:2569`/`:2577`, `read_diff_files`) exercise the Git batch reader, not the worktree reader;
  (ii) the message is `worktree file read failed`, not `worktree path is not a regular file`
  (`:371` / `:461`), which is only reached for a regular-file check *after* a successful open (e.g. a
  device node). Naming that pair (FIFO under `O_NONBLOCK`, symlinked ancestor) as the missing cases;
  I did not run them, so I make no claim about their messages.
- fd hygiene in the extraction: `_open_worktree_file` closes `directory` on `OSError` and re-raises
  (diff-verified) and `_profile_worktree_blob`'s `finally` closes both descriptors, so no leak is
  introduced on the failure paths I read.
- Double read on the small path: `_profile_worktree_blob` delegates to `_worktree_blob(root, path)`
  for `st_size <= MAX`, so a small changed file is walked/opened twice per diff. That keeps existing
  `patch.object(DIFF, "_worktree_blob")` tests meaningful (e.g. `:2616-2622`) — good for
  compatibility — at the cost of one extra fd walk per changed path; harmless at
  `MAX_CHANGED_PATHS = 20_000`. Recorded as Minor.
- Equivalence for ≤limit content (INV-001) holds on the line-count branch: `_line_stats` returns
  `(None, None)` iff `b"\0" in before or b"\0" in after` (`architecture_diff.py:811-816`), which is
  exactly the new `any(profile.binary ...)` test, and the non-UTF-8 `UnicodeDecodeError` branch is
  preserved because small files keep `content`.
- Unreachable-by-test defensive raises: `"Git blob vanished during analysis"` and
  `"worktree file vanished during analysis"` cannot be reached from any committed test (they need a
  race after the metadata probe). Acceptable as defense-in-depth; note that they change the previous
  silent-`None`→`"deleted"` outcome for an object that reads as missing, which no test documents as
  intended either way.

## 6. Commands I relied on (exact tails)

```
$ python3 -m unittest tests.test_architecture_fitness -q
----------------------------------------------------------------------
Ran 103 tests in 72.210s

OK
```

```
$ python3 -m unittest tests.test_architecture_model tests.test_change_spec -q
----------------------------------------------------------------------
Ran 97 tests in 1.925s

OK
```

```
$ python3 -m ruff check .grok-stack/adaptive_grok/architecture_diff.py tests/test_architecture_fitness.py
All checks passed!
```

Supporting probes (in-process, temp repos, no file modified):
```
$ python3 -m unittest -q <two new tests>            -> Ran 2 tests in 1.344s / OK
$ ... same two tests with MAX_ANALYZED_FILE_BYTES=20_000_000
                                                    -> Ran 2 tests in 1.961s / OK  (errors=0 failures=0)
$ full module with MAX_ANALYZED_FILE_BYTES=20_000_000
                                                    -> ran=103 errors=0 failures=0
$ late-NUL / modified-oversized / deleted-oversized probes
                                                    -> Ran 3 tests, FAILED (errors=1): the only error was
                                                       my intentional symlink case, reported in §5.
$ git status --porcelain                            -> (empty)
```
Not run (parent owns them): `scripts/grok_verify.py --mode pr`, the full repository suite.

## 7. Findings

1. **Minor** — `test_oversized_text_file_still_refuses_analysis` is a characterization test, not a
   fix-proof test: its regex matches the pre-fix `"Git blob exceeds analysis limit"`
   (`architecture_diff.py:913`) and `"worktree file exceeds analysis limit"` (`:360`) as well as the
   new `:1099` site. Tightening it to `assertRaisesRegex(..., "text file exceeds analysis limit")`
   in commit mode would make it prove the streamed-and-refused route.
2. **Important** — FORBID-001's declared test evidence does not exist: raising
   `MAX_ANALYZED_FILE_BYTES` (measured at 20 MB) leaves all 103 architecture-fitness tests green.
   Add `self.assertEqual(DIFF.MAX_ANALYZED_FILE_BYTES, 10_000_000)` (plus the other three constants
   named in AC-002) to one cheap test so the forbidden shortcut becomes a red.
3. **Important** — the binary marker is only proven for a NUL at offset 0. One fixture
   (`b"z" * (MAX + 7) + b"\0"`, no extra cost) would pin the per-chunk scan against a
   first-chunk-only sniff. My probe confirms the current code already passes it.
4. **Important** — AC-004's mid-stream mutation guard
   (`architecture_diff.py:494-499`, `"worktree file changed during analysis"` /
   `"... truncated during analysis"`) has no test anywhere; a `patch.object` around `os.read` that
   rewrites the file after the first chunk (or a `size` shrink) would close it.
5. **Minor** — no coverage for an oversized binary that is *modified* or *deleted* (only *added*),
   and no `base_size`/`deleted_lines` symmetry assertions in the worktree blocks. My probes show both
   shapes already behave correctly, so this is regression-guard debt, not a defect.
6. **Minor** — no worktree-side non-regular-file coverage after the `_open_worktree_file` extraction
   (symlink observed safe-but-differently-messaged; FIFO and symlinked-ancestor unnamed); plus the
   double fd walk on the small path described in §5.

Residual risk: the streamed path's guarantees rest on the size/mtime re-check and on
`total == ls-tree/fstat size`, neither of which a committed test drives directly; and the suite
cannot notice if someone later widens a memory constant. One follow-up test I would ask for, if only
one is taken: the constant-pinning assertion of finding 2, because it is the only guard that makes
FORBID-001 enforceable and costs one line.
