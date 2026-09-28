# Documentation and contract analysis: issue #218 squashed delivery candidate

## Scope and ruling

This is a repository-local, read-only analysis of base
`cb9af4073ba6c3d515145164d771c75ebdfa3224` and source endpoint
`68dfc70c5f58adcc927f731c5d88de09a1b4b242`. No network, external write,
product edit, runtime receipt, approval, or merge action was performed.

The defensible adoption unit is the **final source tree**, not the source branch's
40-commit history and not its local evidence. The delivery candidate should be one
new commit whose direct parent is the route base and whose tracked content equals
`68dfc70c` outside this new delivery package. The delivery package itself is new
candidate content and must be included in that same commit. Fresh verification and
reviews must bind the resulting candidate SHA; source-branch receipts cannot be
reused after the squash.

## Repository facts

- `cb9af407` is the merge base and ancestor of `68dfc70c`. The source range contains
  40 linear commits and changes 186 paths (`21,093` insertions, `629` deletions).
  The base tree is `881cb6f0ad65ecd131904adf701829e8146b60e3`; the source tree is
  `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`.
- The issue-#218-specific tail is two commits on top of `9dedad01`: implementation
  `0f25afa5` and documentation-fixture cleanup `68dfc70c`. Its net delta changes 28
  paths. The source implementation record says the first pre-review run correctly
  failed on inherited cumulative-history whitespace plus one current analysis
  fixture, and explicitly requires a clean or squashed delivery chain
  ([implementation evidence](../../20260925-fix-github-issue-218-locally-close-the-verifier-3c65bf/evidence/implementation-general_implementer.md)).
- At analysis time, the delivery worktree was still at `cb9af407`, the index matched
  `68dfc70c` exactly (`git diff --cached --quiet 68dfc70c --` returned `0`), and the
  new delivery package was untracked/incomplete. This is useful staging evidence,
  but it is not a clean committed candidate or completion evidence.
- The locally resolved PR target was `refs/remotes/origin/main` at `cb9af407`; no
  symbolic `origin/HEAD` was configured. This observation is local and must be
  rederived by final verification rather than frozen as authority.

## Adopted verifier contract

The source adds an internal `ChainScan` and separates historical scan scope from the
existing final-snapshot inventory
([verification.py](../../../../.grok-stack/adaptive_grok/verification.py)). For every
selected range it captures one exact head, retains the logical route/PR provenance,
enumerates the exclusive `scan_base..head` commit set, and inspects every parent edge
of each selected commit. Commits and regular-file postimage blobs are deduplicated.

The security and whitespace behavior is intentionally fail-closed:

- `secret-scan` scans committed postimage blobs plus current changed worktree files;
  findings expose bounded commit/path/rule metadata, not matched secret bytes.
- `git-diff-check` retains worktree/index and endpoint checks and additionally runs
  `git diff --check` for each enumerated parent-to-commit edge.
- Missing/malformed Git identity or objects and exceeded bounds make the scope
  `incomplete` and make preflight fail. The implemented bounds are 4,096 commits,
  100,000 path edges, 2 MiB per blob, 512 MiB aggregate blob bytes, and 1,000 retained
  findings.
- `changed_files` remains the endpoint/final-snapshot union. Historical chain paths
  are a separate input to focused-scope eligibility, so consumers of the public
  final-snapshot inventory do not silently change meaning.

The source regression coverage includes add-then-delete secret detection, bounded
history failure, every merge-parent edge, repaired intermediate whitespace, recorded
scope shape, and rejection of a scanless PASS receipt
([verifier tests](../../../../tests/test_verification_doctor.py),
[receipt tests](../../../../tests/test_change_receipts.py)). The six focused selectors
listed below passed in `6.849s` during this analysis.

## README and QUICKSTART consistency

The source documentation is consistent and should be adopted byte-for-byte with the
source implementation:

- [README.md](../../../../README.md) states that PR/release preflight captures one
  exact HEAD; scans the bounded, deduplicated union selected by route base and local
  PR target across every commit/merge-parent edge; rejects transient secret or
  whitespace defects; fails closed on incomplete coverage; preserves final-snapshot
  `changed_files`; and binds the closed scan metadata into the existing schema-v2
  completion receipt.
- [QUICKSTART.md](../../../../QUICKSTART.md) gives the same operational semantics next
  to `grok_verify --mode pr --no-record`, then separately requires final recording on
  the clean committed exact HEAD. Its scope split continues to say local verification
  is preflight and the App-owned exact-PR-SHA check is merge authority.

Acceptance should preserve all of those qualifiers. In particular, documentation
must not call the source branch's 40 commits "verified" by the future squashed
candidate receipt, broaden `changed_files` to historical paths, imply network/deployed
Trust CI changes, or describe local receipts as merge authority.

## Report and receipt compatibility

- The verification report remains `schema_version: 1` and gains additive top-level
  `scan_scope`. The scope contract is
  `adaptive-grok.verification-scan/v1` with the exact closed key set `contract`,
  `status`, `head_sha`, `ranges`, `chain_digest`, `commit_count`, `blob_count`,
  `bytes_scanned`, `path_edge_count`, and `worktree`.
- A PASS verification receipt remains schema v2 with completion contract
  `adaptive-grok.completion-receipt/v1`; the full report, including `scan_scope`, is
  stored under the existing `details` member. There is no new receipt version.
- Completion validation rederives and compares `contract`, exact `head_sha`, closed
  logical `ranges`, `chain_digest`, and `commit_count`; it also requires scope and
  worktree status `complete` and non-negative integer blob/byte/path-edge counts
  ([receipts.py](../../../../.grok-stack/adaptive_grok/receipts.py)). It does not
  independently recompute those three operational counts, so acceptance wording
  should say the **range identity and digest** are rederived, not that every metric is.
- A legacy or otherwise scanless receipt remains parseable but is deliberately
  insufficient for current completion. Extra scope keys also fail the closed v1
  predicate; future additions therefore require an explicit contract-version change.
- Squashing necessarily changes `head_sha`, `chain_digest`, tree fingerprint,
  verification receipt digest, and all review completion bindings. Every source
  receipt/review is stale for the candidate, even when product blobs are identical.

With the currently observed local PR target unchanged, a direct one-commit candidate
would have two logical range rows (`route` and `pr-target`) that both start at
`cb9af407`, while the deduplicated scope has one commit. Final evidence must assert
the values actually emitted; it must not hard-code this expectation if local refs
move before verification.

## Recommended acceptance wording

1. **Squash identity:** Given source endpoint `68dfc70c` and route base `cb9af407`,
   the delivery candidate is exactly one non-merge commit directly parented by the
   route base; outside
   `engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/**`,
   its tracked tree is byte-identical to the source endpoint, and every difference
   from that endpoint is confined to the completed delivery package.
2. **Clean-chain behavior:** On the clean committed candidate, PR-mode verification
   reports PASS for both `secret-scan` and `git-diff-check`; its `scan_scope` is
   `complete`, its `worktree` field is `complete`, its exact `head_sha` equals
   `git rev-parse HEAD`, and its route row uses the exact route base. Any identity,
   history, object, timeout, malformed-data, or configured-bound uncertainty fails
   closed and cannot record a PASS receipt.
3. **Regression behavior:** Disposable real-Git regressions prove that a secret added
   and later removed still fails without value disclosure, repaired intermediate
   whitespace still fails, all merge parents are covered, and exceeded history bounds
   yield incomplete coverage.
4. **Inventory compatibility:** `changed_files` continues to mean the final-snapshot
   union; chain-touched paths remain separately available to focused eligibility.
   Existing check names and report/receipt schema versions are unchanged.
5. **Receipt compatibility:** A final schema-v2 verification PASS contains the exact
   closed scan scope under `details`; validation rederives current range identity and
   digest, rejects missing/forged/stale/incomplete scope, and subsequent review
   receipts bind the fresh verification-receipt digest for the same clean head/tree.
6. **Documentation consistency:** The adopted README and QUICKSTART retain the source
   wording summarized above and continue to distinguish local preflight from external
   App-owned merge authority.
7. **Authority boundary:** The route's `scope_and_design_approval` gate is explicitly
   approved before the approved/implementing transition. No local gate, report,
   receipt, source commit, or squash authorizes a push, pull request, Trust CI change,
   or merge.

## Required candidate evidence

Preserve the repository's evidence order: run preliminary PR verification with
`--no-record` against the assembled squash, obtain and persist all four independent
review reports, finish the package and `ready` transition, and include those tracked
artifacts in the one candidate commit. Then run these identity and final recording
checks on that clean commit:

```bash
test "$(git rev-parse HEAD^)" = "cb9af4073ba6c3d515145164d771c75ebdfa3224"
test "$(git rev-list --count cb9af4073ba6c3d515145164d771c75ebdfa3224..HEAD)" -eq 1
test -z "$(git diff --name-only 68dfc70c5f58adcc927f731c5d88de09a1b4b242..HEAD -- . \
  ':(exclude)engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/**')"
git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224..HEAD
python3 scripts/grok_verify.py --mode pr
python3 scripts/grok_status.py
```

Inspect the resulting JSON/receipt rather than relying only on process exit: require
the exact candidate head, complete scan/worktree status, closed keys, current logical
ranges/digest, PASS history checks, `receipt_recorded: true`, and zero status gaps.
After that final verification receipt exists, record fresh `code_review`,
`test_review`, `security_review`, and `release_review` receipts from the already
persisted route-selected reports so every review receipt binds the final verification
digest and clean candidate head/tree. Any material change after review requires the
affected review and all stale fingerprint-bound evidence to be refreshed.

## Commands executed and observed results

```text
git merge-base cb9af407 68dfc70c
  cb9af4073ba6c3d515145164d771c75ebdfa3224
git rev-list --count cb9af407..68dfc70c
  40
git diff --shortstat cb9af407..68dfc70c
  186 files changed, 21093 insertions(+), 629 deletions(-)
git diff --shortstat 9dedad01..68dfc70c
  28 files changed, 2415 insertions(+), 55 deletions(-)
git diff --cached --quiet 68dfc70c --
  exit 0 (index matched source endpoint at observation time)
git diff --check cb9af407..68dfc70c
  exit 0, no output
python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_pr_secret_scan_rejects_secret_added_then_deleted_in_commit_chain \
  tests.test_verification_doctor.VerificationTests.test_pr_history_scan_fails_closed_when_commit_bound_is_exceeded \
  tests.test_verification_doctor.VerificationTests.test_history_scan_covers_every_merge_parent_edge \
  tests.test_verification_doctor.VerificationTests.test_pr_diff_check_rejects_intermediate_whitespace_repaired_before_head \
  tests.test_verification_doctor.VerificationTests.test_verify_records_receipt_for_active_route \
  tests.test_change_receipts.ReceiptTests.test_verification_pass_without_closed_scan_scope_is_insufficient
  Ran 6 tests in 6.849s — OK
```

The full recording verifier was not run in this analysis: the candidate was not yet a
clean committed ready head, the delivery package was incomplete, and its local human
gate was pending.
