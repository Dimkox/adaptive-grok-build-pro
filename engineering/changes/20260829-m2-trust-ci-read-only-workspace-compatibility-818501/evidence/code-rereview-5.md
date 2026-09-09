# Independent code re-review 5

## Identity, scope, and verdict

- Route: `81850148d1f6`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- Reviewed HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Frozen implementation/evidence fingerprint independently matched before this report was written: `55d50a669c5540c10b29f463cb6566737ad74dfcb121cdf77cf22382faf58a14`
- Scope: full actual diff from HEAD, surrounding implementation/tests, historical review chain, remediation-5 durable package, and regression review of parent creation, output/checksum publication, source reads, exact Git trust, portability, error handling, and descriptor cleanup.
- Current supplied evidence: 39/39 focused tests PASS plus Ruff, Bandit, and diff-check PASS. The remediation-3 disposable pinned 391/391 result is historical and stale for the remediation-5 product/test tree, as the package correctly states.
- **Verdict: PASS** — zero Critical and zero Important findings. Two Minor documentation findings remain.

Local evidence is not merge authority. Fresh pinned remediation-5 verification, final fingerprint-bound receipts, and the App-owned policy-epoch check plus required external approvals on the exact pull-request SHA remain required.

## Prior finding verdict

### Code re-review 4 I7/I8 — restrictive umask breaks missing-parent creation: ADDRESSED

`_ensure_output_parent` now returns explicit cleanup ownership and creates each missing component relative to the already-held parent descriptor (`scripts/package_stack.py:103-203`). For each new name it:

1. uses dirfd-relative `os.mkdir` without changing the process umask (`:143-147`);
2. binds the name with Linux `O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC`, compares held and no-follow named device/inode plus effective-UID ownership (`:148-164`);
3. applies `0700`, reopens no-follow through the held parent, applies `fchmod(0700)` to that held child, and requires exact mode/identity before using it as the next parent (`:165-194`);
4. independently closes child/binding descriptors and removes only operation-created components in reverse order on failure (`:103-113`, `:190-203`).

`write_archive` retains the created-component list across the subsequent output-directory binding and removes it if that step fails (`scripts/package_stack.py:467-528`). This closes both the former `0000` self-rejection and single-component residue path without a process-global umask window.

The committed oracles cover default output under `0002`, `0022`, `0700`, and `0777`; two missing levels under `0777`; post-creation binding failure cleanup; exact resulting `0700`; and archive/sidecar success (`tests/test_manifest_package.py:373-437`). An independent focused run of those cases plus the leaf-owner test passed 4/4. Separate non-root probes under `0700` and `0777` produced exact `0700` parents with archive and sidecar present; injected binding failure removed the full nested chain and left the `/proc/self/fd` count unchanged.

## Regression assessment

### Prior Important findings remain closed

- **Sidecar hardlink/FIFO/symlink/directory authority:** final checksum names are inspected without following or opening. Checksum bytes are written through a separate `O_EXCL | O_NOFOLLOW` held regular fd, name/inode-validated, atomically replaced relative to the held parent, and postvalidated (`scripts/package_stack.py:283-367`, `:396-464`). Hardlink sentinel, bounded FIFO, symlink sentinel, directory preflight, regular-mode, sidecar-swap, and cleanup tests remain present (`tests/test_manifest_package.py:202-371`).
- **Ancestor and final-parent authority:** requested and canonical chains reject foreign ownership and non-sticky shared rename authority; sticky `/tmp` is accepted only for an effective-UID-owned child. The final directory is opened no-follow once, checked for exact effective-UID ownership/private mode, and retained for all output operations (`scripts/package_stack.py:63-100`, `:206-256`). The corrected leaf-owner regression injects only the held directory's `fstat` owner and proves the final predicate plus fd cleanup, rather than exiting at ancestor validation (`tests/test_manifest_package.py:457-487`).
- **Temporary/output identity and modes:** archive and checksum construction retain exclusive fds through hashing/publication. Temporary and published names must match held device/inode; detected mismatches are removed dirfd-relative and cannot return success (`scripts/package_stack.py:259-464`, `:467-525`). New archive mode remains kernel `0666 & ~umask`; existing regular archive and checksum modes remain preserved.
- **Source containment and boundedness:** regular-only enumeration, root-relative no-follow source opens, identity/digest comparison, bounded source/ZIP/checksum streaming, source-manifest invariance, symlink-root legacy helpers, and controlled post-open cleanup remain unchanged in `.grok-stack/adaptive_grok/manifest.py` and their existing regressions.
- **Exact Git trust:** repository Git commands still receive exactly one canonical command-scoped `safe.directory`; isolated global/system configuration remains disabled, `diff --no-index` receives no repository trust, and the receipt clone keeps its exact temporary `ROOT/.git` config. No wildcard or persistent trust was introduced.

### Portability and error paths

- Linux-only `O_PATH` is resolved lazily in `_path_directory_flags`; absence raises controlled `PackageError` only when secure missing-parent creation needs it (`scripts/package_stack.py:41-45`). Existing-parent packaging continues to use the existing lazy directory/temporary capabilities.
- `mkdir`, bind/stat/chmod/open/fchmod failures are caught inside the creation transaction, created names are cleaned in reverse order, and descriptors are closed in the nested `finally` plus outer `finally` paths (`scripts/package_stack.py:140-203`). Later binding failures enter the same created-parent cleanup from `write_archive` (`:475-528`). No product code calls `os.umask`.
- Existing temporary cleanup still attempts close and unlink independently and attaches cleanup errors without replacing the primary exception (`scripts/package_stack.py:354-367`, `:420-423`, `:518-521`).
- The actual diff remains empty under `trust-ci/**` and `.github/workflows/**`; `git diff --check` is clean.

## Findings

### Critical

None.

### Important

None.

### Minor

#### M8 — Architecture narrative retains the previous headroom value

`engineering/changes/20260829-m2-trust-ci-read-only-workspace-compatibility-818501/architecture.md:65` says the final finite rule leaves 78 lines of headroom. The current measured/limit pair is 10,739/10,820, so the value is 81; the typed spec and brief correctly state 81 (`change-spec.yaml:125-126`, `brief.md:51`). Update the narrative literal to avoid two current budget identities.

#### M9 — The P0 test matrix points to two removed test names and the old umask range

`engineering/changes/20260829-m2-trust-ci-read-only-workspace-compatibility-818501/test-plan.md:18-19` still names `test_archive_rejects_output_parent_not_owned_by_effective_uid` and `test_missing_default_output_parent_is_private_under_common_umasks`; neither method exists after remediation-5. The actual oracles are `test_open_output_directory_rejects_foreign_leaf_owner_and_closes_fd` and `test_missing_default_output_parent_is_private_under_restrictive_umasks`, with the latter now covering `0002`, `0022`, `0700`, and `0777` (`tests/test_manifest_package.py:373-390`, `:457-487`). Refresh the table so the durable evidence map remains executable and accurately describes the stronger coverage.

## Commands and evidence

- Read the active route and required skills, all historical code/security/test findings, remediation-5 package/docs, full actual diff, and surrounding implementation/tests.
- `git rev-parse HEAD`, `git status --short`, `git diff --stat HEAD`, `git diff --check HEAD`, protected-path scan, and independent tree-fingerprint calculation.
- Four focused remediation-5 regressions -> 4/4 PASS in 0.018 s.
- Independent temporary-directory probes under umasks `0700` and `0777` -> exact parent `0700`, archive and sidecar present; injected post-creation binding failure -> complete nested cleanup and stable fd count.
- `python3 scripts/grok_architecture.py summary --json` -> canonical composite `d2f31484721c02d7ae0dcd2faa8519a6d20cb23da10de7378ed02fd1a293061b`, rules `2d42ca7373cebd4bf954bcfe1bdb784688df8665d08c4dce2b13de536abee69e`, matching frozen handoff literals.
- Worktree architecture fitness against adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8` -> overall PASS and code-budget PASS under finite 10,820.
- Broad suites and the stale remediation-3 pinned run were not rerun. The supplied current 39/39 and static results were inspected as claims against their implementation/test oracles.

## Evidence boundary

This report is bound to the supplied pre-report fingerprint, preserves all historical reports, changes no application code, and authorizes no push, merge, release, deployment, or external operation.
