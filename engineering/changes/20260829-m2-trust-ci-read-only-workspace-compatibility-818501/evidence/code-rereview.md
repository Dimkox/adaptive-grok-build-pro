# Independent code re-review after remediation

## Identity and verdict

- Route: `81850148d1f6`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- Reviewed HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Reviewed worktree fingerprint before this report: `804a90cecef93cc96ddaddf6cedf64a7b0d8edc866d5cee52953b0837d757696`
- Prior review preserved at `evidence/code-review.md`.
- **Verdict: FAIL** — the prior checksum finding is fixed, but two new Important atomic-publication/compatibility defects remain. No Critical findings.

The supplied preflight is `grok_verify` PASS and the pinned runner is 381/381 PASS. Those are local/preflight evidence only; the GitHub App-owned policy-epoch check and external approvals remain merge authority.

## Prior findings

### I1 — Whole-archive checksum allocation: ADDRESSED

`scripts/package_stack.py:55` now calls the bounded `sha256(output)` loop at `.grok-stack/adaptive_grok/manifest.py:77-82`; it no longer calls `output.read_bytes()`. `tests/test_manifest_package.py:248-263` supplies a path whose `read_bytes()` raises and verifies the streamed digest and unchanged sidecar format. The focused regression passed.

### M1 — Stale 377-test package count: ADDRESSED

The active `tasks.md`, `test-plan.md`, and `release.md` now consistently identify the parent-owned full suite as 378 tests. The later supplied pinned run contains 381 tests after remediation coverage, so the durable handoff wording remains historically accurate rather than falsely claiming parent completion.

## Strengths

- Source enumeration rejects symlinks/non-regular entries, and snapshot/stream opens walk from directory descriptors with `O_NOFOLLOW`; member identity includes device, inode, full mode, size, mtime, and ctime, and content is re-hashed before publication (`.grok-stack/adaptive_grok/manifest.py:48-74`, `:85-201`).
- A replacement between snapshot and streaming aborts while the archive is still temporary, and normal exception paths unlink that temporary name (`scripts/package_stack.py:28-54`). Source manifest bytes remain untouched.
- Architecture trust remains exact and command-scoped. The enhanced regression also proves `diff --no-index` receives no repository `safe.directory` entry (`tests/test_architecture_fitness.py:4142-4189`).
- Independent canonical summary output exactly matches the refreshed handoff: architecture `ee458c0a...`, rules `d5156f3d...`, system `da6453d9...`, schema `c702531d...`, inventory `039feea9...`.
- Worktree fitness independently measured exactly 10,228 scoped changed lines, no unknown statistics, and PASS under the finite 10,300 ceiling.
- No `trust-ci/**` or `.github/workflows/**` path changed; package/install focused compatibility tests passed.

## Findings

### Critical

None.

### Important

#### I2 — Closing the secure temporary fd and reopening by name permits a symlink-swap overwrite

**Evidence:** `scripts/package_stack.py:28-34` obtains an exclusive `mkstemp` descriptor and immediately closes it. `ZipFile` then reopens `temporary_output` by pathname at lines 36-41. A focused race probe replaced that name after line 33 with a symlink to a sentinel file; `write_archive` followed the symlink, changed the sentinel prefix to ZIP bytes (`PK\x03\x04`), moved the symlink to the requested output, and returned successfully.

**Rationale:** The close/reopen gap discards the file authority that `mkstemp` established. A process able to mutate the caller-selected output directory (including a same-UID concurrent process or a writable shared directory) can redirect package writes to another file writable by the packaging process. This conflicts with the change's security motivation and the claim of safe atomic temporary construction.

**Required fix:** Keep the exclusive descriptor open and pass an `os.fdopen` file object to `zipfile.ZipFile`; close/flush the same object before `os.replace`. Never reopen the temporary archive by pathname. Add a regression that swaps the pathname after allocation and proves no external target is opened or changed.

#### I3 — Atomic replacement changes the ZIP filesystem mode to `0600`

**Evidence:** `tempfile.mkstemp` creates the temporary file as `0600` at `scripts/package_stack.py:28-33`, and `os.replace` publishes that inode unchanged at line 51. A focused probe under the current `0002` umask produced a normal control file and sidecar at `0664`, but the archive at `0600`. Before this remediation, `ZipFile(output, "w")` created a new destination with normal `0666 & ~umask` semantics and retained the mode of an existing destination.

**Rationale:** Published packages become owner-only and replacing an existing archive silently discards its mode. This is an observable package compatibility regression not covered by ZIP member-mode tests and can prevent downstream group/read-only consumers from reading the artifact.

**Required fix:** Preserve the existing destination mode when replacing an existing regular output and use normal create-mode/umask semantics for a new output, while retaining an exclusive open descriptor throughout construction. Add controlled-umask tests for both absent and pre-existing destinations.

### Minor

#### M2 — `included_files()` no longer accepts a symlinked root path

`included_files` enumerates from `canonical_root` but sorts with `item.relative_to(root)` (`.grok-stack/adaptive_grok/manifest.py:48-74`). With `root` as a directory symlink, the returned canonical child is not lexically below the supplied alias and the function raises raw `ValueError`; a focused probe reproduced this. `snapshot_files` avoids it by passing the canonical root, so packaging is unaffected, but this is a regression in the existing directly imported helper. Sort relative to `canonical_root` consistently (or explicitly reject a root symlink with `ManifestError` if that compatibility break is intended and approved).

#### M3 — Rare `fstat` failures leak newly opened descriptors

After `os.open`, `_open_root` calls `os.fstat` outside a cleanup guard (`.grok-stack/adaptive_grok/manifest.py:96-105`), and `_open_regular_at` does the same at lines 129-137. If either `fstat` raises, the just-opened descriptor is not closed and the raw `OSError` escapes. Wrap descriptor validation so every post-open failure closes the fd and is normalized to `ManifestError`; add failure-injection coverage.

## Commands and evidence

- `git rev-parse HEAD`, `git status --short`, full `git diff HEAD`, surrounding source/tests/package docs, `git diff --check HEAD`, and protected-path scan.
- Independent `tree_fingerprint(root)` -> `804a90cecef93cc96ddaddf6cedf64a7b0d8edc866d5cee52953b0837d757696`, exactly matching the supplied pre-review fingerprint.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_architecture.py summary --json` -> all five frozen digests match.
- Worktree fitness against adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8` -> PASS, 10,228/10,300 scoped lines, zero unknown line stats.
- Seven focused regressions (external symlink, replacement failure, streamed checksum, deterministic archive, packaged installer, exact Git trust, frozen digests) -> 7/7 PASS in 2.138 s.
- Controlled mode probe -> control `0664`, ZIP `0600`, sidecar `0664`.
- Controlled close/reopen swap probe -> swap succeeded, output became a symlink, and the external sentinel began with ZIP bytes.
- Symlink-root helper probe -> raw `ValueError` from `included_files(link)`.

## Residual/cannot-verify items

- I did not rerun the broad 381-test suite or privileged pinned container; those results were supplied by the parent and intentionally not duplicated.
- This report does not authorize push, merge, release, deployment, or substitute for exact-SHA external Trust CI and required human approvals.
