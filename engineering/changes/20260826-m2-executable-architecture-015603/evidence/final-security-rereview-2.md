# Final security re-review 2 — installer containment

## Exact identity and verdict

- Route: `0156034c05bd`
- Prior HEAD: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`
- Reviewed fix HEAD: `52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad`
- Exact package: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-fd5f7eb..52c4ab8.diff`
- Package SHA-256: `f6645ae122d1fd000796ace4eb2306e57a9b3a60f5461de6524492c6a34f750b`
- Residual directory-relocation finding: **ADDRESSED**
- Rollback mode boundary: **ADDRESSED**
- Staging-cleanup boundary: **NOT ADDRESSED** for a failed rollback publication
- Final verdict: **BLOCKED**

Scoped finding count: zero Critical, one Important, zero Minor. PASS requires zero Critical and Important findings.

## Addressed boundaries

- Created directory components remain transaction-owned through retained parent descriptors. Every opened prefix is reproved from the stable root, relocation causes reverse-order identity-checked `rmdir` rollback, and successful completion releases only the retained descriptors (`scripts/install_into.py:64-70`, `:114-216`). This applies both to managed-file parent creation and `ensure_dir` (`scripts/install_into.py:218-227`, `:322-378`).
- The same `tree.write` implementation remains the publication boundary for managed files, root `AGENTS.md`, and Bitrix `local/AGENTS.md`; ensured `engineering/**` paths use the corrected directory transaction (`scripts/install_into.py:416-429`, `:448-495`).
- Staged files receive an explicit `fchmod`, so rollback restores the captured original mode independently of umask (`scripts/install_into.py:252-280`, `:288-319`, `:332-361`).
- A failure while creating/writing/fsyncing the ordinary stage now unlinks that stage, and the enclosing failed write rolls back operation-created parents (`scripts/install_into.py:288-319`, `:365-378`).
- New tests exercise relocation during managed, AGENTS-like, Bitrix-like, and ensured-directory parent creation; exact byte/mode recovery under restrictive umask; and cleanup after an initial staging failure (`tests/test_installer.py:214-314`).

## Important finding

### I-1 — rollback staging is untracked and a rollback publication failure leaves mutated outside bytes

After a managed file has been published through a parent that is then detected as relocated, the recovery branch creates a second stage in local variable `rollback` and immediately calls `os.replace` (`scripts/install_into.py:351-361`). That stage name is never assigned to the outer `stage` cleanup variable. If this rollback `os.replace` raises, the outer `finally` sees `stage == ''`, so the rollback stage remains under the target root (`scripts/install_into.py:365-378`). More importantly, the already-published replacement remains in the relocated parent instead of the captured original bytes.

This is distinct from the covered initial `_stage` failure. `test_staging_failure_rolls_back_created_parent_and_stage` fails `os.fchmod` before first publication (`tests/test_installer.py:304-314`), while `test_relocation_rollback_preserves_bytes_and_mode_under_umask` lets the rollback `os.replace` succeed (`tests/test_installer.py:261-302`). No test fails allocation or publication of the rollback stage after relocation.

The result violates the requested fail-closed staging-cleanup and outside/authority-byte preservation boundary for managed files, root `AGENTS.md`, and Bitrix guidance, all of which share `tree.write`. Remediation should prepare and track rollback material before the first publication, keep every stage name under one cleanup owner, and add failures at rollback staging and rollback replace/fsync points. Each regression must prove exact original bytes and mode, no `.adaptive-install-*` residue, and no created-parent residue. If the platform cannot guarantee restoration after publication, the installer must avoid publication under that relocation window rather than claim rollback safety.

## New-regression audit and checks

- No other new Critical or Important installer-boundary regression was identified in the exact fix diff.
- Static final/ancestor symlinks and special files remain rejected; direct target-owned architecture authority remains excluded.
- `python3 -m unittest -v tests.test_installer`: **23 tests, OK**. The uncovered rollback-publication failure above prevents those green tests from closing the scoped boundary.
- `git diff --check fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d..52c4ab8fc43a21fe1c6b96ff5404bc39d3f7d2ad`: **PASS**.
- The exact fix range changes no `trust-ci/**` or `.github/workflows/**` path.

## Local-only disclaimer

This was a defensive local source review of the prior report, consolidated fix-wave evidence, exact packaged diff, current installer implementation, and bounded ordinary tests. It made no network call, accessed no credential or secret, performed no external action, modified no product code, and used no subagent. This report is local workflow evidence only and does not attest deployed Trust CI, external holdouts, approvals, branch protection, or merge eligibility.
