# M2-A final remediation round 4

Date: 2026-08-27

Status: implementation and pre-commit verification complete

Commit subject: `fix: make M2-A publication transactional`

## Scope and finding mapping

`code-rereview-3.md`, `test-rereview-3.md`, and `security-rereview-3.md` were read completely and preserved unchanged.

- Code/Security R3-I1 — transactional diagram publication: the writer stages a complete bounded architecture entry, preserves directory mode, ownership, and bounded xattrs, then atomically exchanges it at the held repository root. It compares authority/inventory identity and directory metadata between the staged and displaced entries after exchange. A mismatch or comparison error exchanges them back before reporting failure. Concurrent atomic authority replacement, concurrent extra target-owned entries, restrictive mode, and unavailable atomic exchange have direct regressions.
- Security R3-I1 cleanup boundary: displaced/staged cleanup uses a held child descriptor only for bounded, no-follow inventory. It closes that descriptor before mutation and re-proves the root-relative entry identity before every unlink/rmdir. Relocation before cleanup or during inventory leaves outside bytes untouched and fails instead of operating through the moved inode.
- Test/Security R3-I4 — receiver-bound queue applicability: the file-wide unknown-call/decorator fallback was removed. Calls and decorators signal only when their callable/receiver is transitively derived from a known queue root or proven local adapter. Mixed files with unchanged RQ, Celery, or a proven local adapter and new unrelated `.submit()`, `.delay()`, local `.task`, or generic calls remain true N/A with no `new_queue` trigger and clean drift.
- Code/Security R3-I2/I3 — bounded local provenance: operation dependencies select relevant local imports, and local adapter exports resolve through bounded assignment/import fixed points, including relative imports. Reaching the module, depth, or AST ceiling raises structured unsupported applicability; `_new_queue_sources` is the shared input to background fitness and monotonic risk, so `new_queue` remains aligned. Depth-nine, 32-module import-ceiling, relative re-export, and ordinary deep non-queue controls are covered.
- Code/Security R3-I3/I5 — legacy metadata compatibility: stable absence uses repeated universally available `lstat` metadata probes for the resolved repository root, fixed `architecture` entry, and three authority entries. It no longer opens a directory descriptor or invokes `stat(dir_fd=...)` to prove absence. Clean no-directory consumers remain unconfigured when descriptor-relative metadata and no-follow byte primitives are unavailable; authority appearance/unsafe entries still fail closed, and adopted byte reads retain their secure no-follow requirement.

No state, receipt, reviewer-report, dependency, service, migration, runtime API, external system, `trust-ci/**`, or `.github/workflows/**` file was changed.

## TDD evidence

Initial RED command:

```text
python3 -m unittest \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_publish_preserves_concurrent_authority_and_mode \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_publish_preserves_restrictive_architecture_mode \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_cleanup_never_mutates_relocated_backup \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_mixed_queue_files_ignore_operations_without_queue_provenance \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_adapter_resolution_bounds_fail_closed_only_for_possible_operations \
  tests.test_verification_doctor.VerificationTests.test_clean_legacy_without_architecture_avoids_descriptor_only_metadata
```

Observed RED after correcting test-fixture errors:

```text
concurrent authority replacement: ArchitectureError not raised
architecture directory mode: expected 0700, observed 0755
relocated backup cleanup: ArchitectureError not raised
mixed RQ/Celery/local-adapter files: four unrelated operations reported unsupported
depth-nine, module-ceiling, and relative adapter operations: reported not_applicable
clean descriptor-limited legacy repository: leaked raw NotImplementedError
Ran 6 tests; FAILED (failures=11)
```

GREEN boundary matrix after the repair, including prior relocation/symlink, positive provenance, collision, and concurrent-creation controls:

```text
python3 -m unittest \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_publish_preserves_concurrent_authority_and_mode \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_publish_preserves_restrictive_architecture_mode \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_cleanup_never_mutates_relocated_backup \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_write_does_not_publish_through_relocated_architecture \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_publish_does_not_follow_replacement_architecture_symlink \
  tests.test_architecture_model.ArchitectureModelTests.test_generated_diagram_write_rejects_directory_swap_without_outside_write \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_mixed_queue_files_ignore_operations_without_queue_provenance \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_queue_adapter_resolution_bounds_fail_closed_only_for_possible_operations \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_source_only_queue_signals_fail_background_fitness \
  tests.test_architecture_fitness.ArchitectureFitnessTests.test_unrelated_semantic_method_names_remain_background_not_applicable \
  tests.test_verification_doctor.VerificationTests.test_clean_legacy_without_architecture_avoids_descriptor_only_metadata \
  tests.test_verification_doctor.VerificationTests.test_legacy_absence_cannot_hide_authority_created_during_probe
Ran 12 tests in 8.796s
OK
```

Additional transactional branches:

```text
concurrent extra target-owned entry: rollback, entry preserved
atomic exchange unavailable: failure before mutation, authority/projections byte-identical
relocated cleanup entry: failure, every outside file byte-identical
Ran 4 tests in 0.141s
OK
```

Affected suites:

```text
python3 -m unittest \
  tests.test_architecture_model \
  tests.test_architecture_fitness \
  tests.test_change_receipts \
  tests.test_verification_doctor
Ran 151 tests in 122.936s
OK
```

Full discovery:

```text
python3 -m unittest discover -s tests
Ran 335 tests in 149.513s
OK
```

The no-record PR verifier was run after implementation and again after this evidence file was materialized; the final post-report result is the completion authority for the local tree:

```text
python3 scripts/grok_verify.py --mode pr --no-record --json
exit 0; status=pass; coverage=79%
```

## Static and architecture evidence

```text
ruff check .grok-stack/adaptive_grok scripts tests
All checks passed!

bandit -q -c bandit.yaml -r \
  .grok-stack/adaptive_grok scripts .grok/hooks \
  user_prompt_submit.py pre_tool_use.py post_tool_use.py pre_compact.py \
  session_start.py session_end.py stop_gate.py subagent_start.py subagent_stop.py
exit 0; only the existing shell_targets.py nosec informational warnings

python3 -m compileall -q .grok-stack/adaptive_grok scripts tests
exit 0
```

```text
python3 scripts/grok_spec.py validate \
  --change-id 20260826-m2-executable-architecture-015603 --gate --json
ok=true; errors=[]

python3 scripts/grok_architecture.py validate --json
ok=true; findings=[]

python3 scripts/grok_architecture.py drift --json
ok=true; findings=[]

python3 scripts/grok_architecture.py diagram --check --json
ok=true; mismatches=[]

python3 scripts/grok_architecture.py fitness \
  --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 \
  --worktree --pre-risk red --json
fitness_status=pass; 12 categories; risk red -> red
exact_base_sha=25bfbe59ea188d9687b20a9caad19e7db3d031f8

git diff --check 25bfbe59ea188d9687b20a9caad19e7db3d031f8
exit 0

git diff --name-only \
  25bfbe59ea188d9687b20a9caad19e7db3d031f8 -- trust-ci .github/workflows
empty output
```

## Files changed

- `.grok-stack/adaptive_grok/architecture_diagrams.py`
- `.grok-stack/adaptive_grok/architecture_fitness.py`
- `.grok-stack/adaptive_grok/receipts.py`
- `tests/test_architecture_fitness.py`
- `tests/test_architecture_model.py`
- `tests/test_verification_doctor.py`
- `engineering/changes/20260826-m2-executable-architecture-015603/evidence/remediation-final-4.md`

## Self-review

- Atomic exchange is required, checked before any destination mutation, and used both for publication and rollback. Unsupported kernels/filesystems fail closed; no rename fallback weakens the transaction.
- The staged and displaced authority inventories compare exact names plus regular-file device/inode/size/mtime identity. Directory mode, ownership, and bounded xattrs are copied and compared. In-place hardlink-visible authority edits are preserved; atomic replacement or inventory change rolls back.
- Cleanup descriptors are inventory-only. Every mutation is root-relative and preceded by the expected root-entry identity check, so the deterministic relocation window cannot delete through a moved directory descriptor.
- Queue resolver work is bounded by repository-wide Python/AST ceilings, 32 local modules, depth 8, and the existing 64-pass assignment cap. A reached ceiling becomes unsupported rather than absence; irrelevant imports are not resolved merely because queue code exists elsewhere in the file.
- Stable legacy absence reads no authority bytes and requires two matching full metadata states before returning unconfigured. Once any authority entry exists, the existing secure regular-byte readers remain mandatory.
- Existing M1/M2 behavior, exact Git state handling, diagram compare safety, positive queue cases, and adopted deletion/no-follow failures remain covered by the 151-test affected suite and 335-test full suite.

## Concerns

Transactional diagram publication intentionally requires Linux-style `renameat2(RENAME_EXCHANGE)` plus descriptor-relative/no-follow primitives and bounded xattr access. Where the filesystem or runtime cannot provide them, diagram writes fail closed; compare mode and clean legacy detection remain compatible. External exact-SHA Trust CI and fresh independent review remain outside this implementation task.
