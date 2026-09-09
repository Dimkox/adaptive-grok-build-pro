# Independent security re-review

## Identity and verdict

- Route: `81850148d1f6`
- Change: `20260829-m2-trust-ci-read-only-workspace-compatibility-818501`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Pre-review worktree fingerprint: `804a90cecef93cc96ddaddf6cedf64a7b0d8edc866d5cee52953b0837d757696`
- Supplied evidence: pinned runner `381/381 PASS`; `grok_verify` preflight PASS
- Prior finding I-1: **ADDRESSED**
- Verdict: **PASS**
- Findings: Critical `0`, Important `0`, Minor `1`

The prior external-secret symlink disclosure and hash-to-stream integrity gap are closed. The implementation excludes symlinks/non-regular inputs, reopens every descendant component descriptor-relative with `O_NOFOLLOW`, binds file identity and digest, and publishes the completed ZIP only after all source checks succeed. One narrow descriptor cleanup defect remains on injected `fstat()` failure; it is Minor for this one-shot packaging CLI and does not reopen the confidentiality/integrity boundary.

## Prior finding closure

### I-1 — External-secret symlink and source replacement: ADDRESSED

- Enumeration canonicalizes the source root, uses `lstat()`, and admits only regular files; a final-component symlink is excluded before hashing (`.grok-stack/adaptive_grok/manifest.py:48-74`).
- Snapshot and stream reads pin a root directory descriptor. Every descendant directory is opened relative to the preceding descriptor with `O_DIRECTORY | O_NOFOLLOW`, and the final file is opened relative to its parent with `O_NOFOLLOW`; the opened object must be regular (`.grok-stack/adaptive_grok/manifest.py:16-18`, `.grok-stack/adaptive_grok/manifest.py:96-137`). A symlink or parent replacement introduced after enumeration therefore fails closed instead of being followed.
- Manifest snapshot records device, inode, full mode, size, mtime and ctime, while hashing the held descriptor and requiring identical metadata before and after (`.grok-stack/adaptive_grok/manifest.py:25-39`, `.grok-stack/adaptive_grok/manifest.py:85-93`, `.grok-stack/adaptive_grok/manifest.py:140-166`).
- Archive streaming reopens through the same no-follow traversal, requires the original identity before reading, hashes exactly the bytes written to the ZIP member, and requires unchanged identity plus the original digest afterward (`.grok-stack/adaptive_grok/manifest.py:182-201`). Replacement before open, mutation during read, or digest drift aborts.
- The archive is built at a sibling temporary path and is moved to the requested output only after every member and the central directory complete. Any pre-publication exception removes the temporary path (`scripts/package_stack.py:19-54`). A local injected stream-failure probe preserved a pre-existing output byte-for-byte and left no temporary artifact.

The exact prior sentinel reproduction now reports:

```text
symlink_member_present= False
outside_bytes_packaged= False
```

The focused external-symlink, post-render replacement, and bounded checksum regressions independently passed: `Ran 3 tests ... OK`. The replacement test also proves that a failed source rebind does not publish `archive_path` (`tests/test_manifest_package.py:209-263`). Thus prior I-1 is closed.

## Minor finding

### M-1 — Descriptor leaks if the first post-open `fstat()` raises

`_open_root()` closes its descriptor only when `fstat()` succeeds and reports a non-directory; an exception from `os.fstat(descriptor)` bypasses the close (`.grok-stack/adaptive_grok/manifest.py:96-105`). Similarly, `_open_regular_at()` closes the final file descriptor for a successful non-regular result, but an exception from its first `fstat()` escapes without closing that descriptor (`.grok-stack/adaptive_grok/manifest.py:118-137`).

A bounded subprocess probe injected that failure after the safe file open and observed `open_regular_fd_delta= 1`. Normal success, open failures, hashing/streaming failures, parent descriptors, and explicitly retained file descriptors are otherwise closed by `finally` blocks (`.grok-stack/adaptive_grok/manifest.py:119-133`, `.grok-stack/adaptive_grok/manifest.py:151-166`, `.grok-stack/adaptive_grok/manifest.py:182-199`).

This is Minor because the current packager is a one-shot CLI and the failure terminates the operation; it does not permit path traversal, symlink following, publication of unchecked bytes, or secret disclosure. Harden by wrapping each initial `fstat()` in a close-on-any-exception block and add an injected-failure fd-count regression.

## Other reviewed boundaries

- **Atomic/failure behavior:** source identity or stream failures occur before `os.replace`; the temporary ZIP is removed and an existing output is preserved. ZIP publication itself is atomic. The checksum is now a bounded `sha256()` read loop rather than whole-archive `read_bytes()` (`scripts/package_stack.py:28-57`, `.grok-stack/adaptive_grok/manifest.py:77-82`). Archive and sidecar paths remain explicitly caller-owned; publication of the ZIP and later sidecar write are not claimed as one multi-file transaction.
- **Exact Git trust:** repository roots remain strictly resolved and supplied once as command-scoped `-c safe.directory=<canonical-root>` with the same canonical `cwd`; the non-repository no-index command receives no repository trust. The environment remains a fresh allowlist with system/global config, replacement objects, locks, prompting, hooks, fsmonitor, attributes, excludes, external diff/textconv, and rename behavior neutralized (`.grok-stack/adaptive_grok/architecture_diff.py:158-226`, `.grok-stack/adaptive_grok/architecture_diff.py:627-650`). No wildcard or persistent Git configuration was introduced.
- **Receipt clone isolation:** its temporary global config still contains only exact `ROOT/.git`, is exposed only to `clone --no-local`, and system/host-global config remains disabled (`tests/test_change_receipts.py:322-351`).
- **Trust plane separation:** the actual fix delta remains empty under `trust-ci/**` and `.github/**`. Deployed policy, holdout, images, keys, database state, branch protection, and external services remain outside repository authority.
- **Current-tree symlinks:** the reviewed repository tree contains no filesystem symlinks. The new regression nevertheless protects future package inputs and committed symlink attempts.

## Evidence boundary

I independently recomputed the supplied fingerprint before and after focused checks and obtained `804a90cecef93cc96ddaddf6cedf64a7b0d8edc866d5cee52953b0837d757696`; `git diff --check` was clean. I did not duplicate the broad pinned runner or `grok_verify`; their `381/381 PASS` and PASS status are supplied evidence, not an external attestation or merge authority. All probes were bounded and used temporary sentinel data only. No application code, credential, external system, deployed Trust CI state, or policy was modified or accessed.
