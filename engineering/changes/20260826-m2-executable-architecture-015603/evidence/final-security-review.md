# Final security review — M2-A executable architecture

## Identity and verdict

- Route: `0156034c05bd`
- Adoption base: `25bfbe59ea188d9687b20a9caad19e7db3d031f8`
- Reviewed HEAD: `99de2f9757400f7394b7a9e2c46b3ebce939e438`
- Packaged diff: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-25bfbe5..99de2f9.diff`
- Packaged diff SHA-256: `385aef31d68d78ce9f68b824900bba01d9980e66bf5370897cda77b2dac49a01`
- Verdict: **BLOCKED**

PASS requires zero Critical or Important findings. This review found zero Critical, one Important, and zero independent Minor findings.

## Findings

### Important I-1 — installer can overwrite target-owned architecture authority through a managed-path symlink

The design and P1 test plan require the installer to never install or overwrite target-owned `architecture/adoption.json`, `architecture/system.yaml`, or `architecture/rules.yaml`, including under `--force` (`engineering/changes/20260826-m2-executable-architecture-015603/architecture.md:35`; `test-plan.md:12-13`). The direct-path denylist is correct (`scripts/install_into.py:45-49`, `scripts/install_into.py:64-75`), but it is not enforced at the filesystem write boundary.

For every managed path, the installer tests the destination with APIs that follow symlinks and then calls `dst.parent.mkdir(...)` and `shutil.copy2(src, dst)` (`scripts/install_into.py:79-82`, `scripts/install_into.py:123-140`). `copy2` follows an existing destination symlink by default. Therefore a consumer repository can contain, for example, a managed destination symlink whose target is `architecture/system.yaml`; `install(..., force=True)` will copy the managed source through that alias and replace the bytes of target-owned architecture authority. An ancestor-directory symlink can likewise redirect a managed write outside the target repository. The current regression test writes the three authority paths as ordinary files and checks only direct-path exclusion (`tests/test_installer.py:76-92`), so it does not cover final- or ancestor-symlink aliases.

This violates the explicit target-ownership boundary and makes AC-006/P1 false for a valid repository filesystem shape. Remediation must make each managed destination write repository-contained and no-follow (including every ancestor and final component), fail closed on symlink/special-file/relocation races, and add final- and ancestor-symlink regression tests demonstrating that authority bytes and outside-target bytes remain unchanged under `--force`.

## Boundary evidence without blocking findings

- Malformed architecture input is byte-, depth-, node-, model-, rules-, contracts-, drift-count-, drift-file-, and drift-byte-bounded; parsing rejects BOM, duplicate keys, non-finite values, invalid UTF-8/surrogates, unknown schema content, unsafe paths, symlinks, special files, and concurrent mutation (`.grok-stack/adaptive_grok/architecture.py:20-31`, `:154-237`, `:240-330`, `:490-621`, `:727-897`; closed schemas under `schemas/architecture-*.schema.json`).
- Diagram behavior is repository-read-only: the CLI renders to stdout and `--check` performs descriptor-relative no-follow reads of only five fixed regular files with byte and identity checks; there is no exported or invoked write primitive (`scripts/grok_architecture.py:146-158`; `.grok-stack/adaptive_grok/architecture_diagrams.py:203-292`).
- Exact-state Git reads require exact 40-character commit objects, use an absolute Git executable, disable system/global configuration and replacement objects, pin safety-sensitive Git options, bound stdout/stderr/time, kill/reap the child process group, use literal pathspecs, accept only regular blob modes, and verify reported blob size (`.grok-stack/adaptive_grok/architecture_diff.py:64-205`, `:220-276`). Worktree reads use descriptor-relative no-follow regular-file reads and identity checks (`:340-406`).
- Architecture receipts bind current tree, spec criteria/digest/fingerprint, adoption/base/head/contract inventory and architecture digests/fingerprint; a change during writing marks the receipt stale and raises, while validation recomputes and compares all bindings (`.grok-stack/adaptive_grok/receipts.py:180-224`, `:266-357`).
- The exact base-to-head change set contains no `trust-ci/**` or `.github/workflows/**` path. M2-A remains local advisory evidence and does not claim merge authority.
- `git diff --check 25bfbe59ea188d9687b20a9caad19e7db3d031f8..99de2f9757400f7394b7a9e2c46b3ebce939e438` completed successfully.
- Bounded local suite: `python3 -m unittest tests.test_architecture_model tests.test_architecture_fitness tests.test_change_receipts tests.test_installer tests.test_verification_doctor` — **167 tests, OK**. This does not close I-1 because the symlink-alias scenario is absent from the installer tests.

## Residual risks and review boundary

The review was defensive and local-only. It inspected the frozen design/change package, SDD review package, exact source and bounded repository tests. It made no network calls, accessed no credentials or secrets, performed no external action, and does not attest deployed Trust CI, branch protection, external holdouts, approvals, or runtime infrastructure. Local reports and passing tests are workflow evidence only and are not merge authority.
