# Test plan — M2 Trust CI read-only workspace compatibility

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Different-owner real Git repository requires exact command-scoped architecture trust | `ArchitectureFitnessTests.test_repo_git_commands_trust_only_the_exact_root_under_different_owner` |
| P0 | Pre-existing source manifest is unchanged and archive gets current rendered bytes | `PackageTests.test_write_archive_preserves_source_manifest_and_embeds_current_bytes` |
| P0 | Receipt clone keeps `--no-local` with an exact temporary Git trust config | `ReceiptTests.test_route_base_remains_a_separate_architecture_staleness_binding` |
| P0 | External-secret symlink is excluded without reading sentinel bytes | `PackageTests.test_archive_excludes_external_secret_symlink` |
| P0 | Hash-to-stream replacement aborts without publishing an archive | `PackageTests.test_archive_fails_closed_when_file_is_replaced_after_manifest_render` |
| P0 | Completed archive checksum streams without `Path.read_bytes()` | `PackageTests.test_archive_checksum_streams_without_output_read_bytes` |
| P0 | Temporary-name swap cannot redirect held-fd ZIP writes or publish a mismatched inode | `PackageTests.test_archive_temp_path_swap_fails_without_touching_external_target` |
| P0 | A swap after final name validation cannot return success, publish a sidecar, or leave a non-held output | `PackageTests.test_archive_final_validation_swap_cannot_publish_replacement_inode` |
| P0 | Group- or world-writable output parents fail before temporary/output publication | `PackageTests.test_archive_rejects_group_or_world_writable_output_parent` |
| P0 | Parent relocation fails without redirecting operations or leaking a temporary/output/sidecar entry | `PackageTests.test_archive_parent_relocation_fails_without_redirecting_or_leaking_temp` |
| P0 | Writable non-sticky ancestors are rejected while root-owned sticky `/tmp` plus a private child remains supported | ancestor authority package regressions |
| P0 | Held leaf output-directory ownership mismatch fails before temporary/output/sidecar creation and closes its descriptor | `PackageTests.test_open_output_directory_rejects_foreign_leaf_owner_and_closes_fd` |
| P0 | Missing default output parents are exactly `0700` under umasks `0002`, `0022`, `0700`, and `0777` | `PackageTests.test_missing_default_output_parent_is_private_under_restrictive_umasks` |
| P0 | Sidecar symlink/hardlink/FIFO names are replaced without following, external mutation, or blocking; directories fail before output | adversarial sidecar package regressions |
| P0 | Sidecar temp substitution and close failure clean names while preserving the primary error | sidecar/cleanup injection regressions |
| P0 | New/existing archive permissions retain umask and replacement compatibility | controlled-umask package regressions |
| P0 | Symlink-root enumeration/generate/verify and injected post-open `fstat` cleanup remain controlled | `ManifestTests` compatibility/security regressions |
| P0 | Missing POSIX descriptor flags do not break import or explicit legacy helpers, while secure snapshot fails controlled | `ManifestTests.test_manifest_import_and_legacy_helpers_work_without_posix_open_flags` |
| P0 | Measured 10,739-line compatibility diff passes the finite 10,820-line architecture budget | `ReceiptTests.test_pre_adoption_route_base_uses_one_architecture_comparison_base` and worktree fitness |
| P1 | Archive determinism, modes, exclusions, sidecar, installer content remain stable | `tests.test_manifest_package` |
| P1 | Hostile fsmonitor isolation and line-stat bounds remain stable | selected `ArchitectureFitnessTests` regressions |

## Automated checks

- Unit: pure manifest bytes, explicit manifest generation, archive members, source invariance.
- Integration: real Git repository under `GIT_TEST_ASSUME_DIFFERENT_OWNER=1`; real `git clone --no-local` fixture.
- Contract: public API/event contracts unchanged; archive layout and `generate_manifest` compatibility covered by existing tests.
- E2E: final reviewed-tree disposable exact-tree commit `ec341a22874872e50b2e73f05e6934c816f6fcc6` passed 404/404 under the pinned read-only runner contract. See [`evidence/pinned-runner-remediation-5.md`](evidence/pinned-runner-remediation-5.md); the remediation-3 result remains historical.
- Static analysis: focused Ruff plus `git diff --check` before handoff.

## Manual checks

- **Pinned RED reproduction:** UID/GID `10001:10001`, `/workspace:ro`, `.git:ro`; five architecture failures from lost outer `safe.directory`, receipt clone child `upload-pack` ownership rejection, and package root-manifest write failure.
- **Local TDD RED:** three targeted tests ran and failed with three errors: unavailable base SHA under dubious ownership, missing source manifest after packaging, and `clone --no-local` child ownership rejection.
- **Local focused GREEN:** 16 selected tests passed in 11.848 seconds after the minimal repair.
- **Secondary RED:** the pinned runner cleared the permission/package failures, then the 10,043-line intermediate change failed the prior exact 10,000-line ceiling.
- **Frozen-summary RED:** the structure test rejected the prior M2 handoff composite/rules digests after the approved rules-budget change altered the canonical summary.
- **Independent-review REDs:** a benign source symlink archived an external sentinel, a real post-render replacement succeeded with mismatched manifest/member bytes, and checksum calculation called the output path's forbidden `read_bytes()`.
- **First review-remediation GREEN:** 21 focused package, architecture, receipt, and frozen-summary tests passed in 17.607 seconds; its governed measurement was 10,228/10,300 lines with 72 lines headroom.
- **Code re-review REDs:** closing/reopening the temporary fd allowed a real symlink swap to overwrite an external sentinel; absent/existing outputs became `0600`; a symlink-root raised raw `ValueError`; injected post-open `fstat` failures leaked fds and raw `OSError`.
- **Final focused GREEN:** 26 package, architecture, receipt, and frozen-summary tests passed in 17.327 seconds; the final governed measurement is 10,311/10,400 lines with 89 lines headroom.
- **Remediation-2 REDs:** a deterministic post-final-validation swap did not raise before the repair; capability-absence import raised raw `AttributeError`; and generate/verify through a symlink-root alias raised raw `ValueError`.
- **Remediation-2 focused GREEN:** all three direct regressions passed, followed by all 23 manifest/package tests in 2.363 seconds; worktree fitness passes at 10,368/10,450 lines with 82 lines headroom.
- **Remediation-2 canonical refresh:** architecture digest `79061ad6...` and rules digest `04c1a996...` replace only the corresponding frozen handoff literals after the approved finite ceiling adjustment.
- **Remediation-3 REDs:** group/world-writable parents were accepted, and relocating the output parent after temporary creation left the held temporary inode orphaned in the relocated directory.
- **Remediation-3 focused GREEN:** both new regressions passed, followed by all 25 manifest/package tests in 2.370 seconds; the late-swap, deterministic archive, output-mode, and sidecar checks remain green.
- **Remediation-3 canonical refresh:** architecture digest `8210395a...` and rules digest `2a1e3da8...` replace only the corresponding frozen handoff literals after the finite ceiling adjustment.
- **Historical pinned GREEN:** 386/386 then-current tests passed in 234.638 seconds as UID/GID `10001:10001` with `/workspace:ro`, `.git:ro`, and `--network none` in the exact digest-pinned runner image.
- **Remediation-3 pinned GREEN:** 391/391 tests passed in 227.409 seconds on disposable exact-tree commit `c749343d535fe2d0d02ee6cf770b781e91c827c7` with UID/GID `10001:10001`, read-only container/workspace/Git metadata, `--network none`, executable ephemeral `/tmp`, and exact external `/workspace` Git trust.
- **Remediation-4 REDs:** a hardlink sidecar mutated an external sentinel, a FIFO subprocess timed out, symlink/directory sidecars failed after archive publication, umask-created default parents self-rejected, and writable non-sticky ancestor authority was accepted.
- **Remediation-4 focused GREEN:** all targeted ancestor, ownership, missing-parent, sidecar-type, sidecar-swap, and close-cleanup regressions passed; all 36 manifest/package tests passed in 2.425 seconds.
- **Remediation-4 canonical refresh:** architecture digest `ed04f439...` and rules digest `f3d8253a...` replace only the corresponding frozen handoff literals after the finite ceiling adjustment.
- **Remediation-5 REDs:** restrictive umasks `0700` and `0777` stripped owner permissions from a newly created output parent, and a later binding failure left the created directory behind; the prior effective-UID regression exited at ancestor validation instead of exercising the held leaf owner predicate.
- **Remediation-5 focused GREEN:** exact restrictive-umask, nested-parent, failure-cleanup, and leaf-only ownership regressions passed; all 38 manifest/package tests passed in 2.745 seconds, with Ruff, Bandit, and diff-check green.
- **Remediation-5 canonical refresh:** architecture digest `d2f31484...` and rules digest `2d42ca73...` replace only the corresponding frozen handoff literals after the finite ceiling adjustment.
- **Remediation-5 final pinned GREEN:** 404/404 tests passed in 230.283 seconds on disposable exact-tree commit `ec341a22874872e50b2e73f05e6934c816f6fcc6` with the digest-pinned image, UID/GID `10001:10001`, read-only container/workspace/Git metadata, `--network none`, executable ephemeral `/tmp`, and exact external `/workspace` Git trust.
- Release review, fingerprint-bound receipts, `ready` transition, and PR exact-SHA external evidence remain pending; this local result is never App-owned merge authority.
