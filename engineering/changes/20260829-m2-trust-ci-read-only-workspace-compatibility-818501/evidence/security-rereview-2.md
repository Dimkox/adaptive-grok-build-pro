# Independent security re-review 2

## Identity and verdict

- Route: `81850148d1f6`
- Change: `20260829-m2-trust-ci-read-only-workspace-compatibility-818501`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Reviewed worktree fingerprint: `451c81e02e7e8bcf234e53a5a397c272d30d5309fa78296d84383adb626fa5db`
- Supplied pinned-runner evidence: `386/386 PASS`
- Verdict: **FAIL**
- Findings: Critical `0`, Important `1`, Minor `0`

The prior external-source symlink, source replacement, whole-archive allocation, output-mode, and `fstat` descriptor-cleanup findings are closed. The new exclusive temporary descriptor is correctly held throughout ZIP creation. However, temporary-name identity is checked and then used by a later pathname-based `os.replace`; a swap in that final check/use window publishes an unrelated inode. This violates the typed prohibition against publishing a mismatched temporary inode and blocks PASS.

## Important finding

### I-1 — Final temporary-name check is still racy with publication

The archive is written through the original exclusive descriptor, and both the held descriptor and current temporary pathname are checked against the recorded device/inode (`scripts/package_stack.py:93-120`). The implementation then calls `os.replace(temporary.path, output)` as a separate pathname lookup (`scripts/package_stack.py:121`). A concurrent rename/symlink swap after the second `_validate_temporary_name()` returns but before `os.replace()` is not bound to the held descriptor. The replacement object is atomically moved to `output`, after which `sha256(output)` follows and accepts that object (`scripts/package_stack.py:126-127`).

A bounded temporary probe deterministically swapped the name immediately after the second successful validation. The function returned success and produced:

```text
validate_calls= 2
output_is_symlink= True
output_points_external= True
external_unchanged= True
returned_digest_is_external= True
```

Thus external target bytes were not overwritten, but the requested package output became a symlink to an unrelated external file and the returned/sidecar digest described that external file rather than the ZIP written through the held descriptor. A regular-file replacement in the same window would likewise be published as the package.

This is Important because the durable contract explicitly states that packaging never publishes a mismatched temporary inode (`change-spec.yaml`, `FORBID-004`) and that temporary-name replacement fails closed. The existing regression swaps immediately after allocation, before either validation, so it covers early detection and safe symlink cleanup but not the final validation-to-rename race (`tests/test_manifest_package.py:304-334`). Pinned `386/386 PASS` therefore does not exercise this window.

Required remediation: make publication identity-bound rather than check-then-use. Either use an OS primitive/workflow that publishes the held inode without a replaceable source-name lookup, or explicitly constrain and enforce the output directory as a trusted non-concurrent boundary and narrow the typed claim. Add a regression that swaps the source name after the final successful validation and requires failure with no mismatched output publication. Do not attempt to solve this with another pre-rename `lstat`, which only moves the race window.

## Closed and confirmed boundaries

- **External source symlinks and traversal:** enumeration uses `lstat` and admits regular files only. Source snapshot and streaming open every descendant directory and final file descriptor-relative with `O_NOFOLLOW`; identity and digest are stable before/after reads (`.grok-stack/adaptive_grok/manifest.py:48-74`, `.grok-stack/adaptive_grok/manifest.py:96-176`, `.grok-stack/adaptive_grok/manifest.py:192-211`). The prior external-secret sentinel remains excluded.
- **Hash-to-stream replacement:** device, inode, mode, size, mtime and ctime are bound during manifest hashing; the streamed bytes are hashed again and must match the same identity and digest before publication (`.grok-stack/adaptive_grok/manifest.py:25-39`, `.grok-stack/adaptive_grok/manifest.py:150-176`, `.grok-stack/adaptive_grok/manifest.py:192-211`). Source replacement fails before output publication.
- **Exclusive temporary descriptor:** temporary allocation uses `O_EXCL | O_NOFOLLOW | O_CLOEXEC`; the descriptor is wrapped directly with `os.fdopen` and passed to `ZipFile`, so ZIP construction never reopens the temporary path (`scripts/package_stack.py:19-20`, `scripts/package_stack.py:46-68`, `scripts/package_stack.py:93-118`). Detected early name swaps close the held descriptor, unlink only the sibling name, and do not follow or modify a symlink target (`scripts/package_stack.py:71-81`, `scripts/package_stack.py:122-125`). This does not close I-1's later race.
- **Output mode semantics:** absent output creation uses `0666` subject to the process umask; replacement preserves the existing regular output's permission bits via `fchmod` on the held temporary descriptor (`scripts/package_stack.py:34-67`). Focused new-output and replacement-mode regressions pass (`tests/test_manifest_package.py:336-366`). Existing symlink/non-regular output is rejected.
- **Descriptor cleanup:** post-open `fstat` errors for root and final source files now close descriptors and normalize to `ManifestError` (`.grok-stack/adaptive_grok/manifest.py:96-110`, `.grok-stack/adaptive_grok/manifest.py:123-147`). The prior Minor fd leak is addressed; its fd-count regression passes (`tests/test_manifest_package.py:48-68`).
- **Read-only source behavior:** archive creation snapshots and streams source descriptors but writes only caller-owned output/temp/sidecar paths. It does not create, replace, or remove source `MANIFEST.sha256`; explicit `generate_manifest()` remains the separate source-writing API (`.grok-stack/adaptive_grok/manifest.py:179-217`, `scripts/package_stack.py:84-128`).
- **Exact Git trust:** repository Git uses one command-scoped `safe.directory=<strictly resolved canonical root>` with the same canonical `cwd` and a fresh sanitized environment; non-repository `diff --no-index` receives no repository trust (`.grok-stack/adaptive_grok/architecture_diff.py:158-227`, `.grok-stack/adaptive_grok/architecture_diff.py:627-650`). No wildcard or persistent configuration is introduced. The receipt clone still uses a temporary exact `ROOT/.git` config only (`tests/test_change_receipts.py:322-351`).
- **Trust-domain separation:** the actual fix delta contains no `trust-ci/**` or `.github/**` changes. Deployed policy, holdout, runner image, keys, state, branch protection, and external services remain outside repository authority.

## Focused evidence and limitations

Six adjacent regressions passed independently: `fstat` cleanup, early temp-name swap, absent-output mode, replacement-output mode, external-source symlink exclusion, and source replacement rejection (`Ran 6 tests ... OK`). `git diff --check` was clean, and the fingerprint remained exactly `451c81e02e7e8bcf234e53a5a397c272d30d5309fa78296d84383adb626fa5db` after the checks. The broad `386/386 PASS` result was supplied and not duplicated.

The final-window probe used only temporary sentinel files and monkeypatch timing; it did not read a credential, touch an external system, or modify application/deployed state. This local report is not merge authority and does not substitute for the exact-PR-SHA App-owned Trust CI check and required external approvals.
