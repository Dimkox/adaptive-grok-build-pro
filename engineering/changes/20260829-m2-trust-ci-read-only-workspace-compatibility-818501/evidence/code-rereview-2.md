# Independent code re-review 2

## Identity, scope, and verdict

- Route: `81850148d1f6`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- Reviewed HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Requested and independently matched pre-review worktree fingerprint: `451c81e02e7e8bcf234e53a5a397c272d30d5309fa78296d84383adb626fa5db`
- Scope: the complete tracked diff from HEAD, the active change package, the four findings in `code-rereview.md`, and surrounding manifest/package/Git code and tests.
- Pinned evidence inspected: `evidence/pinned-runner-final.md`, disposable exact-tree commit `3a973b6a8194e752a9ea8d7137a1d7856f76776d`, 386/386 PASS in 234.638 seconds under the documented read-only/no-network/non-root runner contract.
- **Verdict: FAIL** — all four named prior findings are closed, but two new Important correctness/compatibility findings remain. No Critical findings.

Other route reviewers wrote local evidence during this review, so a later whole-tree fingerprint included those new evidence files. The product diff and HEAD inspected here did not change; coordinator-owned final receipts must bind the eventual unchanged final tree.

## Prior finding verdicts

### I2 — `mkstemp` close/reopen symlink overwrite: ADDRESSED

`scripts/package_stack.py:46-67` now creates a random sibling with `O_EXCL|O_NOFOLLOW`, wraps that same descriptor with `os.fdopen`, and `write_archive` passes the held file object to `ZipFile` at lines 93-109. Content is never reopened through the temporary pathname. The regression at `tests/test_manifest_package.py:304-334` swaps the sibling immediately after allocation and proves the external sentinel is unchanged, no output is published, and the swapped name is cleaned. The focused test passed.

### I3 — Published output mode regression: ADDRESSED

For an absent output, `os.open(..., 0o666)` applies the kernel umask (`scripts/package_stack.py:46-55`). For an existing regular, non-symlink output, its permission bits are captured and applied to the held replacement fd (`:34-43`, `:56-59`). Controlled tests prove `0640` under umask `0027` and preservation of existing `0664` under umask `0077` (`tests/test_manifest_package.py:336-366`). Both focused tests passed.

### M2 — Symlink-root `included_files()` regression: ADDRESSED

Enumeration and sorting now both use `canonical_root` (`.grok-stack/adaptive_grok/manifest.py:48-74`). `tests/test_manifest_package.py:33-46` and an independent probe show `included_files(alias)` returns the canonical regular child without `ValueError`.

### M3 — Post-open `fstat` descriptor leaks: ADDRESSED

Both `_open_root` and `_open_regular_at` close the newly opened descriptor and normalize `fstat` failure to `ManifestError` (`.grok-stack/adaptive_grok/manifest.py:96-110`, `:123-147`). Failure-injection coverage checks `/proc/self/fd` counts for both paths (`tests/test_manifest_package.py:48-68`); the focused test passed.

## Strengths

- Source files are enumerated as regular files only, opened root-relative with no-follow directory/file descriptors, identity-bound across both passes, and digest-bound to the ZIP stream. Failure before publication removes the temporary sibling without touching source authority.
- The prior whole-ZIP allocation remains fixed: `sha256` reads 1 MiB chunks and the explicit `read_bytes()` trap passes (`.grok-stack/adaptive_grok/manifest.py:77-82`, `tests/test_manifest_package.py:287-302`).
- New and pre-existing archive permission tests cover the actual filesystem object, not merely ZIP member metadata.
- Exact repository Git commands still carry exactly one canonical `safe.directory` argument, while temporary `diff --no-index` commands carry none (`.grok-stack/adaptive_grok/architecture_diff.py:173-227`, `tests/test_architecture_fitness.py:4142-4189`).
- Independent fitness evaluation passed with exactly 10,311 governed lines, zero unknown line statistics, and the finite 10,400 ceiling. Canonical summary digests exactly match the frozen handoff: architecture `cfbc609f...`, rules `74e35563...`, system `da6453d9...`, schema `c702531d...`, inventory `039feea9...`.
- No `trust-ci/**` or `.github/workflows/**` path changed.

## Findings

### Critical

None.

### Important

#### I4 — Final name validation is racy and the checksum is not bound to the held archive fd

**Evidence:** `scripts/package_stack.py:118-121` validates the temporary pathname, closes the authoritative file object, validates the name again, and then calls `os.replace` in a separate pathname operation. Lines 126-127 subsequently hash and sidecar the published pathname, not the descriptor that received the ZIP bytes. A focused probe performed the swap immediately after the second successful validation: `write_archive` returned success, the output was a symlink to the external file, and a matching sidecar was written for the external bytes.

**Rationale:** The new code prevents the old arbitrary overwrite during `ZipFile` construction, but it still loses identity binding at the publication/checksum boundary. In a mutable output directory, a substitution in the lstat-to-rename window can make a non-archive object authoritative and make the checksum legitimize unrelated external bytes. The test at `tests/test_manifest_package.py:304-334` swaps only before ZIP construction and does not exercise this final window.

**Required fix:** Derive the digest from the held archive fd before releasing it; retain descriptor authority through publication and verify the published entry against the held device/inode before reporting success. Use a private/held directory-fd staging design or another conditional publication strategy if the output directory is in the stated attacker model. Add a deterministic post-final-validation swap regression and prove that no symlink/non-held inode can return success or supply checksum bytes. Sidecar publication must remain bound to the generated archive digest.

#### I5 — Unconditional POSIX flag lookup breaks existing manifest consumers on non-POSIX hosts

**Evidence:** `.grok-stack/adaptive_grok/manifest.py:17-18` evaluates `os.O_DIRECTORY`, `os.O_NOFOLLOW`, and `os.O_CLOEXEC` at import time. These are POSIX capabilities and are not universally present (notably on Windows). The module is imported by `doctor.py`, `scripts/generate_manifest.py`, and `scripts/verify_manifest.py`, not only by the hardened package path. The repository's existing secure readers deliberately use capability checks and controlled failures instead (`architecture.py:154-165`, `architecture_diff.py:333-348`). No approved package document declares the whole manifest/doctor surface Linux-only; backward compatibility explicitly preserves `generate_manifest(root)`.

**Rationale:** On a previously usable non-POSIX installation, importing doctor/generate/verify now raises raw `AttributeError` before any operation or diagnostic. The Linux pinned suite cannot catch this compatibility regression.

**Required fix:** Resolve descriptor capabilities lazily with `getattr`/`os.supports_dir_fd` and fail the security-sensitive snapshot/package operation with a controlled `ManifestError` when unavailable. Preserve the existing explicit generate/verify behavior on supported legacy platforms, or obtain explicit approval and documentation for a versioned Linux-only break. Add a capability-absence import/behavior regression.

### Minor

#### M4 — `verify_manifest()` still fails for the newly supported symlink-root alias

`included_files(alias)` now returns canonical paths, but `verify_manifest` still calculates keys with `item.relative_to(root)` at `.grok-stack/adaptive_grok/manifest.py:235`. After `generate_manifest(alias)`, an independent probe reproduced raw `ValueError` from `verify_manifest(alias)`. Resolve the root consistently in verification and add an end-to-end generate/verify alias test; the current regression tests only direct enumeration.

#### M5 — Durable architecture data-flow numbering is inconsistent

`engineering/changes/20260829-m2-trust-ci-read-only-workspace-compatibility-818501/architecture.md:24-29` numbers publication as step 5 and the following receipt step as step 4. Renumber it to 6 so the durable flow is unambiguous.

## Commands and evidence

- Read `AGENTS.md`, active route, all routed workflow skills, prior reports, pinned evidence, typed/package documents, full actual diff, and surrounding implementation/tests.
- `git rev-parse HEAD`, `git status --short`, `git diff --stat HEAD`, `git diff --check HEAD`, and protected-path scan.
- Independent pre-review `tree_fingerprint(root)` -> exactly `451c81e02e7e8bcf234e53a5a397c272d30d5309fa78296d84383adb626fa5db`.
- Seven focused closure tests (symlink root, both fstat failures, early temp swap, absent/existing modes, streamed checksum, exact Git trust) -> 7/7 PASS in 0.251 s.
- Independent final-window swap probe -> function returned success, output was a symlink to the external file, and sidecar existed.
- Independent generate/verify symlink-root probe -> enumeration passed; verification raised raw `ValueError`.
- Canonical summary and frozen literals matched exactly.
- Worktree fitness against adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8` -> PASS, 10,311/10,400 lines, zero unknown statistics.

## Evidence boundary

The pinned runner report is local exact-tree evidence for its disposable commit, not an App-owned exact-PR-SHA Check Run or human approval. This review authorizes no push, merge, release, deployment, or other external action.
