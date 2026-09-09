# Independent test re-review 4

## Verdict

**FAIL** — zero Critical, one Important, and zero Minor findings. Remediation-4 closes the ancestor-authority, missing-parent, hostile-sidecar, cleanup, and stale-brief findings in implementation, but the committed effective-UID regression is a false-positive oracle and does not bind the final output-parent ownership predicate.

## Exact reviewed identity

- Route: `81850148d1f6`
- Git HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Supplied frozen implementation/evidence fingerprint: `2c217ae3d8401e188657ac916cf3dfc931f4f1c9b90413cc4445ef908a1bcac2`
- Independently calculated fingerprint immediately before this report: exact match, `2c217ae3d8401e188657ac916cf3dfc931f4f1c9b90413cc4445ef908a1bcac2`.
- Actual tracked diff: 11 files, 1,315 insertions and 37 deletions. `git diff --check HEAD` passed; no changed path exists under `trust-ci/**` or `.github/**`.
- The historical remediation-3 pinned result is correctly marked stale. No fresh full-suite result is claimed for this fingerprint; the package deliberately leaves that run pending until independent review.

## Findings by severity

### Critical

None.

### Important

#### I1 — The effective-UID test exits at an ancestor and cannot detect removal of the output-parent owner check

`test_archive_rejects_output_parent_not_owned_by_effective_uid` patches `os.geteuid()` to the real UID plus one while its entire temporary path remains owned by the real UID (`tests/test_manifest_package.py:411-424`). On the actual test path beneath `/tmp`, production raises `PackageError: archive output ancestor grants untrusted rename authority` from `_validate_ancestor_authority()` (`scripts/package_stack.py:63-78`). It never reaches the held output-directory metadata predicate `metadata.st_uid != effective_uid` at `scripts/package_stack.py:151-161`.

This is a material false-green path: deleting only the final output-parent owner check would leave the new regression green because the unrelated ancestor rejection still satisfies its broad `assertRaises(PackageError)`. The prior re-review finding explicitly required a regression for that final effective-UID ownership half of the private-parent predicate, and AC-005 relies on it as a P0 publication boundary.

An independent branch probe that changed only the held directory's `fstat` owner, while leaving the real effective UID and all ancestors valid, reached the intended controlled error: `archive output parent must be owned by the effective user and private`. Current implementation behavior is therefore correct, but it is not protected by the committed test.

Required remediation: inject foreign ownership only into the held output-directory `fstat` result (or test a factored leaf-metadata validator), keep ancestor metadata/effective UID valid, and assert controlled failure before temporary archive, output, or sidecar creation. The oracle should fail if the `metadata.st_uid != effective_uid` condition is removed.

### Minor

None.

## Re-review 3 closure matrix

### I1 — Ancestor relocation/authority: ADDRESSED

The implementation now validates every requested and canonical ancestor owner and rename permission, rejects writable non-sticky ancestors, allows root-owned sticky `/tmp` only for an effective-UID-owned child, and binds the final private directory. The negative unsafe-ancestor test and positive `/tmp` compatibility test are complementary and meaningful. The existing deterministic relocation injection still proves an already-held parent rebinding is detected before publication and leaves both path locations empty. Under the documented same-UID/privileged exception, rejecting untrusted ancestor rename authority closes the former late-relocation success path rather than merely adding another racy pathname check.

### I2 — Common-umask missing parent: ADDRESSED

Missing parents are created explicitly at `0700`, each created component is revalidated, and partial creation is removed on failure. The default-output regression passes under umasks `0002` and `0022` and verifies the missing `dist/` mode plus successful archive publication. An independent two-level missing-parent probe under umask `0002` produced both intermediate directories at `0700`, with archive and sidecar present, confirming the loop behavior beyond the single missing default parent.

### I3 — Hardlink/FIFO/symlink/directory sidecars: ADDRESSED

The hardlink test requires unchanged external bytes and a new sidecar inode; the FIFO test uses a bounded subprocess timeout and requires successful replacement by a regular file; the symlink test requires unchanged target bytes and exact sidecar payload; the directory test requires failure before archive publication. Existing regular-sidecar replacement also checks exact format and mode preservation. These are behavioral oracles, not exception-only smoke tests.

### I4 — Effective-UID ownership regression: NOT ADDRESSED

Production still enforces the predicate, but the committed test does not reach it. See Important I1.

### M1 — Stale brief budget identity: ADDRESSED

The brief, typed spec, requirements, architecture, test plan, rules, and canonical summary consistently describe 10,672 governed lines under the finite 10,750 ceiling with 78 lines of headroom. No former 10,311/10,400 “final” identity remains in the active explanatory brief.

## Sidecar race, cleanup, and compatibility assessment

- The sidecar swap test calls the real validator and swaps only after the third successful temporary-name validation (the sidecar phase). `os.replace` therefore publishes the injected non-held entry, the post-publication held-inode validator removes it, the external target remains unchanged, no sidecar/temp remains, the already verified archive remains, and no success is returned. This meaningfully exercises checksum mismatch cleanup rather than only pre-replace rejection.
- `_cleanup_temporary()` attempts unlink even when close raises. The injected primary binding error plus `CloseFailureFile` regression requires the primary exception to remain authoritative, records the close error as a note, and proves no archive temp/output remains. The same helper is used by archive and sidecar error paths; the sidecar swap regression separately proves its call site performs cleanup.
- New archive mode under umask and existing archive mode preservation remain covered. Existing regular sidecar mode preservation is now covered separately. Symlink-root generate/verify, missing capability import behavior, post-open descriptor cleanup, source replacement/symlink exclusion, bounded archive hashing, deterministic output, exact `safe.directory`, clone isolation, receipt binding, and frozen canonical digests remained green in the bounded checks.

## Independent checks

- `python3 -m unittest -v tests.test_manifest_package` — **36/36 PASS** in 2.483 s.
- Exact different-owner Git trust, deterministic architecture evidence, pre-adoption comparison binding, and separate route-base staleness binding — **4/4 PASS** in 28.512 s.
- `tests.test_structure.StructureTests.test_frozen_m2_handoff_digests_match_canonical_summary` — **1/1 PASS** in 0.142 s.
- Worktree fitness against adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8` — overall PASS and code-budget PASS; independently derived governed measurement `10672`, zero unknown line statistics, finite limit `10750`, headroom 78.
- Canonical summary: architecture digest `ed04f439165ff408911971845c28a7c7199382d379db31debd6642a36723ab54`; rules digest `f3d8253a04d7eaab8955c6c488ab6d74a0be5cade3f6c88966cbb9931604fcbc`.
- Targeted probes: nested missing parents both `0700` with archive/sidecar success; actual patched-eUID test exits at ancestor authority; isolated held-directory foreign-owner metadata reaches the intended leaf ownership failure.
- Final pre-report fingerprint matched the supplied frozen identity; `git diff --check HEAD` was clean and protected Trust CI/GitHub Actions paths were unchanged.

## Evidence boundary

This review intentionally did not treat the stale 391/391 remediation-3 run as current-tree proof and did not duplicate a broad full suite. The fresh pinned read-only run remains pending and, because of Important I1, must follow a corrected leaf-owner regression and a new frozen fingerprint. This local report is not merge authority and does not replace the App-owned exact-PR-SHA Trust CI check or required external architecture, governance, and security approvals.
