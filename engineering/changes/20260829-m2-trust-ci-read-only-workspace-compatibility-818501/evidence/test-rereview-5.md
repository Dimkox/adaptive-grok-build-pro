# Independent test re-review 5

## Verdict

**PASS** — zero Critical, zero Important, and one Minor finding. Remediation-5 closes the restrictive-umask, created-parent cleanup, and leaf-owner test gaps. The prior ancestor, sidecar, source-integrity, compatibility, Git-isolation, budget, and digest regressions remain meaningful and green.

## Exact reviewed identity

- Route: `81850148d1f6`
- Git HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Supplied frozen implementation fingerprint: `55d50a669c5540c10b29f463cb6566737ad74dfcb121cdf77cf22382faf58a14`
- Independently calculated fingerprint before this report: exact match, `55d50a669c5540c10b29f463cb6566737ad74dfcb121cdf77cf22382faf58a14`.
- Actual tracked diff: 11 files, 1,450 insertions and 37 deletions. `git diff --check HEAD` passed; no changed path exists under `trust-ci/**` or `.github/**`.
- The remediation-3 pinned result remains correctly classified as historical. A fresh remediation-5 pinned run is still pending and is not claimed by this report.

## Findings by severity

### Critical

None.

### Important

None.

### Minor

#### M1 — Two test-plan links and one architecture headroom literal remain stale

The P0 matrix still names removed tests `test_archive_rejects_output_parent_not_owned_by_effective_uid` and `test_missing_default_output_parent_is_private_under_common_umasks` (`test-plan.md:18-19`) instead of the current leaf-only and restrictive-umask regressions. `architecture.md:65` still says 78 lines of headroom, while the active typed spec, brief, rules, requirements, live fitness, and arithmetic establish 10,739/10,820 and 81 lines. These are explanatory-document defects only; the executable tests, typed values, canonical digests, and fitness result are current.

## Re-review 4 closure

### Effective-UID leaf-owner oracle: ADDRESSED

`test_open_output_directory_rejects_foreign_leaf_owner_and_closes_fd` leaves the real effective UID and ancestor metadata intact and changes only the `fstat` metadata returned for the already-opened output-directory descriptor. It requires the exact leaf-owner error, no output entries, and restoration of the `/proc/self/fd` count. The test therefore reaches `metadata.st_uid != effective_uid` rather than satisfying `assertRaises` at ancestor validation.

An independent in-memory mutation removed only the production leaf-owner comparison and reran this exact committed test. The mutant produced no `PackageError`, so the test failed with `AssertionError: PackageError not raised`; the test's `finally` branch still closed the unexpectedly returned descriptor. This directly establishes that the regression kills removal of the production predicate and checks the rejection-path descriptor close.

## Remediation-5 coverage assessment

### Restrictive umasks and exact modes: ADDRESSED

The default-output matrix now covers `0002`, `0022`, `0700`, and `0777`, requires successful publication, and checks the created parent is exactly `0700`. The nested regression uses two absent components under `0777`, requires both to be exactly `0700`, and requires archive plus sidecar publication. Together these cases prevent a repair that fixes only ordinary masks, only the final component, or only directory creation without usable publication.

The implementation creates each component relative to the held parent descriptor, binds the new name no-follow, compares named and held device/inode, applies exact `0700`, reopens it securely, applies `fchmod(0700)`, revalidates owner/identity/mode, and advances through held descriptors. It does not chmod a pre-existing directory or use a process-global umask window.

### Created-parent cleanup: ADDRESSED

The cleanup regression creates two missing components under `0777`, injects a later `_open_output_directory` failure with an exact error oracle, and requires the entire newly created outer subtree to be absent. The injected error can only occur after `_ensure_output_parent` has completed, so this is not a false pass caused by failure before creation. Production retains the list of operation-created components, closes its creation descriptors in `finally`, and removes only those components in reverse order on later failure while preserving the primary exception.

## Prior regression preservation

- Ancestor authority tests still pair a real writable non-sticky rejection with successful root-owned sticky `/tmp` operation. The relocation injection checks both the replacement requested path and relocated held directory are empty.
- Sidecar hardlink, FIFO, symlink, directory, normal-mode, post-validation swap, and cleanup cases retain exact external-sentinel, inode/type, timeout, payload, publication, and no-temp assertions. The close-error test preserves the primary failure, records the close note, and proves unlink still occurs.
- New/existing archive mode behavior, deterministic ZIP bytes, bounded checksum streaming, source replacement and external symlink exclusion, source-manifest invariance, symlink-root legacy helpers, lazy capability failure, and post-open descriptor cleanup all remain in the passing 38-test module.
- Exact command-scoped `safe.directory`, no-index isolation, clone `--no-local` configuration lifecycle, architecture evidence determinism, route-base binding, and frozen canonical digest checks remained green in the selected compatibility run.

## Independent checks

- `python3 -m unittest -v tests.test_manifest_package` — **38/38 PASS** in 2.513 s.
- Exact different-owner Git trust, deterministic architecture evidence, pre-adoption comparison binding, separate route-base staleness binding, and frozen handoff digest — **5/5 PASS** in 29.127 s.
- Leaf-owner predicate-removal mutation — expected RED: **1 failure, 0 errors**; exact test failed because `PackageError` was no longer raised.
- Worktree fitness against adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8` — overall PASS, code-budget PASS, exactly 10,739 governed changed lines, zero unknown line statistics, finite limit 10,820, headroom 81.
- Canonical summary: architecture digest `d2f31484721c02d7ae0dcd2faa8519a6d20cb23da10de7378ed02fd1a293061b`; rules digest `2d42ca7373cebd4bf954bcfe1bdb784688df8665d08c4dce2b13de536abee69e`; frozen digest regression PASS.
- Final pre-report fingerprint matched the supplied identity; `git diff --check HEAD` was clean and protected Trust CI/GitHub paths were unchanged.

## Evidence boundary

The supplied independent 39/39 focused result is consistent with the inspected tree; this reviewer independently ran the complete 38-test manifest/package module plus five adjacent compatibility/digest tests and the targeted mutation check. A fresh digest-pinned, non-root, read-only full suite remains a subsequent gate. This local PASS is review evidence only and does not replace the App-owned exact-PR-SHA Trust CI check or required external architecture, governance, and security approvals.
