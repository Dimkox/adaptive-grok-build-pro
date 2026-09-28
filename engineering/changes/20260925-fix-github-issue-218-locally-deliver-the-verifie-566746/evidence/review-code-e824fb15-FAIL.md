# Independent code review — issue #218, e824fb15

Date: 2026-09-26 UTC. Route: `566746aef130`.

Verdict: **FAIL — 0 Critical, 1 Important, 0 Minor findings.**

## Source and scratch binding

- Candidate: `/home/pall/grok-projects/adaptive-grok-build-issue218-delivery`.
- Base and sole parent: `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- HEAD before/after: `e824fb1551ff37ab647c52b00a1fce38ede79213`.
- Git tree before/after: `0e1c4b188503793d48d61ded35afedf109170e3d`.
- Candidate fingerprint before/after: `4e84b701ed15ca39741205a37517b18306ef5a7708ccfd0d5e83ad7e945f2104`.
- Existing dirty file: `engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/state.json`; SHA-256 `2d3fc4a00febbf08c7a1735a598c5001c42c610f2f1aabec297cf19c08a78e73`. It was copied unchanged into scratch. No other staged, unstaged, or untracked candidate changes were present.
- Private scratch parent: `/home/pall/issue218-code-review.QKuctf`, owned by `pall`, mode `0700`, non-sticky; snapshot: its `candidate/` directory. Snapshot fingerprint and dirty-file digest matched the candidate before probes and after probes.
- Probe source: `/home/pall/issue218-code-review.QKuctf/probe.py`.
- Report copy: `/home/pall/issue218-code-review.QKuctf/code-review-report.md`.

reviewed-tree-modified: no

The snapshot used a local `git clone --no-hardlinks --no-checkout`, detached checkout of the exact HEAD, and a copy of the existing dirty state file. `TMPDIR` was set to the private parent for fixture repositories. Code mutants were compiled into the scratch process's module namespace; test imports were reloaded for each mutant. Neither source mutation nor test artifacts touched the candidate. No network or external writes were performed.

## Important finding I-1: unequal repeated-anchor counts permit moved whitespace to pass

`.grok-stack/adaptive_grok/verification.py:1435` discards all occurrences of a clean line whenever its old/new occurrence counts differ. This destroys stable ordering information. The later bad-line interval comparison can then reuse a moved bad occurrence as though it were unchanged.

Executable reproduction:

```python
old = b'bad  \nA\nA\nA\nB\n'
new = b'A\nA\nA\nA\nbad  \nB\n'
```

Commit `old` as the base, then commit `new`. Native `git diff --check <base> HEAD` exits **2**, reporting `repeated.txt:5: trailing whitespace`. The candidate classifier returns **clean**. With the local attribute `repeated.txt -whitespace` in `.git/info/attributes`, the attribute-independent chain scan still reports `status=complete`, no failures, and no whitespace findings. `_git_diff_check(..., 'fast', selection, scan)` returns **PASS, 3/3 checks passed**; `_git_diff_check(..., 'pr', selection, scan)` returns **PASS, 4/4 checks passed**. The PR probe uses the same explicit valid route-base selection and confirms the native endpoint range check cannot rescue detection when repository attributes suppress it.

This is an actual false PASS, not merely a difference in presentation or an exhausted comparison budget. It violates the retained moved-bad-line detection requirement and AC-004/FORBID-002's no-weakened-scan boundary. Local attributes are exactly the hostile input the independent blob comparison is meant to overcome.

Required closure: preserve sufficient stable clean-line ordering when repeated-line counts differ, or return structured incomplete for ambiguity instead of clean. Add an executable regression for the example above with attribute suppression, covering chain inspection and the final diff gate; extend staged/unstaged coverage where the shared classifier is used. Preserve bounded cumulative work, compatibility for genuinely unchanged legacy bad lines, and metadata-only diagnostics. The same write owner should repair and reverify before renewed review.

## Prior finding disposition

- Original stored-scope forgery and mismatched coverage claims: the committed rejection tests pass. Full recomputation and exact equality remain present.
- Repository-local `core.worktree` redirection: the committed regression passes; Git commands explicitly bind both Git directory and worktree.
- Symlink blobs, unsupported gitlinks/special worktree files, replacement race, and source-line disclosure: all focused regressions pass.
- `f2789117` greedy-first-anchor false positive: its concrete longer-stable-order regression passes. Restoring the old greedy classifier kills that regression. However, the replacement introduces I-1 above.
- `f2789117` missing production shared-budget evidence: both new production wiring tests pass and kill the corresponding reset/omission mutants.
- Prior full anchor-list copy and uncharged empty interval: static inspection shows indexed traversal, no copied sentinel list, and a charge on every interval. No separate mutation probe was executed for this minor historical claim.

## Executed commands and results

Identity checks in the candidate:

```sh
git rev-parse HEAD HEAD^{tree}
git rev-list --parents -n 1 HEAD
git status --porcelain=v1
git diff --name-only 68dfc70c5f58adcc927f731c5d88de09a1b4b242 HEAD
git diff --name-only cb9af4073ba6c3d515145164d771c75ebdfa3224 HEAD -- trust-ci
git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224 HEAD
PYTHONDONTWRITEBYTECODE=1 python3 -B -c 'import sys; from pathlib import Path; sys.path.insert(0,".grok-stack"); from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'
```

Observed: exact identities above, one non-merge commit, only the pre-existing state-file dirt, allowed source-relative path contour, empty Trust CI delta, whitespace check exit 0. HEAD/fingerprint were checked again after probing and remained identical. The cumulative base diff contains 211 paths; the source-relative repairs are confined to the declared package/template/verifier/tests/decision/mistake contour.

From the scratch snapshot, the exact focused commands were:

```sh
TMPDIR=/home/pall/issue218-code-review.QKuctf PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v tests.test_verification_doctor.VerificationTests.test_added_whitespace_classifier_tracks_duplicate_occurrences_and_order tests.test_verification_doctor.VerificationTests.test_chain_whitespace_uses_longest_stable_clean_order tests.test_verification_doctor.VerificationTests.test_chain_whitespace_budget_exhaustion_is_structured_incomplete tests.test_verification_doctor.VerificationTests.test_whitespace_budget_is_aggregate_across_comparisons tests.test_verification_doctor.VerificationTests.test_chain_wires_one_aggregate_whitespace_budget_across_edges tests.test_verification_doctor.VerificationTests.test_endpoint_wires_one_budget_across_worktree_and_index tests.test_verification_doctor.VerificationTests.test_endpoint_whitespace_rejects_moved_and_duplicated_bad_occurrences tests.test_verification_doctor.VerificationTests.test_chain_whitespace_check_ignores_local_policy_and_tree_attributes tests.test_verification_doctor.VerificationTests.test_git_scope_ignores_ambient_selectors_config_and_replace_refs tests.test_verification_doctor.VerificationTests.test_pr_secret_scan_rejects_secret_added_then_deleted_in_commit_chain tests.test_verification_doctor.VerificationTests.test_history_scan_covers_every_merge_parent_edge tests.test_verification_doctor.VerificationTests.test_pr_diff_check_rejects_intermediate_whitespace_repaired_before_head
```

Observed: **12 tests passed in 3.805s**.

```sh
TMPDIR=/home/pall/issue218-code-review.QKuctf PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v tests.test_change_receipts.ReceiptTests.test_identity_only_scan_scope_cannot_hide_add_then_delete_secret tests.test_change_receipts.ReceiptTests.test_scan_scope_coverage_and_completion_claims_must_match_recomputation tests.test_verification_doctor.VerificationTests.test_git_diff_check_binds_worktree_despite_local_core_worktree tests.test_verification_doctor.VerificationTests.test_chain_scan_includes_symlink_blob_content tests.test_verification_doctor.VerificationTests.test_chain_scan_rejects_gitlink_mode tests.test_verification_doctor.VerificationTests.test_worktree_scan_rejects_symlinks_broken_links_and_fifos tests.test_verification_doctor.VerificationTests.test_worktree_scan_detects_named_file_replacement_during_read tests.test_verification_doctor.VerificationTests.test_diff_check_does_not_report_secret_bearing_source_lines
```

Observed: **8 tests passed in 3.148s**.

```sh
TMPDIR=/home/pall/issue218-code-review.QKuctf PYTHONDONTWRITEBYTECODE=1 python3 -B /home/pall/issue218-code-review.QKuctf/probe.py
```

Observed mutation results:

| Mutant | Result | Observed failure |
| --- | --- | --- |
| Reset chain budget inside each whitespace-pair iteration | Killed | Chain wiring test: `complete != incomplete` |
| Omit `budget=whitespace_budget` from endpoint calls | Killed | Endpoint wiring test: `pass != fail` |
| Restore `f2789117` greedy classifier | Killed | Stable-order test receives an unexpected `chain-whitespace` finding |

Final mutation run: all three killed, none survived, none inconclusive. An initial endpoint attempt was inconclusive because a cached imported function retained the original implementation; the harness was corrected to reload the test module and the mutant was rerun and killed. No assurance is claimed from that initial attempt. The independent repeated-count behavior probe survived detection and is I-1 above. The harness exits normally after recording expected mutant failures; its process exit code alone is not a test verdict.

## Unexecuted claims and limits

- I did not rerun full PR/core/PostgreSQL verification. The coordinator supplied preliminary `--mode pr --no-record` PASS, core 88.680s, factory/PostgreSQL 191.989s, and source-stability PASS. These are attributed evidence, not independently reproduced results.
- The inherited cumulative #227→#220 source outside the declared delivery repair contour was not independently subjected to a new broad regression or mutation campaign in this bounded review.
- I-1 was executed for a committed edge and fast/PR diff gates. Its identical staged/unstaged manifestation is inferred from the shared classifier, not separately reproduced here.
- No exhaustive equivalence proof against Git's diff algorithms, adversarial resource stress campaign, or OS-enforced sandbox claim is made.
- No external Trust CI run, deployed-policy validation, signed approval, PR operation, merge, or release was performed. This report does not establish merge eligibility.

The intended greedy-anchor and shared-budget regressions are now effective, but the newly reproduced false PASS blocks a passing code review of this exact candidate.
