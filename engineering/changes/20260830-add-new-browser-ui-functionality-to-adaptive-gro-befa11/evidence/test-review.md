# Final exact-head test review — Trust CI root-unittest remediation

## Verdict

**PASS**

The clean-checkout `root-unittest` failure is locally reproduced as fixed on exact product HEAD `8d8bd3e2119105af1510423cc85ba493c857f88f`. The focused failing test and the complete package module pass in a detached clean checkout with no `dist`, create no persistent root manifest, and leave the checkout clean. No Critical or Important gap remains in this remediation.

Only a new App-owned external check on the exact current PR SHA can authoritatively close the prior external failure. This local PASS does not substitute for that check.

## Exact inspected identity

- Product HEAD: `8d8bd3e2119105af1510423cc85ba493c857f88f`.
- Parent: `088ff0ec8877d4b9bda9fa81c3cd5c2476e5222d` (`test: build investor artifact in isolation`).
- Product tree was clean before this report replacement.
- Clean pre-report tree fingerprint: `0a706c272c40d57c82a23bc7938e957c3eb4d99d5f3186cd307409a766d75fd3`.
- Fresh full verification receipt: `.grok-stack/runtime/receipts/befa117340b9/verification.json`, created `2026-08-31T10:35:38+00:00`, status `pass`, bound to the same exact HEAD and fingerprint.
- This evidence report replacement is the reviewer's only source-tree mutation after fingerprint capture.

## Root cause and remediation assessment

The external clean runner lacked gitignored `dist/`, while the prior package test treated the local scratch ZIP and checksum as fixtures. The fixed `test_investor_demo_local_release_artifact_is_complete_and_checksum_bound` now:

1. creates a temporary directory;
2. builds the v2.1.0 archive through the real `PACKAGE.write_archive` path;
3. verifies both emitted ZIP and adjacent checksum;
4. compares the returned digest, checksum text, and independently computed SHA-256;
5. checks the required investor-MVP archive inventory;
6. asserts the repository root has no persistent `MANIFEST.sha256` afterward.

The remediation is test-only and preserves the production packager behavior. `mistakes.md` records the durable lesson that ignored artifacts must never be implicit clean-checkout fixtures.

## Detached clean-checkout reproduction

A new temporary Git worktree was created at exact detached HEAD `8d8bd3e2119105af1510423cc85ba493c857f88f`. Before testing:

- `dist/` did not exist;
- `MANIFEST.sha256` did not exist;
- `git status --porcelain=v1` was empty.

### Exact formerly failing test

`python3 -m unittest tests.test_manifest_package.PackageTests.test_investor_demo_local_release_artifact_is_complete_and_checksum_bound -v`

- Result: **1 test passed**, 1.151 seconds, `OK`.
- The test succeeded without any prebuilt `dist` artifact.

### Normal package suite

`python3 -m unittest tests.test_manifest_package -v`

- Result: **14 tests passed**, 3.466 seconds, `OK`.
- Covered deterministic/self-verifying archives, secret/key/log/runtime exclusions, installer materialization, no GitHub Actions, generated-artifact exclusion, local-demo inventory, and the isolated investor artifact test.

After both commands:

- `dist/` was still absent;
- root `MANIFEST.sha256` was absent;
- `git status --porcelain=v1` was empty.

The temporary detached worktree was then removed successfully. No persistent checkout or test fixture was left behind.

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
- Python unit suite: **480 tests passed**, 441.017 seconds;
- coverage: **80%** total;
- source stability.

The receipt is fingerprint-bound local evidence only. It is not the external App-owned policy-epoch result.

## Rebuilt local ZIP

- Archive: `dist/adaptive-grok-build-pro-v2.1.0.zip`.
- SHA-256: `b973c6c8353db427faa0127423df085175320f36a003ed0f389dee0a7f60b07b`.
- Adjacent checksum validation: PASS.
- ZIP integrity (`ZipFile.testzip()`): PASS.
- Direct inspection confirmed the archive includes the current `tests/test_manifest_package.py`, `scripts/package_stack.py`, v2.1.0 identity, manifest, bootstrap state, and investor-demo guide.
- The packaged remediation test bytes exactly match current HEAD and contain both temporary-directory construction and the no-root-manifest assertion.
- The source root had no `MANIFEST.sha256` after local artifact inspection.

## Severity-classified findings

### Critical

None.

### Important

None.

### Minor / pending external evidence

1. The prior external root-unittest failure cannot be marked authoritatively closed from repository-local evidence. PR #15 needs a fresh App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run on its exact current head, plus any required approvals.
2. The local ZIP remains an unpublished, gitignored delivery artifact; its checksum proves local artifact integrity, not GitHub Release publication or deployment.

## Completion assessment

The root-unittest fixture defect is addressed at the code/test level and passes under the same essential condition that exposed it: a detached clean exact-head checkout with no `dist`. The normal package suite, full local verification, source-stability checks, and rebuilt ZIP are green. Final merge eligibility remains pending the new exact-SHA external Trust CI result and separately required human/operator gates.
