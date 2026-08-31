# Repository exploration: Trust CI read-only root-unittest failure

## Scope and identity

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- Branch: `milestone/m2-executable-architecture`
- HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- The product tracked tree was not modified. The active change package is currently untracked and is the only observed workspace addition.

## Exact root cause

`tests/test_manifest_package.py:67-70`,
`PackageTests.test_packaged_installer_materializes_new_target_without_authority`, calls
`PACKAGE.write_archive(ROOT, archive_path)` where `ROOT` is the checked-out repository
itself. `scripts/package_stack.py:18-20` calls `generate_manifest(root)`. The implementation
in `.grok-stack/adaptive_grok/manifest.py:50-54` writes `root/MANIFEST.sha256`; the packager
then removes it at `scripts/package_stack.py:32-33` after creating the archive.

Trust CI mounts the checkout as `/workspace:ro` and runs the command as UID/GID
`10001:10001` (`trust-ci/src/adaptive_trust_ci/sandbox.py:41-75`). Therefore the test fails
at the manifest write with a read-only-filesystem/permission error. If the source were
writable, `trust-ci` would still reject the behavior: the command runner snapshots the
checkout and `workspace.assert_unchanged()` detects the create/delete mutation.

The Git ownership mismatch is not the root cause in the current executor. The sandbox
preserves the required protection while injecting `GIT_CONFIG safe.directory=/workspace`
(`sandbox.py:89-99`). Do not solve this by making `/workspace` writable, changing ownership,
using `safe.directory=*`, or weakening source-integrity checks.

## Smallest safe fix surface

1. Add a pure manifest renderer in `.grok-stack/adaptive_grok/manifest.py` that computes the
   same deterministic manifest bytes without writing a path.
2. Keep `generate_manifest(root)` backward-compatible for the explicit manifest-generation
   command (`scripts/generate_manifest.py` and doctor/verification callers).
3. Change `scripts/package_stack.py:write_archive` to use the pure renderer and write a
   synthetic `MANIFEST.sha256` archive member from memory. It must never create or delete a
   manifest in the source root; preserve archive ordering, fixed ZIP timestamp, modes,
   digest, and sidecar behavior.
4. Treat the output archive/sidecar as caller-owned external outputs. The CLI's default
   `root/dist` output remains a separate contract issue under a read-only source mount and
   should not be silently solved by weakening the mount.

## Regression coverage

- Replace `test_write_archive_unlinks_root_manifest_but_embeds_it` with assertions that
  `write_archive` leaves source bytes, metadata/fingerprint, and any pre-existing
  `MANIFEST.sha256` unchanged while the ZIP still contains a non-empty manifest member.
- Retain/fix the existing direct `write_archive(ROOT, temporary_archive)` test; it is the
  precise `/workspace:ro` characterization.
- Keep the deterministic archive test and additionally assert the source fingerprint is
  unchanged after two package calls and both ZIP bytes/digests match.
- Add a focused sandbox argv/env regression asserting `--read-only`, `/workspace:ro`, the
  fixed non-root user, and `safe.directory=/workspace` remain present. This guards against
  an unsafe ownership/mount workaround.
- If a portability test for mismatched ownership is needed, make it conditional on the
  test runner being able to create a different-owner fixture; behavior should be validated
  by read-only source invariance rather than relying on privileged `chown`.
