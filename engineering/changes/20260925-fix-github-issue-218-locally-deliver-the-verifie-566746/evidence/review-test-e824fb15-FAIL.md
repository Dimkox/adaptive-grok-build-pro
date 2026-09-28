# Independent test review — issue #218 — e824fb15

Date: 2026-09-26 UTC. Route: `566746aef130`.

Verdict: **FAIL — 0 Critical, 1 Important, 0 Minor findings.**

## Source identity and isolation

- Candidate: `/home/pall/grok-projects/adaptive-grok-build-issue218-delivery`.
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- HEAD before and after: `e824fb1551ff37ab647c52b00a1fce38ede79213`.
- Git tree before and after: `0e1c4b188503793d48d61ded35afedf109170e3d`.
- Candidate fingerprint before and after: `4e84b701ed15ca39741205a37517b18306ef5a7708ccfd0d5e83ad7e945f2104`.
- The sole dirty path before and after was coordinator-owned `engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746/state.json`.
- Private scratch: `/home/pall/issue218-test-review.qEGMHu`, owner `pall`, mode `0700`, below trusted non-sticky `/home/pall` (owner `pall`, mode `0750`).
- Snapshot: local `git clone --no-hardlinks --no-checkout`, detached checkout at exact HEAD, then copy the sole dirty state file. Scratch fingerprint matched the candidate before probes and again after all scratch mutations were reversed. No staged or untracked candidate changes needed overlaying.
- All executable tests, disposable repositories, and mutations ran under private scratch with `TMPDIR` set there. No candidate code, artifacts, receipts, reports, or runtime files were written. No network or external write occurred.

reviewed-tree-modified: no

## Important I-1 — unequal repeated-clean counts erase move boundaries and allow false PASS

At `.grok-stack/adaptive_grok/verification.py:1435`, `_longest_clean_anchors` omits every clean-line value whose old/new multiplicities differ. This leaves an unanchored interval in which a moved whitespace-invalid line can reuse an old occurrence, even though the line crosses a surviving clean line. The tests at `tests/test_verification_doctor.py:1497` cover equal repeated anchors and duplicate clean insertion separately, but omit their interaction with a moved bad occurrence.

Exact synthetic bytes:

```python
old = b'A\nbad  \nA\nB\n'
new = b'A\nA\nA\nbad  \nB\n'
```

Native unsuppressed `git diff --check` exits `2` and identifies `changed-count.txt:4: trailing whitespace`. The candidate classifier returns `False` (no added whitespace error), and the committed-chain scanner reports complete coverage with no failures or whitespace findings.

Repeating the same real Git fixture with committed `* -whitespace` attributes proves this is a production bypass, not merely a direct-helper discrepancy:

- Unstaged `_git_diff_check(...)`: `pass`, `2/2 checks passed`, empty details.
- After committing the move, `_build_chain_scan(...)`: `status=complete`, `blob_count=1`, `bytes_scanned=14`, `path_edge_count=1`, no failures or whitespace findings.
- `_git_diff_check(..., selection, scan)`: `pass`, `3/3 checks passed`.
- After `_secret_scan` closes worktree coverage, `_scan_identity_matches_current(..., require_complete=True)`: `True`.

Thus suppressed Git policy plus a changed clean-line multiplicity defeats the attribute-independent fallback and its complete-scope revalidation. This violates the requested moved-occurrence preservation and AC-004/AC-008. It is Important because the local hygiene/evidence boundary false-passes; external Trust CI remains separate merge authority.

Required repair: retain enough ordering information when clean multiplicities differ to reject this move, or return structured incomplete evidence when ordering cannot be established safely. Add real committed/staged/unstaged hostile-attribute regressions and closed-scope rejection coverage for this counterexample. Preserve clean-insertion/legacy-context compatibility, existing moved/duplicate rejection, deterministic aggregate limits, and metadata-only diagnostics.

## Historical finding disposition and mutation results

The specific `f2789117` findings are covered by executable regressions now:

| Probe | Mutation | Result |
| --- | --- | --- |
| Chain aggregate wiring | Reset `_WhitespaceOperationBudget` inside the `whitespace_pairs` loop | **Killed**: new chain test expected incomplete but got complete; 1 failure in 0.226s |
| Endpoint aggregate wiring | Remove `budget=whitespace_budget` from `_endpoint_whitespace_findings` caller | **Killed**: new endpoint test expected fail but got pass; 1 failure in 0.199s |
| Maximum stable order | Replace LIS result with first-viable greedy candidates | **Killed**: unique and repeated order subcases plus real chain regression failed; 3 failures across 2 tests in 0.211s |
| Changed repeated-clean count plus bad-line move | Adversarial input, no source mutation | **Survived**, producing I-1 above |

All three source mutants were applied only in private scratch and restored with patches. `git diff --exit-code -- .grok-stack/adaptive_grok/verification.py` then passed. Both wiring tests and the history commit-bound test passed after restoration (3 tests, 0.898s), and both classifier/order selectors passed (2 tests, 0.227s). No attempted source mutant was inconclusive. The surviving adversarial input is a finding, not a mutation-score claim.

## Executed commands and results

Commands below ran in `/home/pall/issue218-test-review.qEGMHu/candidate` unless identified as candidate identity checks. Test commands used `TMPDIR=/home/pall/issue218-test-review.qEGMHu PYTHONDONTWRITEBYTECODE=1`.

1. Candidate and restored scratch identity:

   `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.grok-stack python3 -c 'from pathlib import Path; from adaptive_grok.util import tree_fingerprint; print(tree_fingerprint(Path.cwd()))'`

   Result: identical fingerprint quoted above. Candidate `git rev-parse HEAD HEAD^{tree}` and `git status --porcelain=v1` were unchanged before/after. `git diff --check cb9af4073ba6c3d515145164d771c75ebdfa3224 HEAD` passed.

2. Baseline focused matrix:

   `python3 -m pytest -q -p no:cacheprovider tests/test_verification_doctor.py tests/test_change_receipts.py -k 'whitespace or aggregate or scan_includes_symlink or scan_rejects_gitlink or scan_rejects_symlinks or does_not_report_secret or git_scope_ignores or binds_worktree or secret_added_then_deleted or commit_bound or merge_parent or identity_only_scan_scope or scan_scope_coverage'`

   Result: **24 passed, 154 deselected, 32 subtests passed in 9.60s**. The actual invocation included the same `-k` expression without the final two receipt selectors before the second filename, followed by the full expression above; pytest applies the final expression. This matrix covers hostile Git controls, symlink/gitlink/special-file handling, historical secrets, forged coverage fields, whitespace preservation, bounds, and redaction.

3. Chain mutant and restored baseline:

   `python3 -m unittest tests.test_verification_doctor.VerificationTests.test_chain_wires_one_aggregate_whitespace_budget_across_edges`

   Result under mutant: killed as above.

4. Endpoint mutant:

   `python3 -m unittest tests.test_verification_doctor.VerificationTests.test_endpoint_wires_one_budget_across_worktree_and_index`

   Result under mutant: killed as above.

5. Restored production wiring and commit bound:

   `python3 -m unittest tests.test_verification_doctor.VerificationTests.test_chain_wires_one_aggregate_whitespace_budget_across_edges tests.test_verification_doctor.VerificationTests.test_endpoint_wires_one_budget_across_worktree_and_index tests.test_verification_doctor.VerificationTests.test_pr_history_scan_fails_closed_when_commit_bound_is_exceeded`

   Result: **3 tests, OK, 0.898s**.

6. Greedy mutant and restored order baseline:

   `python3 -m unittest tests.test_verification_doctor.VerificationTests.test_added_whitespace_classifier_tracks_duplicate_occurrences_and_order tests.test_verification_doctor.VerificationTests.test_chain_whitespace_uses_longest_stable_clean_order`

   Mutant: **3 failures, 2 tests, 0.211s**. Restored: **2 tests, OK, 0.227s**.

7. Independent real-Git changed-multiplicity probe:

   `python3 /home/pall/issue218-test-review.qEGMHu/probe.py`

   First run without attributes: native diff exit 2, classifier clean, complete chain with no whitespace finding. Final retained script includes hostile attributes and production endpoint/chain/complete-scope checks; output shows the four false-PASS facts listed in I-1. The script uses only synthetic `bad` text, not credentials.

## Unexecuted claims and limits

- The coordinator reports current full `--mode pr --no-record` PASS (core 88.680s, factory/PostgreSQL 191.989s, source stability PASS). I did not rerun that full suite; this report independently establishes only the focused results above.
- Cumulative inherited architecture, factory parallel-runner, receipt lifecycle, and packaging changes were not independently re-executed beyond this focused contour. Existing historical review appendices and current implementation evidence were inspected as context, not promoted to current dynamic proof.
- The O(n log n) structure and charged binary-search/interval traversal were inspected; I did not independently benchmark the full 2 MiB object ceiling or re-run the historical timing series. Executed operation-limit tests establish fail-closed exhaustion, not a general wall-clock SLA.
- No PR, external Trust CI, merge, release, deployment, or live-system behavior was exercised. Local reviews and receipts cannot replace external exact-SHA merge authority.

The latest production-budget and greedy-anchor regressions are effective, but the missing changed-multiplicity move case leaves a reproducible false PASS. Final verdict for this source identity: **FAIL**.
