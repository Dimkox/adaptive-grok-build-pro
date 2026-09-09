# Independent code re-review 4

## Identity, scope, and verdict

- Route: `81850148d1f6`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- Reviewed HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Frozen implementation/evidence fingerprint independently matched before this report was written: `2c217ae3d8401e188657ac916cf3dfc931f4f1c9b90413cc4445ef908a1bcac2`
- Scope: complete actual diff from HEAD, surrounding implementation/tests, all historical code reports, remediation-4 package/docs, the prior security/test findings that overlap the output boundary, and current focused evidence.
- Current supplied evidence: 37/37 focused tests PASS plus Ruff, Bandit, and diff-check PASS. The remediation-3 disposable pinned result (391/391 at `c749343d535fe2d0d02ee6cf770b781e91c827c7`) is historical and stale for this remediation-4 product/test tree, as the package correctly records.
- **Verdict: FAIL** — zero Critical, one Important, and zero new Minor findings. The sidecar defect and both prior Minor findings are closed, but missing-parent creation still violates the approved umask-independent `0700` contract and can self-reject the documented default command.

Local tests/reviews are not merge authority. A repaired tree still needs fresh exact-tree verification/reviews and the App-owned policy-epoch check plus required external approvals on the exact pull-request SHA.

## Prior finding verdicts

### I6 — Sidecar publication follows hardlinks and can block on FIFO: ADDRESSED

`_write_sidecar` no longer opens the final checksum name. It inspects the name without following it, allocates a distinct random sibling with `O_EXCL | O_NOFOLLOW | O_CLOEXEC`, writes through the retained fd, verifies both fd and name identity, replaces relative to the held output-parent fd, and verifies the published inode (`scripts/package_stack.py:220-250`, `:262-304`, `:333-401`). A directory sidecar is preflight-rejected before archive allocation/publication (`:363-378`, `:412-416`); symlink, FIFO, and other non-directory entries are replaced without opening, while an existing regular entry supplies only its mode.

The regressions are meaningful: the hardlink target remains byte-identical and loses alias identity, FIFO completion is subprocess-bounded, a symlink target is unchanged, directories leave no archive, regular-sidecar mode and exact payload are preserved, and a swapped sidecar temp fails without target mutation or temp leakage (`tests/test_manifest_package.py:202-332`). This closes the former external overwrite and liveness blocker.

### I7 — Missing output parent can be created with a self-rejected mode: NOT ADDRESSED

The common-umask symptom is repaired, but the approved invariant is broader and the implementation still inherits restrictive umask bits. This remains the sole Important finding below.

### M6 — Active brief publishes the previous budget identity: ADDRESSED

The active brief now states measured 10,672 lines, finite ceiling 10,750, and 78 lines of headroom at both former stale locations (`engineering/changes/20260829-m2-trust-ci-read-only-workspace-compatibility-818501/brief.md:29`, `:51`). The typed spec, requirements, architecture, tasks, rules, and frozen M2 handoff agree. Independent canonical summary output matched composite digest `ed04f439165ff408911971845c28a7c7199382d379db31debd6642a36723ab54` and rules digest `f3d8253a04d7eaab8955c6c488ab6d74a0be5cade3f6c88966cbb9931604fcbc`; worktree fitness returned PASS under the 10,750 ceiling.

### M7 — A close error can prevent temporary-name cleanup and mask the primary failure: ADDRESSED

`_cleanup_temporary` independently attempts close and dirfd-relative unlink and returns both cleanup errors without replacing the primary exception (`scripts/package_stack.py:291-304`). Both archive and sidecar exception paths attach cleanup failures as notes and re-raise the original failure (`:357-360`, `:454-457`). The injected regression closes the wrapped fd, raises from close, preserves the primary publication error, records the close note, and proves no output or temp remains (`tests/test_manifest_package.py:334-371`).

## Strengths and regression assessment

- The remediation addresses the overlapping security/test ancestor finding rather than adding another racy final `stat`: requested and canonical chains reject foreign ownership and non-sticky shared rename authority, accept a root-owned sticky `/tmp` only for an effective-UID-owned child, and retain the final effective-UID-owned private directory fd for all output operations (`scripts/package_stack.py:56-94`, `:143-193`; `tests/test_manifest_package.py:171-200`, `:411-452`). Under the explicit same-UID/privileged exception, late relocation is no longer available to an untrusted actor.
- Archive and checksum publication each use separate exclusive held regular fds. Temporary creation, mode application, digesting, replacement, post-publication identity checks, mismatch removal, and cleanup are parent-dirfd-relative and never reopen produced content by authority name (`scripts/package_stack.py:196-401`, `:404-461`).
- Existing archives retain regular-file mode; absent archives still use kernel `0666 & ~umask`. Existing regular sidecars retain mode, while hardlink/symlink/FIFO names are safely replaced. Source snapshot/stream identity, bounded hashing, deterministic ZIP content, and source-manifest invariance are unchanged.
- POSIX-only descriptor flags remain lazy and fail controlled on the secure path; explicit manifest rendering/generation/verification remains usable without importing those capabilities. Exact architecture Git trust remains one canonical command-scoped `safe.directory` for repository operations and absent from `diff --no-index`.
- The actual diff remains empty under `trust-ci/**` and `.github/workflows/**`; `git diff --check` is clean.

## Findings

### Critical

None.

### Important

#### I8 — Missing parents are not actually created `0700` independently of ambient umask

**Evidence:** `_ensure_output_parent` calls `path.mkdir(mode=0o700)` and immediately validates only that no group/world permission bits are present (`scripts/package_stack.py:96-140`, especially `:122-131`). POSIX applies the process umask to `mkdir`'s requested mode. The committed regression covers only `0002` and `0022`, which do not remove the owner `rwx` bits (`tests/test_manifest_package.py:373-390`). In contrast, the typed explanatory contract requires missing components to be `0700` independent of ambient umask (`requirements.md:24`), and README advertises the same behavior for the default `dist/` command (`README.md:368-371`).

A focused non-root probe used one absent default-style parent under umask `0777`. `write_archive` failed with `PackageError: cannot bind archive output directory safely` and left the newly created parent behind at mode `0000`; no archive was produced. With two missing components, creation failed while descending and cleaned the partial chain, so behavior also varies with missing depth. Thus the former self-rejection defect still exists for a valid ambient umask, and the final mode is not the promised `0700`.

**Rationale:** This is a real compatibility and contract failure in the documented default path, not merely a cosmetic permission difference. It also leaves caller-owned residue on the single-component failure path because `_ensure_output_parent` has already returned before `_open_output_directory` fails. The current 37-test evidence cannot establish the declared umask-independent invariant because its two masks leave owner permissions unchanged.

**Required fix:** Establish exact `0700` on each directory created by this operation without mutating a pre-existing component or using a process-global umask window. Prefer opening each just-created component no-follow, proving its created identity/ownership, applying `fchmod(0700)` on that held descriptor before descent, and retaining cleanup ownership; then revalidate the final binding. Add restrictive masks such as `0700`/`0777` for one and multiple missing components and assert exact mode, successful archive/sidecar publication, and no residue on injected open/validation failure.

### Minor

None newly identified. The two prior Minor findings are addressed above.

## Commands and evidence

- Read the active route and required skills, all historical code reports, overlapping security/test rereview-3 reports, remediation-4 durable package, full actual diff, and surrounding source/tests.
- `git rev-parse HEAD`, `git status --short`, `git diff --stat HEAD`, `git diff --check HEAD`, protected-path scan, and independent tree-fingerprint calculation.
- `python3 scripts/grok_architecture.py summary --json` -> canonical current digests matched the frozen handoff.
- `python3 scripts/grok_architecture.py fitness --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --worktree --pre-risk red --json` -> overall and code-budget status PASS.
- Focused restrictive-umask probes used only temporary directories: nested missing components under `0777` failed and cleaned the partial chain; one missing parent under `0777` failed, remained mode `0000`, and had no archive.
- Broad suites and the stale remediation-3 pinned run were not rerun. The supplied current 37/37 focused result and static checks were treated as claims and checked against the named implementation/test oracles.

## Evidence boundary

This report is bound to the supplied pre-report fingerprint, preserves historical reports, changes no application code, and authorizes no push, merge, release, deployment, or external operation.
