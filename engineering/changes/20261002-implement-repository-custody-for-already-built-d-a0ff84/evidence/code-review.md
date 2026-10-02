# Independent code review

- Result: PASS
- Reviewed HEAD: `ca9139129232b2264c3c1fa6dbb577acb5513429`
- Reviewed tree: `2cfa638fa1022b1d421bb92b6225bd7749f11f30`
- Base: `e5856acfd4bc7a186f40a740b54ec86459462db5`
- Scratch: `/tmp/artifact-code-third.ZQJHuY` (mode `0700`)
- Candidate status fingerprint before/after: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `reviewed-tree-modified: no`

## Claims and checks

- `active_delivery`, `current_unreleased_change`, and `local_candidate` agree on the v2.1.0 route, branch, package, source commit/tree, artifact paths/hashes, and unpublished/unactivated state.
- Published v2.0.19 identity and bytes remain immutable.
- `python3 -m unittest tests.test_project_state tests.test_manifest_package`: 71 tests passed.
- `git diff --check e5856acfd4bc7a186f40a740b54ec86459462db5...HEAD`: passed.

## Mutation probes

Each probe used `apply_patch` in the private scratch, ran the named unittest, then restored `PROJECT_STATE.json` with `git checkout -- PROJECT_STATE.json`.

1. Package handoff release changed from `v2.1.0` to `v2.0.19`:

   ```bash
   python3 -m unittest tests.test_project_state.ProjectStateTests.test_m4_source_implementation_is_distinct_from_verification_review_and_delivery
   ```

   Observed: `AssertionError: 'v2.0.19' != 'v2.1.0'`; 1 test, 1 failure, exit 1. Result: killed.

2. `next_action` changed to `Merge the v2.0.19 artifact-child PR and publish v2.0.19.`:

   ```bash
   python3 -m unittest \
     tests.test_project_state.ProjectStateTests.test_project_state_has_independent_milestone_axes_and_truthful_facts \
     tests.test_project_state.ProjectStateTests.test_m4_source_implementation_is_distinct_from_verification_review_and_delivery
   ```

   Observed: stale `v2.0.19 artifact-child` assertion and cross-state equality assertion both failed; 2 tests, 2 failures, exit 1. Result: killed.

3. Artifact tree changed from `0dfa04f3ec3ea9c7a04c723e9d127603fc72999b` to old tree `aed3246585fc6435463c3e3a58f1fe6a16070e6a`:

   ```bash
   python3 -m unittest tests.test_project_state.ProjectStateTests.test_m4_source_implementation_is_distinct_from_verification_review_and_delivery
   ```

   Observed: artifact-tree equality assertion failed; 1 test, 1 failure, exit 1. Result: killed.

Final scratch and candidate status SHA-256 remained `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Not executed

External Trust CI, PR merge, tag creation, GitHub Release publication, deployment, and activation were not executed by the read-only reviewer. They require separate exact-head evidence and authority.
