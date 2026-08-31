# Independent security re-review 3

## Identity and verdict

- Route: `81850148d1f6`
- Change: `20260829-m2-trust-ci-read-only-workspace-compatibility-818501`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Frozen implementation/evidence fingerprint: `6d02ed6871caf130d120f9f01097725a4f4da50ffc4dac9f8b39c78c938a2f5c`
- Supplied pinned-runner evidence: `391/391 PASS` in `227.409s`
- Verdict: **FAIL**
- Findings: Critical `0`, Important `1`, Minor `0`

The narrowed same-UID/privileged/private-directory threat boundary is reasonable in principle, and it closes the earlier temporary-name race inside an actually private parent. The implementation enforces ownership and mode on the output parent itself, but not rename authority over that parent's pathname through writable ancestors. A different UID can therefore relocate the accepted private parent after the last binding check and cause a successful return whose requested output path has no archive or sidecar. This actor is outside the explicitly trusted set, so the boundary is not fully enforced and PASS is blocked.

## Important finding

### I-1 — Writable ancestor permits untrusted late output-parent relocation after the final binding check

`_open_output_directory()` requires the canonical output parent to be a directory owned by the effective UID and rejects group/world write bits, then binds its descriptor and device/inode (`scripts/package_stack.py:56-87`). That prevents another UID from mutating entries *inside* the directory. It does not prevent another UID with write/execute permission on a non-sticky ancestor from renaming the private child directory itself.

The requested pathname is checked against the held descriptor initially and again before ZIP work and immediately before publication (`scripts/package_stack.py:90-100`, `scripts/package_stack.py:250`, `scripts/package_stack.py:277`). All later replace, output validation, sidecar publication, and cleanup correctly use the held parent fd (`scripts/package_stack.py:278-293`). Consequently, relocation after line 277 does not redirect those operations to an external target—but it is no longer detected. The archive and sidecar are written into the relocated directory and the function returns success even though `output` at the requested pathname is absent or attacker-controlled.

A bounded temporary probe used a `0777` non-sticky ancestor containing an effective-UID-owned `0700` output parent and relocated the parent immediately after the third/final successful binding check. It produced:

```text
binding_checks= 3
returned_success= True
requested_output_exists= False
relocated_output_exists= True
relocated_sidecar_exists= True
```

The current relocation regression moves the parent immediately after temporary creation, so the next binding check catches it; it does not cover relocation after the final check (`tests/test_manifest_package.py:177-203`).

This is Important because AC-005 and the failure contract require a relocated/rebound requested parent to fail, and the consumer rule permits action after successful return with the requested held-inode output and sidecar present. The typed exception trusts same-UID or privileged actors and concurrent mutation *inside* the private parent. It does not trust an unrelated UID that can rename the parent via an unprotected ancestor.

Required remediation: enforce pathname stability against untrusted ancestor writers, not only entry mutation inside the final parent. The defensible design is to bind/walk the canonical ancestor chain descriptor-relative and reject any component whose containing directory grants untrusted rename authority (accounting for sticky-directory ownership semantics), or require a documented, verified secure ancestor root under which the private output parent is created. Merely adding another post-publication `stat` moves the race and cannot guarantee that path-based consumers see the bound directory after return. If the project instead chooses to trust every actor capable of mutating any requested-path ancestor, that broader exception must be explicit in the typed threat model and operationally acceptable; it is not the current same-UID/privileged boundary.

## Confirmed remediations and boundaries

- **Held private-parent authority:** once bound, existing-output inspection, temporary creation, name validation, replace, published-output validation, cleanup, and sidecar open are all relative to the one held directory descriptor (`scripts/package_stack.py:103-235`, `scripts/package_stack.py:246-293`). Parent entry relocation cannot redirect these descriptor-relative operations. I-1 concerns successful requested-path authority, not writes escaping the held fd.
- **Temporary/output identity:** the ZIP is constructed and digested through the original `O_EXCL | O_NOFOLLOW | O_CLOEXEC` descriptor. After replace, the output entry must be a regular file with the held device/inode; mismatch is unlinked relative to the held parent and fails before sidecar/return (`scripts/package_stack.py:27-31`, `scripts/package_stack.py:119-213`, `scripts/package_stack.py:248-291`). The prior final temp-name swap now fails, removes the mismatched entry, leaves the external symlink target unchanged, creates no sidecar, and returns no success (`tests/test_manifest_package.py:428-460`).
- **Cleanup safety:** detected symlink substitutions are removed with descriptor-relative `unlink`, never opened. A hardlink substitution removes only the sibling link, not another link's bytes. Cleanup of a renamed standalone replacement can remove that sibling name, but mutation inside the required private directory requires a same-UID/privileged actor and is explicitly trusted.
- **Output permissions:** new archives use kernel `0666 & ~umask`; replacement archives inherit the existing regular output's permission bits via `fchmod` on the held temporary descriptor (`scripts/package_stack.py:103-148`). Both focused mode regressions pass (`tests/test_manifest_package.py:462-492`).
- **Sidecar risks under the narrowed model:** `O_NOFOLLOW` prevents a sidecar symlink from being followed; a bounded probe confirmed controlled failure and unchanged target bytes (`scripts/package_stack.py:216-235`). The already-published verified archive may remain when sidecar publication fails, but no success is returned and the contract says consumers act only after success. An existing hardlink sidecar aliases and truncates its external inode; creating such an entry in the enforced private parent requires a same-UID/privileged actor and is therefore an accepted residual under the typed model. Partial sidecar write/close failure similarly returns no success and is not checksum authority. If pre-existing private-directory contents are not intended to be trusted, sidecar publication needs a held exclusive temporary fd plus atomic verified replace rather than `O_TRUNC`.
- **Lazy POSIX capabilities:** source descriptor flags and output-directory/temporary flags are resolved only on secure packaging paths; missing flags, `geteuid`, or descriptor inspection fail with controlled `ManifestError`/`PackageError`, while explicit legacy manifest generation/verification imports and runs without those flags (`.grok-stack/adaptive_grok/manifest.py:23-31`, `scripts/package_stack.py:27-38`, `tests/test_manifest_package.py:34-63`). The pinned Linux contract exercises the required descriptor-relative APIs.
- **Source containment and integrity:** enumeration uses `lstat` and excludes symlinks/non-regular files. Every descendant component is reopened relative to the held source root with `O_NOFOLLOW`; stable device, inode, mode, size, mtime, ctime, and digest are required across manifest hashing and ZIP streaming (`.grok-stack/adaptive_grok/manifest.py:57-83`, `.grok-stack/adaptive_grok/manifest.py:105-187`, `.grok-stack/adaptive_grok/manifest.py:210-229`). Source replacement and external-secret symlink regressions remain passing.
- **Read-only source:** packaging only reads source descriptors and writes caller-owned output paths. It never creates, replaces, or removes source `MANIFEST.sha256`; explicit `generate_manifest()` remains the separate source-writing API (`.grok-stack/adaptive_grok/manifest.py:190-235`, `scripts/package_stack.py:237-293`). The supplied pinned run used `/workspace:ro`, `.git:ro`, read-only container root, UID/GID `10001:10001`, and network `none`.
- **Exact Git trust:** repository Git remains strictly canonical, command-scoped to one exact `safe.directory`, and runs with sanitized system/global config, hooks, fsmonitor, replace objects, prompting, attributes and external diff controls. Non-repository no-index work receives no repository trust; the clone fixture retains only its temporary exact `ROOT/.git` config. No wildcard or persistent configuration was introduced.
- **Trust-plane separation:** the actual fix delta is empty under `trust-ci/**` and `.github/**`. Deployed policy, holdout, images, keys, state, branch protection, and external services remain outside repository authority.

## Focused evidence and limitations

Ten adjacent security regressions independently passed: lazy capability behavior, post-open fd cleanup, unsafe-parent rejection, early parent relocation, early and final temp-name swaps, external source symlink, source replacement, and both output-mode cases (`Ran 10 tests ... OK`). `git diff --check` was clean. The supplied `391/391 PASS` pinned-runner evidence was inspected and not duplicated.

The relocation and sidecar probes used only temporary sentinel files. The hardlink probe intentionally demonstrated the explicitly trusted same-UID residual using temporary data; no real external file, credential, deployed system, policy, or application code was modified or accessed. This report is local review evidence only and does not substitute for the exact-PR-SHA App-owned Trust CI check or required external approvals.
