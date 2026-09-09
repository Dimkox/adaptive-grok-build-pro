# Independent test re-review after remediation

## Verdict

**PASS** — zero Critical, Important, or Minor test findings. The remediation closes both findings from `test-review.md` and supplies meaningful regressions for the packaging defects raised by the independent code/security reviews.

## Exact reviewed identity

- Route: `81850148d1f6`
- Git HEAD before and after focused review checks: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Expected pre-review fingerprint: `804a90cecef93cc96ddaddf6cedf64a7b0d8edc866d5cee52953b0837d757696`
- Independently calculated fingerprint before and after focused review checks: `804a90cecef93cc96ddaddf6cedf64a7b0d8edc866d5cee52953b0837d757696`
- Actual tracked diff: 11 files, 372 insertions and 33 deletions; `git diff -- trust-ci` is empty and `git diff --check` passes.
- Supplied exact-fingerprint evidence: pinned read-only runner **381/381 PASS** and `grok_verify` preflight **PASS**. These broad checks were not duplicated in this re-review.

## Prior findings

### Prior Minor: no dedicated anti-buffering checksum oracle — ADDRESSED

`test_archive_checksum_streams_without_output_read_bytes` passes a real `Path` subclass whose `read_bytes()` raises. The archive is produced successfully, the returned digest equals an independently streamed digest, and the sidecar remains exact. This test fails against the prior whole-ZIP `output.read_bytes()` implementation. Current `sha256()` reads through fixed 1 MiB chunks, so both the regression oracle and inspected implementation support the bounded-memory claim.

### Prior Minor: exact Git trust uniqueness/no-index negative missing — ADDRESSED

The real-Git different-owner test now asserts the complete `safe.directory=` argument list for every repository command equals exactly one canonical-root entry. It separately requires captured `--no-index` commands and asserts they contain no trust entry. It still executes exact-commit and worktree paths under `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` through the real bounded process runner.

## Remediation coverage

### External symlink exclusion

`test_archive_excludes_external_secret_symlink` creates a benign-named source symlink to an external `.env` sentinel, executes the real package writer, and proves both that the link member is absent and the sentinel is not any archived member. This is a direct GREEN for the former disclosure probe. Inspection confirms enumeration uses `lstat()` and admits only regular files; subsequent opens are root-descriptor-relative with `O_NOFOLLOW` on every parent and the file.

### Hash-to-stream replacement race

`test_archive_fails_closed_when_file_is_replaced_after_manifest_render` replaces a real file after its manifest snapshot but before ZIP streaming. The real writer raises, preserves the replacement bytes, and leaves no published output archive. This distinguishes fail-closed behavior from silently producing mismatched manifest/member bytes. Inspection confirms the stream reopen compares device, inode, mode, size, mtime, and ctime to the hashed snapshot, rehashes the streamed bytes, checks post-stream identity, builds into an output-directory temporary file, and deletes that temporary on failure before `os.replace()` publication.

### Existing read-only and deterministic contracts

The source-manifest sentinel remains byte-identical while the archive receives freshly rendered checksum bytes. Two builds still produce identical archive bytes and digests, and existing packaged-installer/mode/exclusion/sidecar cases remain covered by the supplied 381-test pinned run. The real `git clone --no-local` receipt test still supplies only its temporary exact `ROOT/.git` trust config to the child upload-pack environment and passes alongside the architecture staleness binding.

### Architecture budget and digest contracts

An independent worktree evaluation selected frozen adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8`, measured exactly `10228` governed changed lines, loaded the finite `max_changed_lines=10300`, calculated 72 lines of headroom, and returned `code_budget=pass` plus overall fitness `pass`. The canonical summary reports rules digest `d5156f3d6e2413b466cc06e6554fd39692b9e9fb3ef0f62eef72fadc96223901` and composite architecture digest `ee458c0ab162009c38ede77a723a87f25082776ff74a64f0f2811feabcee9436`; the frozen handoff digest regression passes with those exact values.

## Ranked findings

- Critical: none.
- Important: none.
- Minor: none.

The replacement regression uses the public `RuntimeError` superclass rather than coupling to an internal exception type, but its mutation injection, no-output assertion, and surrounding normal-success tests make a false pass implausible and this is not a finding.

## Independent commands and results

- Nine focused remediation/existing regressions: `Ran 9 tests in 14.789s` — `OK`.
- Exact worktree budget probe: `changed_lines=10228`, `max_changed_lines=10300`, `headroom=72`, `code_budget_status=pass`, `fitness_status=pass`.
- `python3 scripts/grok_architecture.py summary --json`: exact refreshed rules/composite digests above; unchanged system/schema/inventory digests remain canonical.
- `git diff --check`: exit 0.
- Final pre-report HEAD/fingerprint check: unchanged and exact.

## Evidence boundary

The pinned 381/381 run and `grok_verify` PASS were supplied as coordinator-owned exact-fingerprint evidence; no raw runner transcript or signed external attestation is stored in this uncommitted package. This report independently validates the changed tests, implementation oracles, local identity, budget, and digests. It is not merge authority and does not replace the App-owned exact-PR-SHA Trust CI check or required external architecture/governance/security approvals.
