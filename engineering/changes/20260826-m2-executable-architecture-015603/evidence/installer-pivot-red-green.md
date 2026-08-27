# Installer pivot RED/GREEN evidence

## Scope and design

Task 2 replaces in-place installation with two boundaries: deterministic,
read-only planning for every existing target and descriptor-relative staging
plus one no-replace rename for an absent target. The implementation does not
execute dependency commands, infer a target profile, copy architecture
authority, or mutate an existing target.

The source payload is represented by immutable `InstallEntry` values and is
sorted by UTF-8 path bytes. A single payload instance supplies both the plan
manifest and staged bytes. Materialization retains parent/stage directory
descriptors and inode identities; files use `O_NOFOLLOW|O_CREAT|O_EXCL`, exact
`fchmod`, full write, `fsync`, read-back digest verification, and exact
inventory comparison. Publication uses only
`renameat2(RENAME_NOREPLACE)` and has no replace fallback.

## RED

Planning regressions were added before the implementation:

```text
python3 -m unittest -v \
  tests.test_installer.InstallerTests.test_existing_target_modes_are_read_only \
  tests.test_installer.InstallerTests.test_force_is_rejected_without_mutation
Ran 2 tests in 1.436s
FAILED (failures=2)
```

The default path attempted `mkdir` under patched mutation primitives, while
`force=True` did not raise and overwrote managed content.

Materialization and packaged-install regressions were then added:

```text
python3 -m unittest -v tests.test_installer -k materialize_new
Ran 6 tests in 0.016s
FAILED (errors=10)

python3 -m unittest -v \
  tests.test_manifest_package.PackageTests.test_packaged_installer_materializes_new_target_without_authority
Ran 1 test in 1.362s
FAILED (errors=1)
```

The failures were the expected missing `plan_install`, `materialize_new`,
`_rename_noreplace`, `_write_all`, and `_verify_stage` APIs. No new-target
atomic publication contract existed.

## GREEN

Focused planning and materialization:

```text
python3 -m unittest -v \
  tests.test_installer.InstallerTests.test_existing_target_modes_are_read_only \
  tests.test_installer.InstallerTests.test_force_is_rejected_without_mutation
Ran 2 tests in 0.086s
OK

python3 -m unittest -v tests.test_installer -k materialize_new
Ran 6 tests in 2.805s
OK

python3 -m unittest -v tests.test_installer
Ran 11 tests in 3.430s
OK

python3 -m unittest -v \
  tests.test_manifest_package.PackageTests.test_packaged_installer_materializes_new_target_without_authority
Ran 1 test in 1.700s
OK
```

The materialization matrix covers exact payload/mode/digest verification under
umask `077`, runnable installed CLI, authority absence, required empty
directories, no dependency subprocess, existing directory/symlink/FIFO,
concurrent target creation, parent relocation, and injected write, fsync,
manifest-check, and publication failures. Every pre-publication failure leaves
the existing target/outside sentinel unchanged and removes the exact owned
stage.

Combined regression and static evidence:

```text
python3 -m unittest -v \
  tests.test_installer tests.test_manifest_package tests.test_structure
Ran 36 tests in 5.876s
OK

python3 -m ruff check \
  scripts/install_into.py tests/test_installer.py tests/test_manifest_package.py
All checks passed!

python3 -m bandit -q -c bandit.yaml scripts/install_into.py
exit 0

python3 -m compileall -q scripts
exit 0

git diff --check
exit 0

git diff --name-only \
  54448fcb5b62f81bc141eca2bcf984155ec20cd5 -- \
  trust-ci .github/workflows
empty output

python3 scripts/grok_architecture.py fitness \
  --base 54448fcb5b62f81bc141eca2bcf984155ec20cd5 \
  --worktree --json
fitness_status=pass; no unsupported/failing categories
```

## Files and self-review

- `scripts/install_into.py`: immutable payload/plan API, static dependency
  advice, descriptor-relative staging and exact cleanup, no-replace publish,
  read-only compatibility wrapper, and explicit CLI modes.
- `tests/test_installer.py`: planning, payload, CLI, success, target-race, and
  failure-containment behavior tests.
- `tests/test_manifest_package.py`: extracted-package materialization test.
- This evidence file and the ignored Task 2 report: exact delivery evidence.

Self-review confirmed that planning has no write flags, filesystem mutation,
dependency checks, or runner calls; source modes and bytes are captured once;
authority paths are rejected even if added to the managed list; stage cleanup
uses only recorded identities and known payload paths; target appearance maps
to `UnsafeInstallTarget`; and unsupported no-replace primitives fail closed.
After successful rename cleanup ownership is cleared, so there is no false
rollback claim over the newly published target.

Residual risk is platform availability of `renameat2(RENAME_NOREPLACE)`, which
intentionally makes materialization unavailable rather than falling back to a
racy rename. Rollout is source-only through review. Rollback is a revert of the
Task 2 commit; no existing repository, dependency state, or external system is
mutated by verification.

Commit subject: `refactor: make installer publication atomic`.

## Task 2 fix round 1 — review boundary hardening

The three Important review findings shared one ownership problem: pathname
validation and resource allocation were separated from the descriptor or
created-name authority used later. The repair binds target ancestry one
component at a time from a retained filesystem-root descriptor, reads every
managed source through retained no-follow descriptors with a `limit + 1`
ceiling and stable full file identity, and records each exclusive staged name
immediately after creation so constructor failures can clean only that owned
entry. The compatibility notice now has one shared literal and each invocation
prints it once.

### RED

The initial combined regression run exercised an intermediate/final ancestry
swap, managed/AGENTS/Bitrix/toolchain source races, and stage/directory/file
constructor gaps:

```text
python3 -m unittest -v \
  tests.test_installer.InstallerTests.test_materialize_new_rejects_ancestor_swaps_during_parent_binding \
  tests.test_installer.InstallerTests.test_source_reads_are_nofollow_and_bounded_at_the_descriptor \
  tests.test_installer.InstallerTests.test_constructor_failures_remove_every_exclusively_created_entry
Ran 3 tests in 0.207s
FAILED (failures=7, errors=1)
```

The old parent binding followed the swapped ancestry (or leaked a raw
`NotADirectoryError`), all three injected post-create metadata failures left an
`.adaptive-install-*` sibling, and path reads exceeded the declared boundary.
After correcting a test-callback precedence defect, the definitive source-read
RED was:

```text
python3 -m unittest -v \
  tests.test_installer.InstallerTests.test_source_reads_are_nofollow_and_bounded_at_the_descriptor
Ran 1 test in 0.009s
FAILED (failures=4)
```

All four source families consumed 34 bytes through the swapped path where the
test allowed at most the configured `limit + 1` of 33 bytes; the toolchain path
also failed to reject its swapped source.

### GREEN

```text
python3 -m unittest -v \
  tests.test_installer.InstallerTests.test_materialize_new_rejects_ancestor_swaps_during_parent_binding \
  tests.test_installer.InstallerTests.test_source_reads_are_nofollow_and_bounded_at_the_descriptor \
  tests.test_installer.InstallerTests.test_constructor_failures_remove_every_exclusively_created_entry \
  tests.test_installer.InstallerTests.test_cli_modes_plan_by_default_and_materialize_only_when_explicit
Ran 4 tests in 1.153s
OK

python3 -m unittest -v \
  tests.test_installer tests.test_manifest_package tests.test_structure
Ran 39 tests in 6.375s
OK

python3 -m ruff check \
  scripts/install_into.py tests/test_installer.py tests/test_manifest_package.py
All checks passed!

python3 -m bandit -q -c bandit.yaml scripts/install_into.py
exit 0

python3 -m compileall -q scripts tests
exit 0

git diff --check
exit 0

git diff --name-only -- trust-ci .github/workflows \
  .grok-stack/adaptive_grok/queue_provenance.py \
  tests/test_architecture_fitness.py
empty output

python3 scripts/grok_architecture.py fitness \
  --base e28d6f404e624f0840487b6ab70e01ea32c6832e \
  --worktree --json
fitness_status=pass; risk_post=green; no failing/unsupported category
```

### Files, self-review, and recovery

- `scripts/install_into.py`: stable component-wise directory bindings, bounded
  descriptor-relative source reads, immediate created-name ownership, exact
  constructor-failure cleanup, and one compatibility notice constant.
- `tests/test_installer.py`: deterministic ancestry-swap, bounded-read race,
  registration-gap, and single-notice regressions.
- This evidence and the ignored Task 2 report record the fix round.

Self-review confirmed that source accepts bytes only after dev/inode/size/
mtime/ctime/mode stability, final and ancestor symlinks are never followed,
publication remains the sole target mutation, and cleanup stays limited to
exclusive installer-created names under retained directory descriptors. No
target/outside sentinel changed in any injected failure. Residual platform risk
is unchanged: lack of `O_NOFOLLOW`, descriptor-relative directory operations,
or `renameat2(RENAME_NOREPLACE)` disables materialization rather than selecting
an unsafe fallback. Rollout remains source-only; rollback is a revert of this
fix commit, with no external or installed-repository state to recover.

Commit subject: `fix: harden installer path ownership`.
