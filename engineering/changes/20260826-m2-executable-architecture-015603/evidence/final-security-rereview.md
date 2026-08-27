# Final security re-review — installer containment fix wave

## Identity and verdict

- Route: `0156034c05bd`
- Prior reviewed HEAD: `99de2f9757400f7394b7a9e2c46b3ebce939e438`
- Fix HEAD: `fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`
- Exact package: `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-99de2f9..fd5f7eb.diff`
- Package SHA-256: `ac1aba14c8498f1c3d1fd6fbd9de7ef7557b09c8c14c9461ce7d5921a3acca54`
- Prior installer finding: **NOT ADDRESSED** (substantially repaired, but one required relocation boundary remains open)
- Final verdict: **BLOCKED**

Finding count in the scoped fix-wave review: zero Critical, one Important, zero Minor. PASS requires zero Critical and Important findings.

## Resolution of prior finding

The ordinary managed-file alias is addressed. `_TargetTree` opens the target and path ancestors descriptor-relatively with `O_NOFOLLOW`, rejects final symlinks and special files, bounds and identity-checks reads, stages inside the root descriptor, and publishes with descriptor-relative `os.replace` (`scripts/install_into.py:64-135`, `:155-275`). The common `tree.write` boundary is used by the managed copy loop, root `AGENTS.md`, and Bitrix `local/AGENTS.md` (`scripts/install_into.py:313-326`, `:345-380`). The new tests cover final symlink to authority, symlinked ancestor to outside, FIFO destination, and file-parent relocation rollback while asserting authority/outside bytes remain unchanged (`tests/test_installer.py:154-211`).

However, the prior finding explicitly required relocation-safe containment for all installer mutations, including ensured directories. That part is still open.

## Important finding

### I-1 — directory creation can escape the current repository after ancestor relocation

`_open_dir(..., create=True)` checks the root only once at entry, then walks components using the currently open descriptor. When a component is absent it calls `os.mkdir(component, dir_fd=descriptor)` and continues (`scripts/install_into.py:97-134`). If an already opened ancestor is renamed out of the repository and replaced while this loop is between components, subsequent directory creation occurs through the old descriptor in the relocated outside tree. Neither `_open_dir` nor `ensure_dir` reopens the completed path from the current root and compares identities or rolls back directories created through the relocated chain (`scripts/install_into.py:136-145`).

The installer exercises that primitive for seven ensured `engineering/**` paths (`scripts/install_into.py:382-392`). The same gap can create intermediate managed-file parent directories outside the current target before `write()` reaches its later file-publication identity check (`scripts/install_into.py:229-265`). The file writer can avoid or roll back the file publication, but it does not track and remove directories already created during `_open_dir(create=True)`.

The new relocation regression patches `os.replace` after `.grok` already exists and verifies restoration of one file (`tests/test_installer.py:182-211`). It does not relocate an ancestor during multi-component directory creation, and there is no equivalent regression for ensured directories. Therefore the fix does not yet satisfy the requested relocation containment across all installer mutation surfaces.

Required remediation: make directory creation transactional or revalidate the complete path from the stable root after every created component; on relocation, remove only directories created by this operation through retained descriptors and fail closed. Add bounded regressions for relocation during `engineering/contracts/openapi` creation and during managed parent creation, proving no directory/file is left in the relocated outside tree and authority/outside bytes remain unchanged.

## Checks and absence of other scoped regressions

- Existing final/ancestor symlink and special-file destinations fail before a content write; direct target-owned authority paths remain denylisted (`scripts/install_into.py:46-50`, `:155-168`, `:278-300`).
- Root `AGENTS.md` and Bitrix-local file publication use the hardened writer; no direct `Path.write_*`/`shutil.copy2` write remains on those paths (`scripts/install_into.py:313-326`, `:368-380`).
- `tree.ensure_dir` rejects statically present symlink/special components. The blocker is specifically concurrent relocation after a component descriptor has been opened.
- `python3 -m unittest -v tests.test_installer`: **20 tests, OK**.
- `git diff --check 99de2f9757400f7394b7a9e2c46b3ebce939e438..fd5f7eb41fe63c8c0950c0195cfcf54a00dee04d`: **PASS**.
- No new Critical or other Important boundary regression was identified in the scoped fix diff.

## Local-only disclaimer

This was a defensive, read-only review of local source, the exact packaged diff, prior reports, and bounded local tests. No network call, credential or secret access, external action, product-code modification, or subagent was used. This report is local workflow evidence only; it does not attest deployed Trust CI, external holdouts, approvals, branch protection, or merge eligibility.
