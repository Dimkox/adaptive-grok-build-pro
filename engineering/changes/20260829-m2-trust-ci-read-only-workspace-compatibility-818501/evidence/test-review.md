# Independent test review

## Verdict

**PASS** — no Critical or Important test defect was found. The current implementation and the exact pinned-runner result cover the read-only/different-owner regression. Two Minor oracle-strengthening opportunities are recorded below.

## Reviewed identity

- Route: `81850148d1f6`
- Git HEAD before and after review checks: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Expected preflight tree fingerprint: `58854a896966d3ec160697d61ca4e1dded628eddc028ef994a032d5a135483c7`
- Independently calculated fingerprint before and after focused checks: `58854a896966d3ec160697d61ca4e1dded628eddc028ef994a032d5a135483c7`
- Reviewed tracked diff: 11 files, 119 insertions and 23 deletions. `git diff -- trust-ci` was empty.
- Parent-supplied pinned read-only runner result bound to this preflight fingerprint: **378/378 PASS**. This review did not rerun that broad suite.

## RED to GREEN assessment

### Different-owner repository Git

`test_repo_git_commands_trust_only_the_exact_root_under_different_owner` is a real-Git regression, not a mocked success: it enables Git's `GIT_TEST_ASSUME_DIFFERENT_OWNER=1`, runs both exact-commit and worktree architecture diffs, and captures the commands while delegating to the real bounded subprocess runner. It fails against the former implementation because the isolated Git environment discards external trust; it passes with `-c safe.directory=<resolved repository>` on repository operations. Inspection confirms `_git()` resolves the root strictly, uses that same canonical path for `cwd` and command-scoped trust, and `_line_stats()` retains the isolated non-repository `git diff --no-index` path without repository trust.

### Manifest invariance and deterministic streaming archive

`test_write_archive_preserves_source_manifest_and_embeds_current_bytes` is a meaningful regression: a stale sentinel source manifest must survive byte-for-byte, while the ZIP member must contain freshly rendered checksums. It fails against the former generate-then-unlink implementation. The existing deterministic test executes two archive builds and compares both returned digests and complete ZIP bytes; existing mode, exclusion, self-verification, sidecar, and packaged-installer tests remain in the passing pinned suite. Inspection confirms source files are copied into ZIP members through `source.open('rb')` and `shutil.copyfileobj(..., length=1 MiB)` and source `MANIFEST.sha256` is never written or removed. The pinned `/workspace:ro` run plus Trust CI's post-command `assert_unchanged()` supplies the full-tree mutation oracle that the focused sentinel test intentionally narrows.

### `git clone --no-local` child upload-pack

The receipt integration test keeps the real `git clone --no-local`. It creates its config beneath the enclosing `TemporaryDirectory`, disables system and host-global config while creating it, writes exactly `safe.directory=<ROOT/.git>`, and exposes that config only through the clone process environment so the child upload-pack inherits it. The temporary config is removed with the fixture directory. The focused test passes locally, while the supplied pinned different-owner run is the decisive positive oracle for the child-process ownership boundary; deleting this setup reproduces the documented pinned failure even though a same-owner developer checkout alone cannot.

### Architecture budget and digest contracts

An independent worktree evaluation selected frozen adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8`, measured exactly `10043` changed lines for the governed prefixes, loaded `max_changed_lines=10100`, calculated exactly 57 lines of headroom, and returned both `code_budget=pass` and overall fitness `pass`. The frozen M2 handoff digest test independently passed after the rules and composite digests were refreshed. Generic negative budget tests still establish failure when byte, line, or AST limits are exceeded.

### Pinned runner contract

Inspection of the unchanged runner shows UID/GID `10001:10001`, container `--read-only`, explicit `/workspace:ro` and `/workspace/.git:ro` mounts, exact `safe.directory=/workspace`, isolated writable temp/cache locations, and the post-command workspace mutation check. Focused runner-contract tests for the mount/trust argv and exact tool pins both passed. No deployed Trust CI source changed in this patch.

## Findings, ranked

### Minor — Streaming is verified by inspection, not a dedicated anti-buffering oracle

The deterministic archive test would still pass if a future implementation replaced source streaming with whole-file buffering. The current implementation is correct, so this does not block the change. A future regression test could wrap a large source file or instrument source reads to reject unbounded `read_bytes()` while allowing the archive-output checksum read.

### Minor — Exact trust test does not assert uniqueness or the no-index negative explicitly

The different-owner test requires the canonical trust value and rejects `safe.directory=*`, but an additional non-wildcard trust entry would not fail its current assertions; it also filters temporary no-index commands instead of asserting that they contain no `safe.directory`. Current code inspection shows exactly one canonical repository entry and none for no-index, so there is no present defect. Counting `safe.directory=` argv entries and asserting zero on captured no-index commands would make the security oracle sharper.

## Commands and results

- Fingerprint calculation with `tree_fingerprint(Path.cwd())`: exact expected digest before and after focused checks.
- Five changed/adjacent regressions (different-owner Git, manifest preservation, deterministic ZIP, child-clone receipt, pre-adoption budget binding): `Ran 5 tests in 14.695s` — `OK`.
- Direct architecture worktree probe: `changed_lines=10043`, `max_changed_lines=10100`, `headroom=57`, `code_budget_status=pass`, `fitness_status=pass`.
- Frozen handoff digest contract: `Ran 1 test in 0.142s` — `OK`.
- Unchanged pinned-runner contract tests (read-only mount/trust argv and exact tool pins): `Ran 2 tests in 0.003s` — `OK`.

## Evidence limitation

The 378/378 pinned result and its binding to the supplied preflight fingerprint were provided as review input; no raw runner transcript or signed external attestation was present in this uncommitted change package. Accordingly, this report validates the code/test contract and exact local fingerprint but does not elevate local or supplied runner evidence into merge authority. The App-owned exact-PR-SHA Trust CI check and required external approvals remain separate.
