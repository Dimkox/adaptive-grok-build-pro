# Independent code re-review 3

## Identity, scope, and verdict

- Route: `81850148d1f6`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- Reviewed HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Frozen implementation/evidence fingerprint independently matched before review: `6d02ed6871caf130d120f9f01097725a4f4da50ffc4dac9f8b39c78c938a2f5c`
- Scope: complete actual diff from HEAD, surrounding source/tests, all historical code findings, remediation-3 package/docs, and fresh pinned evidence.
- Pinned evidence inspected: disposable exact-tree commit `c749343d535fe2d0d02ee6cf770b781e91c827c7`, 391/391 PASS in 227.409 seconds under the documented non-root, read-only, no-network, digest-pinned runner contract.
- **Verdict: FAIL** — I4, I5, M4, and M5 are closed, but two new Important package-output defects remain. No Critical findings.

Local tests/reviews and the disposable pinned run are not merge authority. The exact PR head still requires the App-owned policy-epoch check and required external approvals.

## Prior finding verdicts

### I4 — Final name/checksum lost held-fd identity: ADDRESSED

The ZIP digest is now streamed from the still-held temporary file object before publication (`scripts/package_stack.py:181-187`, `:266-284`). Temporary creation, both name validations, `os.replace`, published-output validation, mismatch cleanup, and sidecar publication are relative to one held private-parent descriptor (`:119-178`, `:190-234`, `:246-293`). The archive fd remains open until post-replace identity validation. The deterministic final-validation swap regression proves no replacement inode can return success, touch the external sentinel, survive as output, or create a sidecar (`tests/test_manifest_package.py:428-460`). Under the newly explicit contract that same-UID/privileged concurrent mutation inside a private parent is trusted/out of scope, this closes the prior finding.

### I5 — Import-time POSIX capability regression: ADDRESSED

Manifest descriptor flags are now resolved lazily in `_descriptor_flags`; absence produces controlled `ManifestError` only when secure snapshotting is requested (`.grok-stack/adaptive_grok/manifest.py:23-31`). Legacy rendering/generation/verification no longer use secure snapshot descriptors unless entries are explicitly requested (`:190-207`, `:232-266`). `tests/test_manifest_package.py:34-63` loads the module with POSIX open flags removed, proves import plus generate/verify still work, and proves snapshotting fails closed. The focused test passed.

### M4 — Symlink-root verification: ADDRESSED

`verify_manifest` resolves one canonical root and keys all enumerated paths relative to it (`.grok-stack/adaptive_grok/manifest.py:238-266`). The end-to-end alias test at `tests/test_manifest_package.py:80-90` passes.

### M5 — Architecture flow numbering: ADDRESSED

The durable data flow is now numbered 1 through 6 without duplication (`engineering/changes/20260829-m2-trust-ci-read-only-workspace-compatibility-818501/architecture.md:22-29`).

## Strengths

- The output parent is canonicalized, opened no-follow once, checked for effective-UID ownership and absence of group/world write bits, then retained as the authority for existing-output inspection, temp allocation, replace, validation, cleanup, and sidecar operations (`scripts/package_stack.py:56-100`, `:237-293`).
- Parent relocation after temp creation is detected against the requested path, while cleanup still reaches the old held directory inode; the focused relocation regression leaves both original/replacement locations clean (`tests/test_manifest_package.py:177-203`).
- Source snapshot/stream identity and digest binding, bounded archive hashing, deterministic members, output-mode preservation, and source-manifest invariance remain intact.
- Missing POSIX capabilities fail lazily and explicitly rather than breaking module import.
- Exact Git trust remains one canonical command-scoped `safe.directory` for repository operations and absent for temporary `diff --no-index`; its focused regression passed.
- Independent canonical summary matches the frozen handoff: architecture `8210395a...`, rules `2a1e3da8...`, system `da6453d9...`, schema `c702531d...`, inventory `039feea9...`.
- Worktree fitness independently passed with exactly 10,502 governed lines, zero unknown line statistics, and the finite 10,600 ceiling. No `trust-ci/**` or `.github/workflows/**` path changed.

## Findings

### Critical

None.

### Important

#### I6 — Sidecar publication follows hardlinks and can block forever on a FIFO

**Evidence:** `_write_sidecar` opens the pre-existing sidecar name directly with `O_TRUNC|O_NOFOLLOW` (`scripts/package_stack.py:216-234`). `O_NOFOLLOW` protects only symlinks; it neither rejects hardlinks nor non-regular inodes. In an effective-UID-owned `0700` output parent, an independent probe created `archive.zip.sha256` as a hardlink to an external sentinel: `write_archive` returned success and replaced the external sentinel bytes with the checksum payload. A second probe used a FIFO sidecar: the child remained blocked in `os.open` after one second, while the archive had already been published.

**Rationale:** A pre-existing filesystem state—not a concurrent same-UID mutation—can redirect an authorized package build into an external write or indefinite hang. The operation can also leave a new archive with an old/invalid sidecar on failure. There is no regression coverage for pre-existing sidecar symlink, hardlink, FIFO, directory, or other non-regular entries.

**Required fix:** Never open an existing sidecar entry for truncation. Build the sidecar through its own exclusive held regular temporary fd in the private parent and publish it with dirfd-relative replacement/identity checks; inspect/reject or safely replace pre-existing symlink, hardlink, and non-regular entries without following or blocking. Preserve documented regular-sidecar mode/format semantics and add explicit symlink, hardlink, FIFO, directory, failure-cleanup, and successful replacement tests.

#### I7 — A missing output parent is created with a mode that the next line may reject

**Evidence:** `write_archive` creates `output.parent` with default `Path.mkdir(parents=True, exist_ok=True)` semantics at `scripts/package_stack.py:245`, then `_open_output_directory` rejects any group/world-writable parent at lines 56-74. Under the common collaborative umask `0002`, an independent probe of a missing output parent created it as `0775` and immediately failed with `PackageError`. The documented default `python3 scripts/package_stack.py` has this behavior whenever `dist/` is absent under that umask. Existing tests use already-private `TemporaryDirectory` parents and do not cover creation of the default/missing parent.

**Rationale:** The new private-parent invariant is reasonable, but the implementation does not establish it for a directory it creates itself. This breaks the advertised default package command and leaves an empty directory behind, despite no unsafe pre-existing parent.

**Required fix:** Create the final missing output parent with an explicit private mode (for example `0700`, still subject to ownership/identity validation) without chmod-mutating a pre-existing directory. Add missing-parent tests under umask `0002` and `0022`, plus the documented default-output path; retain rejection of pre-existing group/world-writable parents.

### Minor

#### M6 — The active brief still publishes the previous budget identity

The authoritative typed spec, requirements, tasks, architecture, decisions, rules, canonical summary, and fitness evidence now use 10,502/10,600 with 98 lines of headroom. `brief.md:29` and `:51` still say 10,311/10,400 with 89 lines. Refresh those explanatory literals so the durable package does not present two “final” budget states.

#### M7 — Cleanup can skip unlinking if file-object close itself raises

The inner exception path calls `temporary.file.close()` and only then unlinks the temp entry (`scripts/package_stack.py:286-289`). A close error would mask the originating failure and skip name cleanup, although the outer directory fd is still closed. Use nested `try/finally` cleanup that attempts both close and dirfd-relative unlink while retaining a useful primary error; add close-failure injection if this helper is expected to be reused in-process.

## Commands and evidence

- Read active route/skills, historical reports, remediation-3 pinned evidence, typed package/docs, full actual diff, and surrounding source/tests.
- `git rev-parse HEAD`, `git status --short`, `git diff --stat HEAD`, `git diff --check HEAD`, protected-path scan, and independent fingerprint calculation.
- Nine focused closure tests (lazy capability handling, alias generate/verify, fstat cleanup, private-parent rejection, relocation cleanup, final swap, absent/existing output modes, exact Git trust) -> 9/9 PASS in 0.246 s.
- Hardlink-sidecar probe -> function returned success and external sentinel was overwritten with checksum bytes.
- FIFO-sidecar bounded probe -> still blocked after one second; archive already published; child terminated by the review harness.
- Missing-parent probe under umask `0002` -> new parent mode `0775`, followed by controlled `PackageError`.
- Canonical summary/frozen literals matched; worktree fitness -> PASS at 10,502/10,600 with no unknown statistics.

## Evidence boundary

This report preserves all historical evidence, modifies no application code, and authorizes no push, merge, release, deployment, or external operation.
