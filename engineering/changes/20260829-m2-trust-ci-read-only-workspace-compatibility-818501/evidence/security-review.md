# Independent security review

## Identity and verdict

- Route: `81850148d1f6`
- Change: `20260829-m2-trust-ci-read-only-workspace-compatibility-818501`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Reviewed worktree fingerprint: `58854a896966d3ec160697d61ca4e1dded628eddc028ef994a032d5a135483c7`
- Supplied pinned-runner evidence: `378/378 PASS`
- Verdict: **FAIL**
- Findings: Critical `0`, Important `1`, Minor `0`

The Git ownership compatibility repair is narrowly scoped and does not weaken the deployed Trust CI boundary, but the touched packaging boundary can follow a repository path symlink outside the source root and package external secret bytes. That Important confidentiality issue blocks PASS.

## Important findings

### I-1 — Packaging follows file symlinks outside the source root and bypasses secret exclusions

`included_files()` uses `Path.is_file()`, which follows symlinks, and applies exclusions only to the lexical link name (`.grok-stack/adaptive_grok/manifest.py:20-39`). Manifest hashing then opens that path normally (`.grok-stack/adaptive_grok/manifest.py:42-53`). The changed archive path records mode with `path.stat()` and later opens the same path normally, with no `lstat`, containment check, `O_NOFOLLOW`, descriptor identity binding, or post-read digest comparison (`scripts/package_stack.py:19-39`).

Consequently, a path such as `innocent.txt -> /path/to/.env` is admitted even though `.env`, `.key`, `.pem`, and related names are intended to be excluded. A local temporary sentinel probe against the reviewed implementation produced:

```text
member_present= True
outside_bytes_packaged= True
```

The probe created a source-root `innocent.txt` symlink to an external sentinel `.env`; the ZIP member contained the external bytes. No repository file or credential was read or changed. The same split hash/stat/open sequence also permits target/content changes between manifest rendering and archive streaming, so a mutable symlink target can make the embedded manifest describe different bytes from those archived.

Impact is Important: a committed or locally introduced benign-looking symlink can cause a release/package operation to disclose readable files outside the repository, including ignored secrets, and the archive may not be self-consistent. The exact reviewed tree currently contains no file symlinks, which explains why the pinned suite passes, but this is a latent input-boundary defect and there is no symlink regression in `tests/test_manifest_package.py:122-135` or `tests/test_manifest_package.py:185-201`.

Required remediation: reject symlinks and non-regular files during repository-contained enumeration and again at descriptor open; use no-follow, descriptor-relative reads with identity/stability checks, and ensure the bytes hashed for the embedded manifest are the same bounded bytes written to the archive. Add regressions for an external-secret symlink and a hash-to-stream replacement/race. Preserve the existing source-manifest invariance contract.

## Confirmed boundaries

- **Exact command-scoped Git trust:** repository roots are canonicalized with strict resolution, passed as the command `cwd`, and added as a single `-c safe.directory=<canonical-root>` argument (`.grok-stack/adaptive_grok/architecture_diff.py:173-226`). It is not persisted and no wildcard is used. The non-repository `diff --no-index` path receives no repository trust (`.grok-stack/adaptive_grok/architecture_diff.py:627-650`).
- **Sanitized Git process:** Git is resolved once, invoked with an argv and `shell=False`; the process receives a fresh allowlisted environment with system/global config disabled, replacement objects disabled, optional locks disabled, and prompting disabled (`.grok-stack/adaptive_grok/architecture_diff.py:44-45`, `.grok-stack/adaptive_grok/architecture_diff.py:88-93`, `.grok-stack/adaptive_grok/architecture_diff.py:158-170`). Repository-controlled hooks, fsmonitor, attributes, excludes, pager behavior, external diff, text conversion, and rename behavior are neutralized in argv (`.grok-stack/adaptive_grok/architecture_diff.py:173-207`).
- **Temporary clone configuration:** the receipt regression creates its config inside a `TemporaryDirectory`, disables system and host-global config while creating it, writes only `safe.directory=<exact ROOT/.git>`, and exposes that file only to the required `git clone --no-local` subprocess (`tests/test_change_receipts.py:322-351`). No wildcard, persistent config mutation, credential variable, or host HOME is inherited.
- **Source manifest mutation removed:** `render_manifest()` returns bytes and explicit `generate_manifest()` remains the only source-writing API (`.grok-stack/adaptive_grok/manifest.py:50-59`). `write_archive()` embeds synthetic manifest bytes and no longer creates or unlinks root `MANIFEST.sha256` (`scripts/package_stack.py:19-40`). This closes the stated read-only-manifest regression, subject to I-1.
- **Trust plane unchanged by this fix:** the actual worktree diff contains no `trust-ci/**` or `.github/**` change. Deployed policy, holdout, images, keys, state, branch protection, and external services remain outside repository authority.
- **Finite governance rule:** `max_changed_lines` changes from `10000` to the explicit finite `10100`; the typed change requires architecture and governance scopes. This is not a wildcard or deployed-policy relaxation (`architecture/rules.yaml:39-49`).

## Evidence boundary and residual risk

The supplied pinned-runner result is recorded as `378/378 PASS`; it was not broadly rerun during this independent review. I independently confirmed the supplied tree fingerprint, inspected the actual worktree diff and relevant surrounding code, ran `git diff --check`, verified no fix delta under `trust-ci/**` or `.github/**`, confirmed the exact tree contains no symlinks, and ran only the bounded temporary sentinel probe described in I-1. No application code, deployed state, external system, secret, or credential was modified or accessed.

No other Critical or Important issue was found in the scoped Git trust, environment isolation, clone configuration, or Trust CI separation changes.
