# Test review — issue #167

Decision: PASS. No valid mutant survived; the candidate was not modified.

## Candidate identity

- Worktree: `/tmp/agbp-issue167-static-scope`
- Branch: `fix/issue-167-static-scope-20260922`
- HEAD: `130ce4a42d9f9bbd1b56772d40b19ae530283205`
- Working-tree fingerprint: `e07b18ed30d5877f29c0e6a7df992948b9fee414e4389f9b1d7065585a5bd6f1`
- Scratch: `/home/pall/review-scratch-issue167-parent/candidate`, permissions `0700`
- Candidate and scratch fingerprints matched before and after; `reviewed-tree-modified: no`.

## Verification

The exact scratch snapshot passed 17 verifier tests, 2 status-inventory tests, and 1 workflow allowlist test:

```text
Ran 20 tests in 6.429s
OK
```

The tests covered status provenance, fail-closed classification, PR no-downgrade, rejected-scope suppression, empty/non-unittest contract rejection before discovery, rename/delete/copy provenance, and exact focused workflow command allowlisting.

Mutation results:

- deleted/renamed/copied status handling: killed;
- PR dispatch downgrade: killed;
- rejected scope invoking the contract subprocess: killed;
- malformed exact reason code: killed;
- workflow prefix/extension acceptance: killed.

No valid mutant survived and no severity findings were found.

## Inconclusive claims

The full PR verifier, focused CLI smoke, historical RED baseline, external Trust CI, and integration/E2E claims were not independently rerun. The prior full-verifier PASS was accepted as a precondition; the coordinator must rerun it after evidence and receipts are recorded.
