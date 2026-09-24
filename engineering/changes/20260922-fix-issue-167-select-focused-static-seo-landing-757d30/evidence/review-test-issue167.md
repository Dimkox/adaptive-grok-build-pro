# Test review — issue #167

Decision: PASS. No valid mutant survived the current test review.

## Exact candidate identity

- Worktree: /tmp/agbp-issue167-static-scope
- Branch: fix/issue-167-static-scope-20260922
- HEAD reviewed: 526255f4ec7fd3ef00d45641da571c54f40cbe0f
- Route/base: 130ce4a42d9f9bbd1b56772d40b19ae530283205
- Repository fingerprint: 9cdee9f712cc80dd5ce16636788716bcb621581589d5fc8553a2d81d1c4d44bd
- Git tree: 7251b1fc383aca958f0803683a6187522fc50d37
- Worktree at review: clean
- reviewed-tree-modified: no
- Scratch: not used in this read-only re-review; no mutation claim is made from a private scratch.
- This report records the candidate before the report itself and final receipt were persisted.

## Test command and result

    python3 -m unittest tests.test_verification_doctor tests.test_util_fingerprint tests.test_workflow_artifacts

Result: 131 tests passed in 217.014s.

The coverage includes accepted and rejected focused scopes, one-directory and focused-test binding, deleted/renamed/copied/malformed/untrusted Git status provenance, PR-mode no-downgrade, suppression of the landing-contract subprocess for rejected scopes, focused execution, and exact workflow command allowlisting.

## Claim outcomes

- Accepted focused landing inventory: killed; focused tests cover the positive path.
- Mixed, unknown, multi-directory, missing-test, mismatched-test, malformed, deleted, renamed, and copied inventory: killed.
- PR mode silently downgrading: killed.
- Rejected focused scope launching a contract subprocess: killed.
- Extra workflow arguments bypassing the allowlist: killed.
- Product source, Trust CI authority, and external merge behavior: unexecuted by unit tests; these are bounded by source review and require the external App-owned check.
- Full PR verifier: executed by the coordinator before report persistence and passed; the coordinator must rerun it after persistence for a current receipt.

## Limitations

- No external Trust CI check was run.
- This report does not claim that static focused evidence replaces the required exact-head external merge gate.
- The final verification receipt must bind the post-persistence tree.

## Final assessment

The regression suite protects the intended optimization without allowing focused verification to certify an unclassified or mixed change.
