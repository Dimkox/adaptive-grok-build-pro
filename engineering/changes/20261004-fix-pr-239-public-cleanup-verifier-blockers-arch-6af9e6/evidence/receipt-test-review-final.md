# Independent test review: receipt repair and handoff

Reviewer: `cleanup_test_reviewer`. Scoped verdict: PASS for frozen HEAD `8b766e23c6700ead66ddec8a78ee8daf7abdc703`. The receipt serialization P2 is closed. All 151 tests in the five binding modules and six targeted tests passed; all three mutants were killed.

Actual PR base: `6dbbc7dbe81812d919851c2300db6f4917033d43`. Candidate fingerprint before/after: `b206e6ded5a849acd570670936f84633f2f8cd12615b77d9a8dd4381cc75e74b`. HEAD and clean status remained unchanged.

Scratch relative to candidate: `../adaptive-grok-build-pro/.review-scratch/test-review-finalhandoff-sOBena/repo`. Its reviewer-owned parent and trusted non-sticky `.review-scratch` parent are mode `0700`. The local clone reproduced the exact HEAD and fingerprint. Mutations were restored; final scratch fingerprint matched. Candidate Git calls used `GIT_OPTIONAL_LOCKS=0`.

reviewed-tree-modified: no

Capacity remeasured at `2026-10-04T15:09:47Z`: 14 physical cores, 28 online logical CPUs; default affinity exposed 22. Effective cpuset `0-27`, no finite applicable cgroup quota observed. Child-only widening succeeded; reviewer allocation at most four CPUs.

All Python commands used `GIT_OPTIONAL_LOCKS=0`, `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=.grok-stack:tests`.

## Binding modules

```bash
TMPDIR=/tmp/grok-test-output-yqzlfH taskset -c 0-3 timeout 175s \
  python3 -m unittest -q \
  tests.test_structure tests.test_project_state tests.test_manifest_package \
  tests.test_workflow_sources tests.test_repo_router
```

Observed: Ran 151 tests in 14.786s, OK, zero skips.

The first combined attempt under project-contained TMPDIR ran 156 tests and produced 13 failures/21 errors because unchanged package safeguards rejected the project's mode-0775 ancestry. The coordinator permitted private mode-0700 ephemeral test output under `/tmp`; the complete rerun passed without modifying guards or permissions. This environment limitation is closed. The Git snapshot remained inside the project.

## Targeted checks

With TMPDIR set to the private project scratch sibling `tmp`:

```bash
taskset -c 0-3 python3 -m unittest -v \
  test_verifier_recovery.DurableReceiptRecoveryTests.test_verification_classification_serialization_faults_retire_prior_pass \
  test_verifier_recovery.DurableReceiptRecoveryTests.test_spilled_report_reference_and_all_envelope_bindings_are_closed \
  tests.test_project_state.ProjectStateTests.test_current_continuation_binds_cleanup_dependency_and_fresh_clone \
  test_verification_doctor.TypedSpecVerificationTests.test_proven_v1_retirement_is_disclosed_without_current_gate_evidence \
  test_verification_doctor.TypedSpecVerificationTests.test_v2_cannot_be_archived_and_relocation_keeps_strict_gate \
  test_verification_doctor.TypedSpecVerificationTests.test_retirement_rejects_tampered_missing_active_current_and_unknown_specs
```

Observed: Ran 6 tests in 4.969s, OK. P2 exercises circular and unserializable details, requiring removal of prior pass, missing evidence, and no temporary/report artifacts. Handoff binds PR239, observed PR240 dependency, actual source base, durable route/manifest, historical labels and fresh-clone pointer. PR239 verification/merge fields remain null.

Executed `_historical_spec_migrations` against actual manifest, durable route and original blob paths resolved from `git ls-tree -rz` at the agreed base. Observed: 13 mappings validated, 12 legacy archives, one v2 relocation retained for strict validation, base `6dbbc7dbe81812d919851c2300db6f4917033d43`. The clone initially made its candidate branch `origin/HEAD`; only private clone refs were aligned to the agreed base and source-observed `origin/main` before this proof.

## Mutations

| Mutant | Exact command/probe | Outcome |
|---|---|---|
| Restore serialization classification outside the retirement guard | `taskset -c 0 python3 -m unittest -v test_verifier_recovery.DurableReceiptRecoveryTests.test_verification_classification_serialization_faults_retire_prior_pass` | Killed: two failures; prior pass remained after both serialization errors. |
| Point `fresh_clone.continuation_record` at historical `active_delivery` | `taskset -c 0 python3 -m unittest -v tests.test_project_state.ProjectStateTests.test_current_continuation_binds_cleanup_dependency_and_fresh_clone` | Killed: pointer assertion failed. |
| Restore manifest source base to old `97a758…` | Same handoff command, plus actual-base migration probe | Killed: source-base equality failed; validator rejected `migration origin is not unique in the trusted source base`. |

No surviving or inconclusive mutants. `git diff --quiet 6dbbc7dbe81812d919851c2300db6f4917033d43..HEAD -- trust-ci` returned zero. Trust CI source is inherited from the merged dependency; no deployed-authority or cryptographic-attestation claim.

Earlier reports, including `194cdc62f`, remain historical. No full verifier, PostgreSQL or external approval checks were run here. This report binds frozen `8b766e23c` only; the planned public-projection hygiene edit requires fresh evidence.

## Hygiene addendum: b405a606

Independent test-review addendum: PASS for `8b766e23c..b405a6066dd70505f066642b2851af3bc09fe52b`. No scoped finding.

HEAD before/after: `b405a6066dd70505f066642b2851af3bc09fe52b`. Fingerprint before/after: `4432f6d5956303ea8a87e11b0539a15c9d06c6e33d51c21fcdfd5dea8e424e5e`. Candidate remained clean.

Scratch: `../adaptive-grok-build-pro/.review-scratch/test-review-finalhandoff-sOBena/repo`, exact HEAD, private mode-0700 parent. Restored scratch matched candidate fingerprint. Startup capacity remeasured; reviewer used one CPU. Git calls used `GIT_OPTIONAL_LOCKS=0`.

reviewed-tree-modified: no

Fresh command with bytecode disabled, private TMPDIR and `PYTHONPATH=.grok-stack:tests`:

```bash
taskset -c 0 python3 -m unittest -v \
  tests.test_structure.StructureTests.test_cancelled_preflight_public_projection_preserves_scope_without_home_paths
```

Observed: Ran 1 test in 0.001s, OK.

Preservation probe resolved original report at base `6dbbc7dbe81812d919851c2300db6f4917033d43` to blob `6334c167ac00bf35bafa37e441f087d4de685c33`. Its 25,603 bytes matched SHA256 `4350077c2590c484ac063fca91decb6e1b9b503e1bfa8149f3e1c9f3b0e30096`. Parsed reports identical after removing projection annotation and replacing only the named argv field. Status remained fail, terminal cancelled, check status incomplete.

Private-copy custody independently checked with `stat`, `sha256sum` and `git check-ignore -v`: parent `0700`, file `0600`, 25,603 bytes, original hash, ignored by `.git/info/exclude:8`. Copy relative to candidate: `../adaptive-grok-build-pro/.review-scratch/public-log-projection.5UrFsb/original-scope-preflight-cancelled.json`.

Mutation restored a generic `/home/exampleproject/review/` prefix in projected argv, then reran the same test. Killed, exit 1: `cancelled historical report contains an operator-home path`. Mutation restored; no surviving or inconclusive probes.

The non-dereferenceable flag applies to the ignored private copy; original Git blob remains historical content. Prior 8b review is historical. No 151-test/full rerun performed; this addendum grants no current verification or receipt authority. Coordinator persistence is report-only; fresh final full verification and external exact-head Trust CI remain separate gates.
