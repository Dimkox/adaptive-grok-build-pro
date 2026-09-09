# M2-A decisive remediation test re-review 4

## Verdict

**BLOCKED**

Reviewed exact remediation range `cb0be3ceb56abf353dbfb83d60b52d09825227f6..7061ad2561d5fd4746b4ef476f7ecbb9c34d05c1` under route `0156034c05bd`. The packaged patch `.superpowers/sdd/2026-08-26-m2a-executable-architecture/review-cb0be3c..7061ad2.diff` applied cleanly to an archive of the exact base and produced a byte-identical tree to the exact head. HEAD remained `7061ad2561d5fd4746b4ef476f7ecbb9c34d05c1` throughout the read-only review.

Finding count: 0 Critical, 3 Important, 1 Minor. All three Important findings are incomplete closures/later windows of previously reported diagram and relative-provenance findings; no distinct new Critical/Important defect family was found.

## Important findings

### TST-R3-I1A — REPEATED/UNRESOLVED: authority replacement after the inventory snapshot is still lost with a successful return

Atomic exchange makes the destination swap indivisible, but the authority comparison is not a conditional atomic operation. `_replace_generated()` exchanges first, reads the staged/current inventory and then the displaced/previous inventory, compares directory mode/ownership/xattrs, and proceeds to destructive cleanup (`.grok-stack/adaptive_grok/architecture_diagrams.py:463-505`). Nothing revalidates the displaced authority after `_authority_inventory(previous_fd)` returns. Directory metadata at lines 478-480 excludes directory mtime/ctime, so an atomic authority-file replacement after that inventory snapshot is not detected.

An independent exact-head probe injected a replacement of the displaced `system.yaml` immediately after the second production `_authority_inventory()` returned but before metadata comparison:

```text
writer outcome=success
inventory_calls=2
concurrent_replaced=true
published_is_concurrent=false
published_restored_old=true
leftover staging entries=[]
```

The command reported success and cleanup deleted the concurrent target-owned bytes. This is the same lost-authority-update defect as prior Code/Security R3-I1/I2, at a later comparison window rather than a new defect family.

The committed regression at `tests/test_architecture_model.py:704-732` replaces authority before entering `_replace_generated()`, so both inventories observe the mismatch and rollback. The inventory-change test at lines 742-758 likewise adds the owner entry before exchange. Neither mutates the displaced entry after its final inventory snapshot, and neither can fail when the comparison itself becomes stale.

Required repair: use a publication design whose authority precondition and mutation are protected by one enforceable ownership/locking or syscall-level protocol, or stop replacing the target-owned authority container. Add deterministic replacements after each side's final inventory/metadata observation and assert failure or preservation of the newest authority, never successful restoration of stale bytes. Snapshot all three authority files, projections, directory metadata, and hidden recovery entries.

### TST-R3-I1B — REPEATED/UNRESOLVED: cleanup can still delete outside after the final identity check

`_discard_architecture_entry()` now closes inventory descriptors and calls `_require_entry_identity()` before each mutation, which fixes relocation before cleanup. It then performs multi-component `stat`, `unlink`, and `rmdir` operations relative to `root_fd` (`architecture_diagrams.py:333-385`). The identity check and mutation are separate syscalls. If the checked entry is relocated and replaced by an outside-pointing symlink after line 366 returns, `follow_symlinks=False` protects only the final component; the intermediate entry is followed by lines 368 and 371.

An independent exact-head cleanup probe moved the checked temporary architecture tree outside and installed a symlink at its old root-relative name immediately after the first successful `_require_entry_identity()`:

```text
outcome=ArchitectureError
identity_checks=1
outside_unchanged=false
outside file deleted=generated/container.mmd
```

The later check detected the symlink, but only after the first external file had been deleted. This is the later mutation window of prior Security R3-I1, not a new defect family.

The committed cleanup test at `tests/test_architecture_model.py:785-824` relocates the tree before `_discard_architecture_entry()` begins, so its initial `_entry_identity()` rejects the path before any child mutation. It does not exercise relocation after a successful per-mutation identity check. The remediation evidence's claim that relocation “during inventory” is safe also does not cover the check-to-unlink window.

Required repair: avoid destructive cleanup where containment is not guaranteed at the mutation syscall, or use a primitive that rejects intermediate symlinks and proves beneath-root resolution atomically for each mutation. Add deterministic hooks after the identity check and after child stat for generated files, authority files, and directory removal; assert every outside byte/name is unchanged.

### TST-R3-I3 — REPEATED/INCOMPLETE: relative queue provenance fails through a package `__init__.py`

The resolver now supports the tested file-module form `project/jobs.py -> from .celery_app import app`. `_local_queue_exports()` also accepts `project/jobs/__init__.py` as an alternative blob for module `project.jobs` (`.grok-stack/adaptive_grok/architecture_fitness.py:1108-1113`), but it does not retain which alternative was selected. `_resolve_import_module()` always removes the last component of `current_module` before resolving a relative import (`architecture_fitness.py:1073-1082`). That is correct for `project/jobs.py`; for `project/jobs/__init__.py`, `from .celery_app import app` must resolve to `project.jobs.celery_app`, not `project.celery_app`.

Independent exact base/head results:

```text
project/jobs.py -> from .celery_app import app:
background_job=unsupported overall=fail new_queue=true

project/jobs/__init__.py -> from .celery_app import app:
background_job=not_applicable overall=pass new_queue=false
```

The second head adds a real `@app.task` backed by `project/jobs/celery_app.py`, yet applicability and risk both disappear. This is an incomplete closure of prior relative-import provenance finding Security R3-I3. The committed relative regression at `tests/test_architecture_fitness.py:850-867` covers only the module-file form, so it false-passes the broader “including relative imports” claim.

Required repair: carry module-vs-package origin through local blob resolution and resolve relative imports against the correct package context. Add `package/__init__.py` cases for `from .child`, `from . import child/export`, parent-relative imports, aliases/re-exports, and depth/module boundaries. Retain exact base/head subtraction and assert `unsupported`, overall fail, and aligned `new_queue` for the real task delta.

## Minor finding

### TST-M1 — The affected-suite count in remediation evidence is not repeatable at exact HEAD

`remediation-final-4.md` records 151 tests for the four affected modules. Exact-head discovery loads 49 architecture-model, 39 architecture-fitness, 22 change-receipt, and 43 verification-doctor tests: 153 total, and the independent run passed all 153. Full discovery is repeatable at the reported 335/335. This is an evidence-count accuracy issue, not a hidden test failure.

## Confirmed closures and meaningful coverage

- Proven existing RQ/Celery objects, assignment/`getattr`/factory chains, direct local adapters, and the tested file-module relative adapter revoke N/A and produce aligned `new_queue`.
- Mixed RQ/Celery/local-adapter files with new unrelated `.submit()`, `.delay()`, local `.task`, and generic calls now remain true N/A with overall pass, no trigger, and clean drift. TST-I1-R3 is closed for the requested matrix.
- Depth-nine and module-ceiling possible-operation cases fail closed as unsupported; an ordinary deep non-call assignment stays N/A. The package-relative bypass above is separate from the explicit ceiling behavior.
- Clean legacy absence returns `None` without descriptor-relative `open/stat` or `O_NOFOLLOW`; authority creation during the first absence observation fails closed. No distinct false-pass path was found in these legacy tests.
- Normal transactional publication independently preserved restrictive mode, uid/gid, a user xattr, authority bytes, and left no hidden staging entry.
- Injected atomic-exchange unavailability independently failed before destination mutation, preserved the complete file/metadata snapshots, and left no hidden staging entry. The committed no-exchange test compares only architecture file bytes, but current cleanup behavior satisfied the stronger oracle.
- The early authority-replacement, owner-inventory, restrictive-mode, no-exchange, relocation-before-cleanup, parent-relocation, and replacement-symlink tests all exercise real filesystem state and passed; the findings above identify later untested windows rather than invalidating those exact assertions.

## Independent verification

- Packaged patch applied to exact base and matched exact head: PASS, zero tree differences.
- Twelve focused remediation/prior-boundary selectors: PASS, 12/12.
- `python3 -m unittest -q tests.test_architecture_model tests.test_architecture_fitness tests.test_change_receipts tests.test_verification_doctor`: PASS, 153/153.
- `python3 -m unittest discover -s tests`: PASS, 335/335.
- Independent normal mode/xattr/authority/cleanup probe: PASS.
- Independent no-exchange full-tree/metadata/no-leftover probe: PASS.
- Independent post-inventory authority replacement: reproduced successful loss of concurrent authority.
- Independent post-identity cleanup relocation/symlink: reproduced deletion of an outside generated file before failure.
- Independent file-module versus package-`__init__` relative adapter matrix: package form reproduced `not_applicable`, overall pass, no trigger.
- `git diff --check cb0be3ceb56abf353dbfb83d60b52d09825227f6..7061ad2561d5fd4746b4ef476f7ecbb9c34d05c1`: PASS.
- Exact remediation range under `trust-ci/**` and `.github/workflows/**`: empty.

Local evidence does not replace the App-owned exact-SHA Trust CI check or external approvals.

## Conclusion

Round 4 meaningfully closes the mixed-file queue false positives, explicit resolver ceilings, legacy descriptor compatibility, restrictive-mode preservation, and the tested early transaction/cleanup branches. It does not close the prior transactional safety finding at the last-observation-to-mutation windows, and its relative-import test covers a module but not a package. Because exact-head probes still lose concurrent target-owned authority, delete an outside file during cleanup, and hide a real package-relative Celery task as N/A, test review remains BLOCKED for exact head `7061ad2561d5fd4746b4ef476f7ecbb9c34d05c1`.
