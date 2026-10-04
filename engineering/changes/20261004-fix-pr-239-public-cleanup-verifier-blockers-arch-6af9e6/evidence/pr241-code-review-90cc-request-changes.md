# Independent code review — 90cc6cd6

Verdict: REQUEST_CHANGES for two P2 receipt-cleanup gaps. The three QG repairs are validated.

Reviewed scope: actual `69f5e29f..90cc6cd6` delta, surrounding receipt paths, and relevant agreed-main bindings. Earlier cleanup reviews remain historical.

## Findings

1. P2 — changed foreign bytes can be deleted after the first post-link stat fault (`.grok-stack/adaptive_grok/receipts.py:159`).
   - Reproducer rewrites the newly linked file in place, then raises one-shot `OSError` at line209.
   - `owned_identity` remains `None`; cleanup consequently checks only device/inode and deletes the modified bytes.
   - Observed: `foreign-first-stat remaining_reports=0`.
   - Repair: pin staged data identity before linking and require bounded digest/content validation before deleting when complete publication metadata is unavailable. Preserve changed bytes.

2. P2 — the second post-link stat fault can strand an unchanged owned report (`:212–219`).
   - The stored identity includes ctime. Unlinking the temporary hardlink changes ctime; if the following stat fails, cleanup compares against the stale pre-unlink identity.
   - A deterministic 25ms clock-boundary delay reproduces one orphan. Immediate execution is timing-dependent: observed both zero and one.
   - Observed: `second-stat-clock-boundary remaining_reports=1`.
   - Repair: distinguish legitimate hardlink ctime changes from data modification, retaining bounded digest validation and foreign-identity protection.

Both need failing regressions. Neither reproduction left a qualifying receipt; the issues concern artifact ownership and cleanup.

## Validation

- QG plus all `DurableReceiptRecoveryTests`: 32 passed, 53.154s.
- Both new installer controls plus current-continuation binding: 3 passed, 0.829s.
- Changed Python Ruff checks and `git diff --check`: passed.
- Actual-main `6dbbc7d..HEAD -- trust-ci` diff: empty.
- Static review covered captured template bytes/mode, nine launchers, canonical dispatch/fallbacks, PR241 historical/current separation, merged/no-op instructions and architecture ownership additions. No additional finding identified.

Commands executed from private snapshot, with `GIT_OPTIONAL_LOCKS=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=.:.grok-stack:tests`, private `TMPDIR=../tmp`, and CPU affinity `0-5`:

```bash
taskset -c 0-5 timeout 175s python3 -B -m unittest -v test_quality_gates test_verifier_recovery.DurableReceiptRecoveryTests
taskset -c 0-5 timeout 30s python3 -B -m unittest -v test_installer.InstallerTests.test_legacy_root_hook_names_delegate_and_preserve_fallback test_installer.InstallerTests.test_hook_aliases_use_the_inventoried_template_snapshot test_project_state.ProjectStateTests.test_current_continuation_binds_cleanup_dependency_and_fresh_clone
taskset -c 0-5 python3 -B ../review_90cc_stat_faults.py
taskset -c 0-5 python3 -B ../review_90cc_mutations.py disable-exact-skips
taskset -c 0-5 python3 -B ../review_90cc_mutations.py disable-owned-cleanup
git diff --check 69f5e29f..HEAD
git diff --name-status 6dbbc7dbe81812d919851c2300db6f4917033d43..HEAD -- trust-ci
```

Mutation results:

- Disable exact skip allowances: killed, six PR/release subcase failures.
- Disable owned cleanup: killed, two failures covering cancellation and envelope failure.
- Initial allowance harness accidentally captured a reassigned variable; that invocation was inconclusive, corrected and rerun—not a surviving product mutant.

## Identity and isolation

Identity before/after, candidate and clean scratch alike:

- HEAD: `90cc6cd6f475ac6486d762aadec99a37ea9ef9cf`
- Fingerprint: `ab024c0f8c0c616842a7a7941d697b69aa05d6475c462f15098ba0a1f362df71`
- Candidate Git status: clean both times.

Scratch relative to candidate: `../adaptive-grok-build-pro/.review-scratch/receipt-code-EjOjoX/snapshot`.
Its reviewer-owned parent and `.review-scratch` are mode0700. Reproduction/mutation scripts remain in that private parent.

Limitations: no full verifier, external check revalidation, deployed-policy assessment or PR/thread mutation. Architecture execution and broader installer/state mutations remain outside this bounded code-review run.

reviewed-tree-modified: no
