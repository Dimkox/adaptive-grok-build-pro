# Final exact-head test review — read-only Trust CI sandbox remediation

## Verdict

**PASS**

The complete package test module passes in a recursively non-writable detached checkout at exact product HEAD `b2126d1b23507a802ed00b860f58102a6b1d8612`. Both tests that previously packaged from the source root now use the same canonical writable staging helper. No Critical or Important test gap remains.

Only a new App-owned external check on the exact current PR SHA can authoritatively close the prior external root-unittest failure. This local PASS does not substitute for that check.

## Exact inspected identity

- Product HEAD: `b2126d1b23507a802ed00b860f58102a6b1d8612`.
- Parent: `5f48cfe8cdee104053d406de523c60690cec791d`.
- Product tree was clean before route-selected review evidence updates.
- Fresh verification receipt fingerprint: `4c63e1f67dc3fb4b906930afb419b2fce07e72eeed3fe1441276dcf90c2231ae`.
- Receipt: `.grok-stack/runtime/receipts/befa117340b9/verification.json`, created `2026-08-31T11:26:38+00:00`, status `pass`, bound to the same exact HEAD.
- Combined pre-test-report fingerprint after the final code-review append: `c43880c222bdde2c16b37b32ac692d5d50beaf330fca5cbb0582815149ac7703`.
- Replacing this report is this reviewer's only subsequent repository mutation.

## Remediation assessment

The prior external runner mounts exact source as read-only `/workspace`. Earlier remediation fixed the investor-artifact test but left `test_packaged_installer_materializes_new_target_without_authority` calling `PACKAGE.write_archive(ROOT, ...)`, which still attempted to create `/workspace/MANIFEST.sha256`.

The final code centralizes `PackageTests._stage_package_source(parent)`. It:

1. enumerates the canonical `included_files(ROOT)` inventory;
2. proves the only runtime member is `.grok-stack/runtime/.gitkeep`;
3. copies every included file into a writable temporary source root;
4. proves the staged inventory exactly equals the canonical source inventory;
5. rejects `.git` and `dist` in staging;
6. returns staging for the real production archive writer.

Both ROOT-derived packaging tests now call `PACKAGE.write_archive(staging_root, archive_path)`. Manifest generation, archive output, checksum output, and cleanup therefore occur only in writable temporary storage. Production packaging code is unchanged.

## Independent read-only detached reproduction

A fresh Git worktree was created detached at exact HEAD `b2126d1b23507a802ed00b860f58102a6b1d8612`. The checkout was made recursively non-writable with no writable source path. A separate sibling `TMPDIR` was confirmed writable.

Preconditions:

- no checkout `dist/`;
- no checkout `MANIFEST.sha256`;
- no writable file/directory under the checkout;
- empty Git status.

### Both affected tests

`python3 -m unittest tests.test_manifest_package.PackageTests.test_investor_demo_local_release_artifact_is_complete_and_checksum_bound tests.test_manifest_package.PackageTests.test_packaged_installer_materializes_new_target_without_authority -v`

- Result: **2/2 passed**, 4.380 seconds, `OK`.

### Complete package module

`python3 -m unittest tests.test_manifest_package -v`

- Result: **14/14 passed**, 5.403 seconds, `OK`.
- Covers deterministic/self-verifying archives, installer materialization, investor artifact inventory/checksum, secret/key/log/runtime exclusions, generated-artifact exclusion, and no GitHub Actions.

Postconditions after both runs:

- checkout still had no `dist/`;
- checkout still had no `MANIFEST.sha256`;
- checkout remained recursively non-writable;
- Git status remained empty;
- external staging remained writable and contained no leftover test entries.

The temporary checkout permissions were restored only for cleanup, and the detached worktree/staging parent were removed successfully.

## Full verification receipt

The exact-head receipt records PASS for:

- git diff check;
- typed change spec;
- architecture drift, fitness, and diagrams;
- governance;
- secret scan;
- contract structure;
- SQL safety;
- Ruff;
- Bandit;
- Python unit suite: **480 tests passed**, 450.557 seconds;
- coverage: **80%** total;
- source stability.

## Rebuilt local ZIP

- Archive: `dist/adaptive-grok-build-pro-v2.1.0.zip`.
- SHA-256: `9e9deb97b9cb487a6c400ed7b156e1f8ff561e134e2cf9b5f86e11af7a652b6d`.
- Adjacent checksum validation: PASS.
- ZIP integrity: PASS.
- Packaged `tests/test_manifest_package.py` exactly matches current HEAD and contains the shared staging helper, both staging-root archive calls, and the exact runtime inventory assertion.
- The source root had no `MANIFEST.sha256` after archive inspection.

## Severity-classified findings

### Critical

None.

### Important

None.

### Minor / pending external evidence

1. Repository-local reproduction cannot authoritatively change the status of the previous external failure. PR #15 requires a new App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run on its exact final head and any required signed approvals.
2. The verified ZIP is a local gitignored artifact; its checksum does not claim GitHub Release publication or deployment.

## Completion assessment

The read-only sandbox fixture defect is locally closed at exact HEAD: both affected tests and the entire package module pass with source recursively non-writable, staging writable, and no source manifest/dist/Git mutation. Final merge eligibility remains pending the new exact-SHA external Trust CI result and separate human/operator gates.
