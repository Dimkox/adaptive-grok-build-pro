# M3 final test re-review

Status: **PASS**

Reviewed product SHA: `512ac3f2690d5489b5cf83020952dd9b685c2c37`

Reviewed clean product fingerprint: `e8840dbdafb2ba50da2cc427ed482e92646b398856bed30b460e6befbbf4dac1`

Comparison base: `635c9ddf2d63c1ea823074106976a8f3de6299a9`

## HIGH finding resolution

The nested authority-directory TOCTOU finding is closed. The loader now opens the complete fixed authority topology once, retains descriptors and identities for `schemas/`, `governance/`, all three registry directories, four schemas, and three registries, reads only from those pinned file descriptors, and reopens/rechecks every named directory and file before returning the snapshot. The snapshot also retains source-byte digests, and handoff construction compares every authority/evidence/example/test byte consumed during evaluation with the exact Git-head blobs; a swap-and-restore cannot become exact-head evidence.

The retained regression reproduces replacement of both `schemas/` and `governance/` between document reads. Adjacent tests preserve repository-root replacement, final-file mutation, symlink rejection, frozen schema identity, dirty worktree, handoff shape, and exact-head swap/restore coverage.

## Focused evidence

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_governance.GovernanceLoaderTests.test_loader_rejects_nested_authority_directory_replacement \
  tests.test_governance.GovernanceLoaderTests.test_loader_pins_one_root_identity_for_the_complete_snapshot \
  tests.test_governance.GovernanceLoaderTests.test_loader_rejects_symlink_and_read_mutation \
  tests.test_governance.GovernanceLoaderTests.test_loader_freezes_complete_v1_governance_schema_identities \
  tests.test_governance.GovernanceHandoffTests.test_exact_head_binding_rejects_swap_restore_authority_bytes \
  tests.test_governance.GovernanceHandoffTests.test_handoff_rejects_dirty_worktree_sha_and_digest_mismatches \
  tests.test_governance.GovernanceHandoffTests.test_handoff_has_exact_closed_immutable_v1_shape

7/7 passed in 1.319s
```

A review-only four-level mutation matrix independently replaced the named path after a pinned read:

```text
schemas: REJECTED code=io message=schemas: authority directory changed while loading
governance: REJECTED code=io message=governance: authority directory changed while loading
registry-subdir: REJECTED code=io message=governance: authority directory changed while loading
registry-file: REJECTED code=io message=governance/rules/index.json: authority file changed while reading
```

Static checks:

```text
ruff check .grok-stack/adaptive_grok/governance.py tests/test_governance.py
All checks passed!

git diff --check ecdbc7b..0a9191615c0c839815995ab462e3fcfc8ef174be -- \
  .grok-stack/adaptive_grok/governance.py tests/test_governance.py
exit 0
```

## Test-quality and coverage assessment

The repair adds `454` lines to `governance.py` and `96` lines to `test_governance.py`. The focused tests exercise opening, pinned reads, nested topology mismatch, file-identity mutation, frozen schema mismatch, exact-head source-digest mismatch, and the successful handoff path. The deeper registry-subdirectory and real named-file replacements were additionally exercised by the review-only matrix; retaining those two cases in the repository would improve failure localization, but the shared topology loop and exact original exploit are covered and no blocking gap remains.

The previous broad receipt's `80%` repository / `86%` governance coverage belongs to `ecdbc7b` and must not be reused as coverage evidence for this larger tree. No broad suite or `grok_verify` was rerun during this re-review. The final route verifier must measure the new exact tree after evidence files are stable; the configured repository threshold remains `74%`.

## Repeated-path affected re-review

The follow-up repair `0a91916..512ac3f` is also approved. `_ConsumedInputRecorder` binds every normalized path to its first byte observation, returns those same bytes for repeated references, rejects inconsistent repeated observations, caps unique consumed inputs at the existing evidence bound, and supplies one digest per path to the exact-head comparison. Rule validation and effective-rule/example evaluation share the same recorder, preserving lifecycle provenance instead of rereading mutable evidence.

The retained repeated-path test proves both sides: alternating A/B bytes cannot satisfy two different digests and the physical path is read once; identical expected content completes a full handoff with exactly one physical read. Alias/path normalization and input bounds remain fail closed.

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_governance.GovernanceHandoffTests.test_handoff_binds_repeated_evidence_path_to_first_observation \
  tests.test_governance.GovernanceLoaderTests.test_loader_rejects_reference_alias_that_drops_target_constraints \
  tests.test_governance.GovernanceLoaderTests.test_loader_enforces_record_and_evidence_limits \
  tests.test_governance.GovernanceLifecycleTests.test_transition_rejects_unvalidated_traversal_evidence \
  tests.test_governance.GovernanceLifecycleTests.test_repository_validation_binding_is_not_caller_constructible \
  tests.test_governance.GovernanceLifecycleTests.test_effective_rules_reject_missing_and_mismatched_evidence \
  tests.test_governance.GovernanceLifecycleTests.test_live_evidence_is_required_after_candidate_status

7/7 passed in 0.966s

ruff check .grok-stack/adaptive_grok/governance.py tests/test_governance.py
All checks passed!

git diff --check 0a91916..512ac3f -- \
  .grok-stack/adaptive_grok/governance.py tests/test_governance.py
exit 0
```

This follow-up adds a net `131` product lines and `85` test lines. No blocking test-quality or lifecycle-provenance gap was found; final broad coverage remains intentionally delegated to the single final verifier on the stabilized evidence topology.

## Evidence-topology note

This review inspected the exact Git object above while code, security, and test reports were concurrent untracked evidence files. The clean fingerprint is `sha256(HEAD ASCII)` for that exact product commit and intentionally excludes those untracked reports. Materializing this report changes the live worktree fingerprint, so any earlier verification receipt is stale. All final reports must be present before the one final verifier/receipt recording pass, and every review receipt must then bind that identical final fingerprint. Local evidence remains preflight only and does not replace the App-owned exact-PR-SHA Trust CI check.
