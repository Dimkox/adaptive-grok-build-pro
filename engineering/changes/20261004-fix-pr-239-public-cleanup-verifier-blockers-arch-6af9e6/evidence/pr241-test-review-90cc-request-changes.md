# Independent test review — 90cc6cd6

Verdict: installer and handoff repairs pass this bounded test review at frozen90cc. Overall REQUEST_CHANGES remains appropriate because the coordinator reports a reproduced receipt-cleanup P2 from the independent code reviewer. I did not duplicate that reproducer.

## Identity and isolation

- HEAD before/after: `90cc6cd6f475ac6486d762aadec99a37ea9ef9cf`.
- Fingerprint before/after: `ab024c0f8c0c616842a7a7941d697b69aa05d6475c462f15098ba0a1f362df71`.
- Candidate stayed clean. Private exact clone also remained clean with the same HEAD/fingerprint.
- Scratch relative to candidate: `../adaptive-grok-build-pro/.review-scratch/test-review-repair-RXX326/`.
- Scratch parent and TMPDIR: reviewer-owned0700, nonsticky; locally ignored through `.git/info/exclude:8`.
- Capacity recorded before task inspection at `2026-10-04T17:29:25Z`: 14 physical/28 logical CPUs; default affinity22 CPUs; child-only widening verified28, effective cpuset0-27, no finite quota observed. Commands pinned CPUs6-11, maximum6 workers; every invocation bounded by175s.
- reviewed-tree-modified: no

## Executed claims

1. `build_payload()` now captures the inventoried template once, with its expected identity, and generates all aliases from captured content **and mode**. A deterministic post-capture bytes/mode mutation retained the original bytes/mode640 in all nine generated entries.
2. Hostile source-alias contents did not enter the payload: zero source-alias reads. The removed unbound template reread branch is absent.
3. All nine regular eight-line source launchers delegate shared implementation. Independent execution from an unrelated working directory preserved canonical script root/name, stdin, stdout, stderr and canonical exit7. Every missing-canonical fallback returned0 with the expected JSON.
4. Current continuation binds PR241, superseded239, dependency240 and base `6dbbc7dbe81812d919851c2300db6f4917033d43`. Historical69f5 App observation remains explicitly non-current; current checked-head/merge/external-success fields remain null. Merged/unchanged continuation retains its no-op instruction.
5. Selected receipt regressions passed for helper cancellation, envelope failure, repeated orphan prevention, reused artifacts, foreign-inode replacement and in-place changes after successful ownership capture. Existing cap, closed reference/envelope binding, serialization-failure retirement and source-change refusal tests also passed. These passes do not cover the code reviewer’s newly reported combined fault/rewrite boundary.

## Commands and observed results

All test commands ran from `scratch/repo` with:

```text
GIT_OPTIONAL_LOCKS=0
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=.grok-stack
TMPDIR=<private scratch>/tmp
GROK_TEST_WORKERS=6
taskset -c 6-11 timeout 175s
```

The complete scoped batch was:

```bash
python3 -B -m unittest -q \
 tests.test_quality_gates \
 tests.test_project_state \
 tests.test_installer.InstallerTests.test_hook_aliases_use_the_inventoried_template_snapshot \
 tests.test_installer.InstallerTests.test_legacy_root_hook_names_delegate_and_preserve_fallback \
 tests.test_installer.InstallerTests.test_installed_template_artifacts_are_explicit_reusable_source \
 tests.test_installer.InstallerTests.test_source_inventory_rejects_bound_root_or_managed_dir_relocation \
 tests.test_installer.InstallerTests.test_source_reads_are_nofollow_and_bounded_at_the_descriptor \
 tests.test_hooks.HookTests.test_root_shim_dispatches_pre_tool_use \
 tests.test_hooks.HookTests.test_root_shim_fail_open_when_canonical_missing \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_helper_does_not_adopt_replacement_between_link_and_stat \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_helper_post_link_stat_fault_cleans_descriptor_owned_artifact \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_helper_post_publication_cancellation_removes_owned_artifact \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_envelope_failures_do_not_accumulate_new_report_orphans \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_aborted_reused_report_preserves_preexisting_referenced_digest \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_helper_abort_preserves_a_referenced_reused_artifact \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_abort_cleanup_does_not_unlink_identity_changed_report \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_oversized_report_still_fails_and_invalidates_prior_receipt \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_publication_faults_retire_prior_pass \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_verification_classification_serialization_faults_retire_prior_pass \
 tests.test_verifier_recovery.DurableReceiptRecoveryTests.test_report_publication_rechecks_source_before_receipt
```

```text
Ran 46 tests in 27.830s
OK
```

Reviewer-owned independent probes:

```bash
python3 -B ../independent_installer_checks.py -v
```

```text
Ran 2 tests in 1.016s
OK
captured_template: one bound read; nine old bytes/mode640;
zero source-alias reads
legacy_launchers: nine names; unrelated cwd;
stdin/stdout/stderr/exit7 preserved; all fallbacks pass
```

Bounded mutations, each running only its corresponding regression:

```bash
python3 -B ../mutation_checks.py
```

- M1: restore unbound template rereads during alias generation — KILLED; one regression failure, `10 != 1`.
- M2: make `pre_tool_use.py` dispatch as `session_end.py` — KILLED; canonical name/payload assertion failed. Injection counter confirmed exactly one altered launcher.
- M3: change current handoff PR241 back to239 — KILLED; `239 != 241`.
- M4: remove merged/no-op continuation — KILLED; `'no-op' not found`.
- No valid mutant survived.

Read-only source checks:

```text
git diff --stat 69f5e29f57c3bbc7169ae43d8e9ad9e3dcf98321..HEAD
git diff --name-only 69f5e29f57c3bbc7169ae43d8e9ad9e3dcf98321..HEAD
git diff 69f5e29f57c3bbc7169ae43d8e9ad9e3dcf98321..HEAD -- <all25 changed paths>
git diff --check 69f5e29f57c3bbc7169ae43d8e9ad9e3dcf98321..HEAD
git rev-parse HEAD
git status --porcelain=v1
```

Inspected the complete25-file delta and relevant installer, template, receipt writer/reader, tests and handoff surroundings. Diff whitespace check returned0. Receipt262144/report8388608 caps, public reference contract and hydration validation are unchanged in this delta.

Before/after fingerprint command:

```bash
GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys,pathlib;sys.path.insert(0,".grok-stack");from adaptive_grok.util import tree_fingerprint;print(tree_fingerprint(pathlib.Path.cwd()))'
```

## Limitations and closed harness issues

- Initial batch omitted PYTHONPATH:38 tests ran in15.830s with one module-import error. Corrected complete batch passed above.
- First M2 interception used an unresolved path and never injected; its apparent survival was INCONCLUSIVE. Resolved-path interception plus injection assertion closed that harness error. Reviewer-local mistake notes are in private scratch.
- Receipt tests separately cover first post-link-stat failure and in-place rewrite after successful identity capture, not their combination. The coordinator-reported P2 needs its own combined regression and repair.
- No full suite/verifier, PostgreSQL, architecture executable check, deployed UI, remote-state refresh, external approval/check validation, GitHub write or thread resolution was performed.
- Prior cleanup reviews and69f5 findings are historical. This report establishes only the freshly executed90cc scoped claims above, not completion or merge authority.
