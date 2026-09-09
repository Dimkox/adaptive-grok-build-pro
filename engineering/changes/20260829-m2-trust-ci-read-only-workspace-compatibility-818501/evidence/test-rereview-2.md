# Independent test re-review 2

## Verdict

**FAIL** — one Important test/behavior gap remains in temporary archive publication. No Critical findings. All other requested remediation regressions pass and their oracles are meaningful.

## Exact reviewed identity

- Route: `81850148d1f6`
- Git HEAD before and after focused checks: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Expected worktree fingerprint: `451c81e02e7e8bcf234e53a5a397c272d30d5309fa78296d84383adb626fa5db`
- Independently calculated fingerprint before and after focused checks: `451c81e02e7e8bcf234e53a5a397c272d30d5309fa78296d84383adb626fa5db`
- Actual tracked diff: 11 files, 562 insertions and 34 deletions; `git diff --check` passes and `git diff -- trust-ci` is empty.
- Supplied pinned evidence: **386/386 PASS** in 234.638 s under the recorded digest-pinned runner, UID/GID `10001:10001`, `/workspace:ro`, `/workspace/.git:ro`, and network disabled. The persisted local evidence names disposable exact-tree commit `3a973b6a8194e752a9ea8d7137a1d7856f76776d`; it remains local evidence, not merge authority.

## Findings by severity

### Critical

None.

### Important

#### I1 — The temp-swap regression misses the final validation-to-rename race, which still publishes a mismatched inode

`test_archive_temp_path_swap_fails_without_touching_external_target` swaps the temporary pathname immediately after `_create_temporary_archive()`. That is a valuable regression: ZIP writes remain bound to the held descriptor, the external sentinel is unchanged, validation rejects the symlink, and no output or temporary name remains.

However, production code performs these distinct operations after ZIP construction:

1. `_validate_temporary_name(temporary)` while the descriptor is open;
2. close the held descriptor;
3. `_validate_temporary_name(temporary)` again;
4. `os.replace(temporary.path, output)`.

The current test never swaps the pathname after step 3. A bounded deterministic probe wrapped `_validate_temporary_name`, delegated both calls to the real validator, and after the second successful validation replaced the sibling temp name with a symlink to an external sentinel. The unmodified writer then returned successfully with a digest, `output.is_symlink()` was true, and `output.resolve()` pointed at the external sentinel. The sentinel bytes were not overwritten, but the verified ZIP inode was discarded and a different filesystem object was published and hashed.

Observed probe result:

```text
returned_digest=True
output_is_symlink=True
output_target=<temporary external sentinel path>
external_unchanged=True
```

This contradicts AC-005 and the explicit failure contract that the temporary name must still resolve to the held regular inode at publication. It is Important because a same-UID process able to mutate the caller-selected output directory can substitute the released package identity after every asserted check; the successful return and sidecar then bless the substituted target rather than the archive bytes that were built and validated. The 386-test suite passes because it contains only the early-swap injection.

Required remediation: use a publication mechanism whose source identity is atomically bound to the held inode on the supported platform, or otherwise redesign the output-directory authority so no attacker-controlled pathname operation exists between validation and publication. Add a deterministic regression that swaps specifically after the final current validation and proves the writer cannot return success or publish a symlink/mismatched inode; retain assertions for external bytes, pre-existing output, sidecar, and temporary cleanup.

### Minor

None beyond I1. A generic `RuntimeError` assertion is acceptable here only when paired with precise postconditions; the current early-swap and source-replacement tests do supply those postconditions.

## Prior/new regression assessment

### Temporary pathname swap — PARTIALLY ADDRESSED

Holding the exclusive fd through ZIP construction closes the original close/reopen overwrite. The new test proves an early pathname swap cannot redirect writes or touch the external target. I1 shows the stronger “cannot publish a mismatched inode” claim and its late boundary remain uncovered and false.

### New and existing output modes — ADDRESSED

The controlled-umask new-output test obtains `0640` under umask `0027`, matching `0666 & ~umask`. The replacement test begins with mode `0664`, runs under umask `0077`, proves the resulting ZIP retains `0664`, and verifies ZIP integrity. These tests fail against the former `mkstemp`-mode publication and distinguish absent from existing output behavior.

### Post-open `fstat` cleanup — ADDRESSED

The failure-injection test covers root and final-file opens separately, requires normalized `ManifestError`, and compares `/proc/self/fd` counts before and after each injected `fstat` exception. Inspection confirms both new cleanup branches close the just-opened descriptor before raising.

### Symlink-root compatibility — ADDRESSED

The helper regression passes a real directory symlink, calls `included_files(alias)`, and compares returned canonical children relative to the canonical root. Sorting now consistently uses `canonical_root`, eliminating the prior raw `ValueError`. The CLI already resolves roots, while this test protects the directly imported helper contract.

### Source symlink and replacement races — ADDRESSED for the source boundary

The external-secret symlink test proves the link member and sentinel bytes are absent. The post-manifest replacement test mutates a real file before streaming, requires failure, proves replacement bytes remain, and proves no output is published. Descriptor-relative `O_NOFOLLOW`, identity comparison, streamed digest comparison, and temporary cleanup support these oracles. This source-boundary closure is separate from I1's output-publication race.

### Bounded archive checksum — ADDRESSED

The `StreamingChecksumPath` regression makes `read_bytes()` fail, verifies the returned digest against an independent streamed digest, and checks the exact sidecar. Current hashing reads fixed 1 MiB chunks.

### Exact scoped Git trust — ADDRESSED

The real different-owner regression requires exactly one `safe.directory=<canonical-root>` entry on every repository command and explicitly requires zero such entries on captured `git diff --no-index` commands. Exact-commit and worktree modes both execute through real Git under `GIT_TEST_ASSUME_DIFFERENT_OWNER=1`.

### Read-only manifest/clone compatibility — ADDRESSED

The source-manifest sentinel remains byte-identical while the ZIP receives current rendered bytes. Deterministic ZIP bytes/digests still match across two builds. The real `clone --no-local` receipt fixture continues to pass its exact temporary `ROOT/.git` config only to the clone/child upload-pack environment. These focused regressions pass alongside the supplied read-only pinned suite.

### Architecture budget and frozen digests — ADDRESSED

Independent worktree evaluation selected adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8`, measured exactly `10311` governed changed lines, loaded finite `max_changed_lines=10400`, calculated 89 lines of headroom, and returned both `code_budget=pass` and overall fitness `pass`. Canonical summary and the frozen handoff test agree on rules digest `74e35563bb95cfde614c7ff50ef332e070a77993b0656cd6fa67034c2ab6889d` and composite architecture digest `cfbc609f31dffeb4703292b8215f45987b55f31e4e092b708ec6cb94137ce204`; unchanged system/schema/inventory digests also match.

## Independent checks

- Fourteen focused regressions covering symlink-root, `fstat` cleanup, early temp swap, both output-mode cases, external source symlink, source replacement, bounded checksum, source-manifest invariance, deterministic ZIP, exact Git trust, child clone, budget binding, and frozen digests: `Ran 14 tests in 14.987s` — `OK`.
- Late temp-name swap probe after the second real validation: reproduced successful mismatched symlink publication as documented in I1.
- Architecture probe: `10311/10400`, headroom 89, code budget PASS, overall fitness PASS.
- Canonical architecture summary: exact refreshed rules/composite digests.
- Final pre-report HEAD/fingerprint and `git diff --check`: unchanged/exact and clean.

## Evidence boundary

The pinned 386/386 result is a strong exact-tree read-only compatibility check, but it cannot close an adversarial path absent from its tests. This report is local independent review evidence only; it does not replace the App-owned exact-PR-SHA Trust CI check or the required external architecture, governance, and security approvals.
