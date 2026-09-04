# Independent security re-review 5

## Identity and verdict

- Route: `81850148d1f6`
- Change: `20260829-m2-trust-ci-read-only-workspace-compatibility-818501`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Frozen pre-review implementation/evidence fingerprint: `55d50a669c5540c10b29f463cb6566737ad74dfcb121cdf77cf22382faf58a14`
- Current supplied focused evidence: `39/39 PASS`; the prior remediation-3 pinned result is stale and is not used as current-tree proof.
- Verdict: **PASS**
- Findings: Critical `0`, Important `0`, Minor `0`

The remediation-5 output-parent creation fix closes the remaining security-relevant boundary finding. Requested and canonical ancestry reject authority held by an unrelated UID, missing components are created beneath a held trusted parent and forced to exact private mode through retained descriptors, and archive/checksum publication remains bound to exclusive regular-file descriptors inside the retained private output directory. No Critical or Important boundary regression was found.

## Prior finding closure

### I8 — Restrictive umask could create an unusable/non-private missing parent and leave residue: ADDRESSED

`_ensure_output_parent()` identifies the first existing requested-path ancestor, resolves its canonical peer, and validates both chains before creation. Existing ancestors must be owned by root or the effective UID; a group/world-writable ancestor is rejected unless sticky semantics protect an effective-UID-owned next component. The creation parent receives a separate authority check (`scripts/package_stack.py:56-94`, `scripts/package_stack.py:106-125`). This rejects the earlier different-UID rename boundary while retaining the normal root-owned sticky `/tmp` case.

Each absent component is then created relative to the held parent fd. The implementation immediately retains an `O_PATH | O_DIRECTORY | O_NOFOLLOW` binding, compares it with a no-follow named stat, raises the new component to `0700` so it can be opened despite a restrictive umask, opens the directory no-follow, applies `fchmod(0700)` to that held directory fd, and verifies type, effective-UID ownership, device/inode identity, and exact mode before descent (`scripts/package_stack.py:126-177`). Thus neither umask `0700` nor `0777` strips owner access from the final accepted component.

Creation ownership is recorded immediately after successful `mkdirat`. Every binding/chmod/open/validation error closes the child and binding descriptors, the outer `finally` closes the retained chain fd, and reverse cleanup attempts only the components created by this invocation while retaining the primary exception (`scripts/package_stack.py:95-104`, `scripts/package_stack.py:132-179`). If later output binding or publication fails, the same owned chain cleanup runs; non-empty created parents are conservatively retained with a diagnostic note rather than recursively deleting contents (`scripts/package_stack.py:404-528`).

The committed oracles cover common and restrictive umasks, one and multiple missing components, exact `0700`, later binding failure cleanup, the final held-leaf owner predicate, unsafe non-sticky ancestry, and the supported root-owned sticky `/tmp` path (`tests/test_manifest_package.py:171-200`, `tests/test_manifest_package.py:373-487`). A separate read-only run of these and adjacent publication/source cases completed `13/13 PASS` in `0.138s`.

## Confirmed security boundaries

- **Requested/canonical chain and sticky authority:** both path views are validated, the final directory must be effective-UID-owned and not group/world writable, and its device/inode is held and rechecked against the requested binding before publication (`scripts/package_stack.py:56-94`, `scripts/package_stack.py:181-239`). A different UID cannot rename an effective-UID-owned child in an accepted sticky ancestor; same-UID and privileged mutation remains the explicit trusted exception.
- **Archive descriptor and publication:** existing output is inspected no-follow and must be regular. The sibling temporary uses `O_EXCL | O_NOFOLLOW | O_CLOEXEC`; mode changes, ZIP writes, bounded digesting, and identity checks use the held fd. Replace, post-publication inode validation, mismatch removal, and cleanup are relative to the retained private-parent fd (`scripts/package_stack.py:242-331`, `scripts/package_stack.py:404-528`). A hardlink output is replaced without modifying its other inode link; symlink, FIFO, directory, and other non-regular output entries fail before allocation.
- **Checksum descriptor and hostile entries:** an existing sidecar is inspected without following or opening. Directories fail before archive publication; a symlink, hardlink, FIFO, or other replaceable entry is atomically replaced by a separately held exclusive regular temporary. Existing regular mode is copied only onto that temporary. Published checksum identity is checked against the held fd, and a detected mismatch is removed relative to the held parent before failure (`scripts/package_stack.py:333-401`, `scripts/package_stack.py:408-416`). The hardlink target remains unchanged, FIFO handling does not block, and temp-name swaps do not touch an external target (`tests/test_manifest_package.py:202-332`).
- **Cleanup and controlled failures:** archive and checksum error paths attempt close and dirfd-relative unlink independently, attach cleanup failures as notes, and preserve the primary error. A swapped temp name is never opened; unlink removes only that directory entry. A valid archive may remain if later checksum publication fails, but no success is returned and the typed consumer contract permits use only after successful return (`scripts/package_stack.py:291-304`, `scripts/package_stack.py:333-360`, `scripts/package_stack.py:454-528`).
- **Source no-follow and integrity:** enumeration admits only `lstat`-verified regular files. Snapshot and archive streaming reopen every directory component and final file relative to held roots with `O_NOFOLLOW`, require regular type, compare full identity before/after, stream in bounded chunks, and bind the streamed ZIP bytes to the snapshot digest (`.grok-stack/adaptive_grok/manifest.py:23-31`, `.grok-stack/adaptive_grok/manifest.py:57-83`, `.grok-stack/adaptive_grok/manifest.py:105-187`, `.grok-stack/adaptive_grok/manifest.py:210-229`). External-secret symlinks are excluded and replacement after manifest rendering fails before output publication.
- **Read-only source behavior:** `write_archive()` renders manifest bytes in memory and writes only the caller-selected output directory. It does not create, replace, or remove source `MANIFEST.sha256`; the source-writing `generate_manifest()` remains a separate explicit API (`.grok-stack/adaptive_grok/manifest.py:190-235`, `scripts/package_stack.py:404-528`).
- **Exact Git trust:** Git is resolved once, invoked with an argument vector and `shell=False`, receives a fresh allowlisted environment with system/global config, replacement objects, prompts and optional locks disabled, and repository commands receive exactly one canonical command-scoped `safe.directory`. The isolated `diff --no-index` path receives no repository trust (`.grok-stack/adaptive_grok/architecture_diff.py:44-45`, `.grok-stack/adaptive_grok/architecture_diff.py:158-233`, `.grok-stack/adaptive_grok/architecture_diff.py:627-650`). No wildcard or persistent safe-directory configuration is introduced; the receipt clone fixture remains scoped to exact `ROOT/.git` in its temporary config.
- **Trust-plane separation:** the actual worktree delta is empty under `trust-ci/**` and `.github/**`; `git diff --check HEAD` is clean. No deployed policy, holdout, runner image, signing key, database state, branch protection, or external service is changed or claimed by this local fix.

## Residual threat boundary and evidence limits

The accepted private-parent design deliberately trusts the same effective UID and privileged actors. Such an actor can race names inside the private directory or relocate an effective-UID-owned component; post-publication checks still fail closed on detected inode mismatch, but the contract makes no portable zero-transient guarantee against that trusted actor. Actors lacking that authority cannot cross the validated ownership, sticky-directory, and private-mode chain.

The supplied current `39/39` focused result and this review's `13/13` security subset are current-tree evidence. The historical `391/391` remediation-3 pinned run is stale after later product/test changes; a fresh frozen-tree pinned run remains required before completion. Local tests and this report are not merge authority and do not replace the App-owned exact-PR-SHA policy-epoch check or required external approvals.

## Review actions and local-only disclaimer

I inspected the actual diff, typed requirements/specification, historical security/code/test reports, current package/source/Git implementations, and protected-path delta. I ran only the named bounded local unit subset and ordinary read-only Git/diff checks. No credential, network service, external system, deployed Trust CI state, application code, or policy was accessed or modified. This report records local defensive review evidence only.
