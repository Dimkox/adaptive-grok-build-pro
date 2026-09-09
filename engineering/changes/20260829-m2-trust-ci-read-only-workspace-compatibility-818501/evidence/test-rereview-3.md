# Independent test re-review 3

## Verdict

**FAIL** — zero Critical, four Important, and one Minor finding. The prior temporary-file, capability, symlink-root, source-integrity, hashing, mode, Git-trust, budget, and digest findings are covered and green, but the output-parent/sidecar matrix still has material false-green paths.

## Exact reviewed identity

- Route: `81850148d1f6`
- Git HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Supplied frozen implementation/evidence fingerprint: `6d02ed6871caf130d120f9f01097725a4f4da50ffc4dac9f8b39c78c938a2f5c`
- Independently calculated fingerprint at review start: exact match, `6d02ed6871caf130d120f9f01097725a4f4da50ffc4dac9f8b39c78c938a2f5c`.
- Actual tracked diff at review start: 11 files, 887 insertions and 36 deletions; `git diff --check` passed and `git diff -- trust-ci` was empty.
- While this review was running, other route reviewers added `code-rereview-3.md` and `security-rereview-3.md`; those evidence-only writes changed the aggregate tree fingerprint but did not change HEAD or the tracked implementation diff reviewed here.
- Fresh pinned evidence inspected: disposable exact-tree commit `c749343d535fe2d0d02ee6cf770b781e91c827c7`, **391/391 PASS** in 227.409 s under the recorded digest-pinned non-root, read-only, no-network runner contract.

## Findings by severity

### Critical

None.

### Important

#### I1 — Parent relocation is tested only before the final binding check; a late relocation returns success at the wrong path

`test_archive_parent_relocation_fails_without_redirecting_or_leaking_temp` relocates the parent immediately after temporary creation. The next `_validate_output_directory_binding()` detects this, and the test meaningfully proves that both the replacement requested directory and relocated held directory are clean.

There are three binding checks in a normal write. No test relocates the requested parent after the third/final successful check. An independent deterministic probe delegated all checks to the real validator, renamed the parent immediately after check 3, and observed:

```text
binding_checks=3
returned_success=True
requested_output_exists=False
relocated_output_exists=True
relocated_sidecar_exists=True
```

The held dirfd correctly prevents redirection outside the relocated inode, but the function reports success even though consumers at the requested output path have neither archive nor sidecar. With a writable non-sticky ancestor, relocation can be performed by a different UID, which is outside the typed exception for same-UID/privileged mutation inside the private parent. The 391-test suite therefore does not prove the full “relocated/rebound requested parent fails” contract.

Required remediation: enforce or explicitly constrain ancestor rename authority, then add a deterministic regression that relocates/rebinds after the final current binding check and requires no success, no requested/relocated output or sidecar, and no temporary artifact.

#### I2 — Missing-parent creation is untested and breaks the default command under common umask `0002`

Every committed package test writes to an already existing private `TemporaryDirectory` or creates its own private child. None exercises an absent final output parent. Production calls `output.parent.mkdir(parents=True, exist_ok=True)` with default mode and immediately rejects group/world-writable parents.

An independent probe under umask `0002` produced a new parent with mode `0775`, then returned `PackageError` and left that empty directory behind. This affects the documented default `dist/` path whenever it is absent in a collaborative-shell umask. The pinned runner does not expose the gap because test temporary parents already exist with private modes.

Required remediation: create only the missing final parent with an explicit private mode without chmod-mutating pre-existing parents, and add absent-parent/default-output regressions under at least umasks `0002` and `0022`, asserting mode, archive, sidecar, and no failure residue.

#### I3 — Sidecar safety has no adversarial regression; hardlinks overwrite external bytes and FIFOs can block

The suite checks exact normal sidecar text and proves that a detected archive-identity mismatch creates no sidecar. It never supplies a pre-existing sidecar symlink, hardlink, FIFO, directory, or other non-regular entry.

`_write_sidecar()` opens the existing name directly with `O_TRUNC | O_NOFOLLOW`. `O_NOFOLLOW` protects a symlink only; a hardlink is a regular inode and a FIFO can block during `os.open`. An independent hardlink sentinel probe returned success and changed the external sentinel through the shared inode. Independent bounded code-review evidence observed the FIFO path still blocked after one second with the archive already published.

The typed threat model trusts same-UID/privileged concurrent mutation *inside* a private parent, but this is also a pre-existing filesystem-state and packaging-liveness/compatibility problem; no current test states or enforces which pre-existing sidecar types are supported. The P1 claim that sidecar behavior remains stable is consequently too broad.

Required remediation: publish the sidecar through an exclusive held regular temporary fd and verified replace, or explicitly validate/reject unsupported pre-existing entries without opening them. Add symlink, hardlink, FIFO, directory, normal replacement, mode/format, failure-cleanup, and no-hang tests.

#### I4 — The effective-UID ownership half of the P0 parent predicate has no regression

AC-005 requires an effective-UID-owned, non-group/world-writable parent. `test_archive_rejects_group_or_world_writable_output_parent` exercises only modes `0770` and `0702`; no test supplies a foreign `st_uid`, changes `geteuid`, or creates a real different-owner output parent. The pinned runner creates output fixtures as UID 10001, so it also exercises only the matching-owner branch.

An independent probe patched only `geteuid` to disagree with the real parent metadata and confirmed current code raises `PackageError` with no entries. Current behavior is correct, but removing the `st_uid != effective_uid` predicate would leave all 391 tests green. This is an Important coverage gap because ownership is the enforcement premise used to narrow the final publication threat model.

Required remediation: add a deterministic owner-mismatch regression (injected stat/eUID is sufficient and portable for the unit layer) asserting controlled failure before temp/output/sidecar creation; retain the real mode negatives separately.

### Minor

#### M1 — `brief.md` still publishes the previous budget identity

The typed spec, requirements, architecture, rules, canonical summary, and live fitness use 10,502/10,600 with 98 lines of headroom. `brief.md` still states 10,311/10,400 with 89 lines at lines 29 and 51. The tests validate canonical digests but do not detect this stale explanatory identity.

## Confirmed regression coverage

### Late temporary-name swap — ADDRESSED within the approved private-parent model

The final-validation test injects after the second real temp-name validation, then requires an exception, exactly two validation calls, unchanged external sentinel, no output, no sidecar, and no temp. Current code hashes through the held archive fd, replaces relative to the held parent fd, validates the published device/inode, removes a mismatched entry, and fails before sidecar publication. This closes the prior test-review finding under the now-explicit same-UID/private-directory exception.

### Unsafe parent mode and early relocation cleanup — PARTIAL

Group- and world-write branches are real, negative, and assert no output/sidecar/temp. Early relocation asserts both the newly recreated requested path and relocated held directory are empty. I1 and I4 identify the missing late-relocation and ownership dimensions.

### No-leftover behavior — COVERED for tested failure points

Early/final temp swaps and unsafe-parent failures assert no publish artifacts; final swap explicitly checks output, sidecar, and temp. Parent relocation checks both directory locations. Source replacement asserts no output, and implementation inspection shows its pre-publication exception removes the held temp. The missing sidecar-type matrix in I3 remains the significant uncovered publication failure class.

### Output modes — ADDRESSED

The absent-output test proves `0640` under umask `0027`; the existing-output test begins at `0664`, runs under umask `0077`, verifies retained `0664`, and opens the result as a valid ZIP. I2 concerns missing parent creation, not archive inode mode.

### Descriptor cleanup and capability absence — ADDRESSED

Root/file post-open `fstat` failures require normalized `ManifestError` and unchanged `/proc/self/fd` counts. The capability test imports a fresh manifest module with `O_CLOEXEC`, `O_DIRECTORY`, and `O_NOFOLLOW` absent, proves explicit generate/verify still work, and proves secure snapshot fails controlled. Lazy flag resolution avoids the former import-time crash.

### Symlink-root helpers — ADDRESSED

Direct enumeration and end-to-end generate/verify each use a real directory symlink and pass against canonical-root path handling.

### Source symlink/replacement and bounded hashing — ADDRESSED

The external-secret symlink member and sentinel bytes are absent. A real post-render file replacement fails before output publication. Deterministic ZIP bytes/digests match across builds. `StreamingChecksumPath.read_bytes()` raises, while the returned checksum and sidecar match an independent streamed digest; source, member, and archive reads use bounded chunks.

### Exact scoped Git trust and child clone — ADDRESSED

The real different-owner test requires exactly one canonical `safe.directory` entry on every repository command and zero entries on captured `--no-index` commands. Exact and worktree paths execute under real Git with `GIT_TEST_ASSUME_DIFFERENT_OWNER=1`. The receipt fixture retains real `clone --no-local` and its isolated exact `ROOT/.git` child config.

### Architecture budget and canonical digests — ADDRESSED

Independent worktree evaluation selected adoption base `25bfbe59ea188d9687b20a9caad19e7db3d031f8`, measured exactly `10502` governed changed lines with no unknown line statistics, loaded finite `max_changed_lines=10600`, calculated 98 lines of headroom, and returned code-budget plus overall fitness PASS. Canonical summary and frozen handoff agree on rules digest `2a1e3da8b8c06d7d3f72536da92af2fc89084072cbd5228c7fd92b307975450d` and composite architecture digest `8210395a851d0b9ef7f9c5cdff5c583d5bfcbd0dba8d46605dcfc3fd92f02778`; unchanged system/schema/inventory digests also match.

## Independent checks

- Entire `tests.test_manifest_package` plus exact Git trust, both receipt/budget bindings, and frozen digest test: `Ran 29 tests in 17.146s` — `OK`.
- Foreign-owner predicate probe: controlled `PackageError`, no parent entries.
- Sidecar symlink probe: controlled `PackageError`, external sentinel unchanged, no temp; verified archive remains and no success is returned.
- Sidecar hardlink probe: function returned success and external sentinel bytes changed through the shared inode.
- Missing-parent probe under umask `0002`: controlled `PackageError`, created parent mode `0775`, empty directory remained.
- Late parent-relocation probe after binding check 3: function returned success; requested output absent; archive and sidecar existed only in relocated directory.
- Exact architecture probe: 10,502/10,600, headroom 98, zero unknown line stats, code-budget and overall fitness PASS.
- `git diff --check`: clean at the frozen implementation.

## Evidence boundary

The 391/391 disposable-commit pinned run is strong read-only compatibility evidence, but it cannot cover absent adversarial cases. This report is local review evidence only and does not replace the App-owned exact-PR-SHA Trust CI check or required external architecture, governance, and security approvals.
