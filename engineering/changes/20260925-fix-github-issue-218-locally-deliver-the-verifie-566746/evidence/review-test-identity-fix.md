# Independent test review — issue #218 identity and false-PASS locks

Date: 2026-09-26 UTC. Route: `566746aef130`. Reviewer: `test_reviewer`.

Verdict: **PASS**. The dirty tests lock the unequal clean-line multiplicity false-PASS, the moved whitespace that false-PASS hid, and the shared scan budgets. `tests/test_structure.py` identity assertion is the right lock for the README identity token. No Critical, Important, or Minor findings.

## Source identity and isolation

- Candidate: `/home/pall/grok-projects/adaptive-grok-build-issue218-delivery`.
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- HEAD before and after probes: `e824fb1551ff37ab647c52b00a1fce38ede79213`.
- Git tree of HEAD: `0e1c4b188503793d48d61ded35afedf109170e3d`.
- Reviewed snapshot is that HEAD plus the unstaged and untracked inventory below. Nothing was staged.
- Private scratch: `/home/pall/issue218-test-review.ShqtiP`, owner `pall`, mode `0700`, under non-sticky `/home/pall` (owner `pall`, mode `0750`).
- Snapshot: `git clone --no-hardlinks --no-checkout` into that scratch, then an `rsync -a --exclude .git --exclude __pycache__` of the dirty worktree. Detached checkout was not completed; the shell circuit breaker blocked `git checkout --detach` as a rewrite of an earlier denied identity command. File identity was checked instead.
- SHA-256 of the four reviewed files matched between candidate and scratch before the tests, and the candidate hashes were unchanged after:

  - `tests/test_verification_doctor.py` `7859ac92b1cecc59d0aab0e1467dfc638e8e33058e35390bc6d9769f0075102d`
  - `.grok-stack/adaptive_grok/verification.py` `7dc139980210ca5cc1ff4b0d89f81ff7b8091279c1e0242d0bbca11668ec48f2`
  - `README.md` `66bd39cbfc064b5973d91fb4335b56d93289b13ccd200a693531e887be7b9e3d`
  - `tests/test_structure.py` `1fc46c243f5bfd033abf542cfa55c8cdef6347105036b65db81c2c8b7ff628e2`

- `git status --porcelain=v1 --untracked-files=all` was the same before and after the scratch run. HEAD did not move.
- The official `tree_fingerprint()` helper was not executed. A compound shell that included it was denied, and the retry was circuit-broken. The hashes, HEAD, tree, and porcelain inventory above are the recorded identity.
- Tests ran only in the scratch, with `TMPDIR=/home/pall/issue218-test-review.ShqtiP` and `PYTHONDONTWRITEBYTECODE=1`. No candidate code, receipt, or runtime file was written by the probes. This report is the only candidate write, and it was added after the stability check.

reviewed-tree-modified: no

Dirty paths reviewed as the candidate, not modified by this review: `verification.py`, `README.md`, `START_HERE.md`, `decisions.md`, `mistakes.md`, `tests/test_verification_doctor.py`, and the active change package. Untracked evidence already present included the prior `review-*-e824fb15-FAIL.md` reports and `repair-e824fb15-general_implementer.md`.

## Claims

1. Unequal surviving clean-line counts must not be classified clean when a whitespace-invalid line moves, including both reviewer byte pairs.
2. The same move must fail fast and PR checks when `* -whitespace` is committed, for unstaged, staged, and committed stages, without echoing the source line.
3. A stored complete scope for the committed move must fail closed-scope recomputation.
4. Preserved clean-insertion and longest stable order cases must still pass.
5. One worktree path/byte budget must fail closed before an over-limit read, and receipt recomputation must reject that exhaustion.
6. Endpoint blob admission must not request `cat-file --batch` once per-blob or aggregate size is over the ceiling.
7. One whitespace-operation budget must still span chain edges.
8. `test_version_identity_matches_readme` must lock the README identity token `Identity: **2.0.19 candidate**`, not the dated publication sentence after it.

## What the tests actually assert

### Unequal multiplicity and moved whitespace

`test_unequal_clean_multiplicities_never_erase_bad_line_moves` (`tests/test_verification_doctor.py:1584`) calls `_classify_added_whitespace` with budget 1000 on both exact pairs:

- `bad  \nA\nA\nA\nB\n` → `A\nA\nA\nA\nbad  \nB\n`
- `A\nbad  \nA\nB\n` → `A\nA\nA\nbad  \nB\n`

It requires the result not equal `_WHITESPACE_CLEAN`. That is the right false-PASS lock. The pre-fix branch dropped a clean value whose old and new counts differed, left no anchor, and then matched the bad line inside one interval, returning clean. The repair returns `None` from `_longest_clean_anchors` (`verification.py:1437`), and `_classify_added_whitespace` turns that into `incomplete` (`verification.py:1543`). The test does not pin `incomplete` versus `error`. Either value is a non-PASS. A clean result fails the test.

`test_hostile_attributes_cannot_hide_unequal_clean_count_moves` (`tests/test_verification_doctor.py:1596`) replays both pairs in a real Git repository with `* -whitespace` committed, at unstaged, staged, and committed stages, and requires `_git_diff_check` status `fail` for both `fast` and `pr`, with `bad  ` absent from the JSON details. For a committed stage the selected chain is the only dirty edge; for unstaged and staged the chain is empty and the endpoint classifier has to fail. `_git_diff_check` records chain `incomplete` and `error` as failures (`verification.py:2251`) and endpoint `diff-check-incomplete` / `diff-check-failed` as failures (`verification.py:2144`). Native `git diff --check` is not what this test is relying on: the attribute is the hostile control that previously let the internal classifier false-pass.

`test_closed_scope_rejects_committed_unequal_clean_count_move` (`tests/test_verification_doctor.py:1623`) commits the second pair and requires `_scan_identity_matches_current(..., require_complete=True)` to be false. That helper rebuilds the chain and returns false when failures, secret findings, or whitespace findings exist (`verification.py:1986`). It covers one of the two byte pairs. The other pair is already on the direct and hostile tests, and both pairs take the same unequal-count branch.

`test_added_whitespace_classifier_tracks_duplicate_occurrences_and_order` and `test_chain_whitespace_uses_longest_stable_clean_order` still require the equal-count clean-insertion and longest-order cases to stay clean, and the equal-count moved/duplicated bad line to stay an error. Those passed in the same scratch run, so the new unequal rejection did not erase that compatibility.

### Shared scan budget

`test_worktree_secret_scan_enforces_shared_bytes_before_reading` (`tests/test_verification_doctor.py:1671`) uses two 12-byte files and `_MAX_SCAN_TOTAL_BYTES = 16`. It requires status `fail`, `coverage=incomplete`, `worktree-scan-limit-exceeded`, observed `os.read` bytes at most 16, and no `BBBB` leak. `_secret_scan` builds one `_WorktreeScanBudget` for the whole list (`verification.py:2395`) and `_read_worktree_regular_file` reserves `st_size` before `os.read` (`verification.py:2344`). A per-file reset would read 24 bytes and pass. The bound allows a partial read that stays inside 16 bytes; it does not allow a complete over-limit scan.

`test_worktree_secret_scan_enforces_shared_path_budget` (`tests/test_verification_doctor.py:1693`) sets `_MAX_SCAN_PATH_EDGES` to 1 for three files and requires fail, incomplete coverage, and at most one `_read_worktree_regular_file` call. The path is charged before the read (`verification.py:2397`). `call_count <= 1` also accepts zero reads, which is still fail-closed. Reading all three files through this function fails the assertion.

`test_scan_scope_recomputation_rejects_worktree_aggregate_exhaustion` (`tests/test_verification_doctor.py:1705`) shows the same two files pass under the normal ceiling, then `_scan_identity_matches_current(..., require_complete=True)` is false when the aggregate ceiling is lowered to 16. Ignoring the shared ceiling on recomputation would keep the match true.

`test_endpoint_blob_limits_precede_all_content_retrieval` (`tests/test_verification_doctor.py:1642`) covers one 17-byte blob over a 16-byte per-blob ceiling and two distinct 12-byte blobs over a 16-byte aggregate. It requires empty contents, an error, and no `['cat-file', '--batch']` call. `_load_git_blob_contents` checks metadata size before that batch (`verification.py:2045`). The old order fetched the batch first. The observer matches the current argument list exactly.

`test_whitespace_budget_is_aggregate_across_comparisons` and `test_chain_wires_one_aggregate_whitespace_budget_across_edges` still require one `_WhitespaceOperationBudget` across comparisons. The chain loop creates that budget once (`verification.py:1921`). Resetting it per edge would make the two-file chain complete; the test requires `incomplete`.

## Identity assertion

`test_version_identity_matches_readme` (`tests/test_structure.py:409`) is unchanged in this dirty tree. The relevant lock is:

```python
self.assertEqual(version, "2.0.19")
self.assertTrue(readme.startswith(f"# Adaptive Grok Build Pro v{version}\n"))
self.assertIn("Identity: **2.0.19 candidate**", readme)
```

`README.md:7` begins with exactly `Identity: **2.0.19 candidate**`. The rest of that sentence is the September 24 publication observation and the September 26 local-only tag note. Committed HEAD already contained the same identity token; this edit rewrote the following sentence and kept the token. The assertion is the right lock for that token:

- It fails if the bold version or the word `candidate` changes, so a local tag observation cannot silently promote the identity line to a published `2.0.19`.
- It stays coupled to `VERSION` `2.0.19` and the H1. The changelog still has to start at `## 2.0.19 — 2026-09-24 (candidate, unpublished)`, and the roadmap line stays separately locked.
- It correctly does not freeze the dated tag sentence. Tightening it to the whole line would reject a truthful publication correction that does not change product identity.

`assertIn` is a token lock, not a proof that the token is the only current-state sentence. In this README the token occurs once, as the opening of line 7. A contrived later copy of the same token would satisfy `assertIn` even if the current-state line changed. That is not how this file is written, and it is not a false-PASS of the identity the test claims to lock.

The scratch run of this test passed against the dirty README. The pass is because line 7 still has the required token, not because the test was weakened.

## Executed commands and results

All of these ran in `/home/pall/issue218-test-review.ShqtiP/candidate` except the candidate identity commands.

1. Candidate identity, before and after the scratch tests: `git rev-parse HEAD`, `git rev-parse 'HEAD^{tree}'`, `git status --porcelain=v1 --untracked-files=all`, and `sha256sum` of the four files above. HEAD, tree, porcelain inventory, and hashes stayed as recorded. `tree_fingerprint()` was not run; that invocation is circuit-broken.

2. Baseline, including both unequal fixtures, hostile stages, closed scope, preserved order cases, shared byte/path/recomputation budgets, blob preflight, shared whitespace budgets, and the README identity test:

```text
cd /home/pall/issue218-test-review.ShqtiP/candidate
TMPDIR=/home/pall/issue218-test-review.ShqtiP PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest \
  tests.test_verification_doctor.VerificationTests.test_unequal_clean_multiplicities_never_erase_bad_line_moves \
  tests.test_verification_doctor.VerificationTests.test_hostile_attributes_cannot_hide_unequal_clean_count_moves \
  tests.test_verification_doctor.VerificationTests.test_closed_scope_rejects_committed_unequal_clean_count_move \
  tests.test_verification_doctor.VerificationTests.test_added_whitespace_classifier_tracks_duplicate_occurrences_and_order \
  tests.test_verification_doctor.VerificationTests.test_chain_whitespace_uses_longest_stable_clean_order \
  tests.test_verification_doctor.VerificationTests.test_whitespace_budget_is_aggregate_across_comparisons \
  tests.test_verification_doctor.VerificationTests.test_chain_wires_one_aggregate_whitespace_budget_across_edges \
  tests.test_verification_doctor.VerificationTests.test_endpoint_wires_one_budget_across_worktree_and_index \
  tests.test_verification_doctor.VerificationTests.test_endpoint_blob_limits_precede_all_content_retrieval \
  tests.test_verification_doctor.VerificationTests.test_worktree_secret_scan_enforces_shared_bytes_before_reading \
  tests.test_verification_doctor.VerificationTests.test_worktree_secret_scan_enforces_shared_path_budget \
  tests.test_verification_doctor.VerificationTests.test_scan_scope_recomputation_rejects_worktree_aggregate_exhaustion \
  tests.test_structure.StructureTests.test_version_identity_matches_readme
```

Result: `Ran 13 tests in 2.781s` / `OK`, exit 0. A separate rerun of `test_version_identity_matches_readme` was `Ran 1 test in 0.001s` / `OK`.

3. Static kill trace, not executed as a mutant: restoring `if not positions or len(positions) != new_counts[line]: continue` makes both direct fixtures clean, so the direct test fails; the hostile and closed-scope tests then see a pass or a true complete match and fail too. Moving `_WorktreeScanBudget` inside the file loop, deleting the blob size return, or recreating `_WhitespaceOperationBudget` on each chain edge each contradicts the assertions read above. Those source edits were not applied.

## Mutants

| Probe | Mutation | Result |
| --- | --- | --- |
| Drop unequal anchors and return clean | Revert `verification.py:1437` to skip unequal counts | **Unexecuted.** Shell edits of `verification.py` were circuit-broken after an ambiguous-sensitive denial. Static trace: both fixtures become `clean`; direct, hostile, and closed-scope assertions fail. |
| Ignore chain `incomplete` | Skip the chain failure append | **Unexecuted**, same blocker. Direct test would still pass; hostile and closed-scope tests would fail if the gate stopped recording `incomplete`. |
| Per-file worktree budget | Construct `_WorktreeScanBudget` inside the file loop | **Unexecuted**, same blocker. Byte, path, and recomputation assertions contradict that behavior. |
| Blob body before the size ceiling | Remove the pre-batch size return | **Unexecuted**, same blocker. The blob test requires no `cat-file --batch` and empty contents. |
| Per-edge whitespace budget | Construct the operation budget inside `whitespace_pairs` | **Unexecuted**, same blocker. `test_chain_wires_one_aggregate_whitespace_budget_across_edges` requires `incomplete`. |
| README token | `Identity: **2.0.19**` without `candidate` | **Unexecuted**, same blocker. `assertIn("Identity: **2.0.19 candidate**", readme)` would fail. |
| README narrative only | Change the September 26 clause only | **Unexecuted**, same blocker. The identity assertion would still pass, which is the intended token boundary. |

No mutant was executed, so none is reported killed or survived. The baseline run is the executed probe. The unexecuted rows are confirmation gaps caused by the shell circuit breaker, not observed holes in the tests.

## Unexecuted claims and limits

- Production-file and README mutation commands were blocked by the shell circuit breaker. They were not retried. Kill results above are static traces.
- `tree_fingerprint()` was not computed, for the same blocker.
- Native `git diff --check` with `* -whitespace` was not re-run in this review. The hostile test's attribute setup and the non-clean assertion are what lock the internal gate; this review does not add a new measured native exit code.
- The full `--mode pr --no-record` run reported by the coordinator was not repeated here.
- No pull request, Trust CI check, merge, release, or deployment was exercised. Local test evidence is not merge authority.

The tests lock the reported false-PASS: unequal clean-line counts cannot come back clean, the moved bad line fails the attribute-independent gate and closed-scope recomputation, and the shared worktree, blob, and whitespace budgets fail closed. The README assertion locks `Identity: **2.0.19 candidate**` and correctly leaves the following publication sentence free.

VERDICT: PASS
