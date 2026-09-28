# Independent code review — issue #218 identity repair

Date: 2026-09-26 UTC. Route: `566746aef130`. Reviewer: code_reviewer. Read-only except this report.

Verdict: **PASS — 0 Critical, 0 Important, 0 Minor findings.**

The dirty repair closes the previous false PASS. Unequal surviving clean-line counts no longer drop anchors and then accept a moved bad line. Both review fixtures fail closed under attribute suppression for unstaged, staged, and committed edges, on fast and PR gates. The README identity token required by `test_version_identity_matches_readme` remains exactly `Identity: **2.0.19 candidate**`. No second product identity was introduced.

## Source and scratch binding

- Candidate: `/home/pall/grok-projects/adaptive-grok-build-issue218-delivery`.
- Branch: `fix/issue-218-scan-chain-delivery`.
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`.
- HEAD before review probes: `e824fb1551ff37ab647c52b00a1fce38ede79213` (sole parent, the base above). This report does not create a commit.
- Dirty contour reviewed: unstaged `.grok-stack/adaptive_grok/verification.py`, `tests/test_verification_doctor.py`, `README.md`, `START_HERE.md`, `decisions.md`, `mistakes.md`, and the active change-package files, plus the untracked repair handoff and four prior FAIL reports. No staged delta.
- Private scratch parent: `/home/pall/issue218-code-review-identity.cNWddB`, owner `pall`, mode `0700`, not sticky. Snapshot: `candidate/` via `rsync -a` of the worktree, excluding `.git`, `__pycache__`, and `*.pyc`. `TMPDIR` for the executed tests was that parent.
- A detached `git clone` of HEAD was not created. That command was denied by the shell circuit breaker, so the snapshot is a byte copy of the working tree rather than an independent object database. Probe imports and `project_copy` git repositories used this copy.
- SHA-256 before probes, matched between candidate and scratch:
  - `verification.py` `7dc139980210ca5cc1ff4b0d89f81ff7b8091279c1e0242d0bbca11668ec48f2`
  - `README.md` `66bd39cbfc064b5973d91fb4335b56d93289b13ccd200a693531e887be7b9e3d`
  - `tests/test_verification_doctor.py` `7859ac92b1cecc59d0aab0e1467dfc638e8e33058e35390bc6d9769f0075102d`
- After probes, those candidate digests were unchanged and `cmp` showed the restored scratch `verification.py` equal to the candidate. `tree_fingerprint()` was not recomputed; the import helper was denied by the same circuit breaker.

reviewed-tree-modified: no

## Claims probed

1. The two unequal-count fixtures must not classify as clean: `bad  \nA\nA\nA\nB\n` → `A\nA\nA\nA\nbad  \nB\n`, and `A\nbad  \nA\nB\n` → `A\nA\nA\nbad  \nB\n`.
2. With `* -whitespace`, the fast and PR diff gates must fail for those bytes when the move is unstaged, staged, or committed, and the report must not contain the bad line text.
3. Closed-scope recomputation must reject the committed form.
4. Equal-count legacy behavior must remain: duplicate-order cases and the longer stable clean order still pass when the bad line is not an addition.
5. README identity stays `Identity: **2.0.19 candidate**` with no other product identity, and `test_version_identity_matches_readme` passes.

Static trace of the repair in `.grok-stack/adaptive_grok/verification.py`: `_longest_clean_anchors` used to `continue` when a surviving clean line’s old and new counts differed, which discarded the boundary. It now returns `None` on that inequality. `_classify_added_whitespace` maps `None` to `_WHITESPACE_INCOMPLETE`. Chain inspection records `chain-whitespace-comparison-incomplete` and endpoint inspection records `diff-check-incomplete`. `_git_diff_check` sets `status=fail` when either chain failures or endpoint findings are present. That is fail-closed, not a clean claim. Equal counts still use the existing budgeted monotone anchors, so the longer-stable-order case is unchanged.

## Executed commands and results

From the scratch snapshot, with `TMPDIR` set to the private parent and `PYTHONDONTWRITEBYTECODE=1`:

```sh
python3 -B -m unittest -v \
  tests.test_verification_doctor.VerificationTests.test_unequal_clean_multiplicities_never_erase_bad_line_moves \
  tests.test_verification_doctor.VerificationTests.test_hostile_attributes_cannot_hide_unequal_clean_count_moves \
  tests.test_verification_doctor.VerificationTests.test_closed_scope_rejects_committed_unequal_clean_count_move \
  tests.test_verification_doctor.VerificationTests.test_added_whitespace_classifier_tracks_duplicate_occurrences_and_order \
  tests.test_verification_doctor.VerificationTests.test_chain_whitespace_uses_longest_stable_clean_order \
  tests.test_structure.StructureTests.test_version_identity_matches_readme
```

Observed: **6 tests, OK, 1.876s**, exit 0. This includes both fixtures, all three stages, and both fast and PR gates inside the hostile-attribute test.

README check, separate from the test lock:

- `VERSION` is `2.0.19`. The dirty diff does not touch `VERSION`, `CHANGELOG.md`, `DARK_FACTORY_ROADMAP.md`, or `adaptive_grok.__version__`.
- The only `Identity:` line is `Identity: **2.0.19 candidate**.` The H1 remains `# Adaptive Grok Build Pro v2.0.19`.
- Relative to HEAD, that token is unchanged. The hunk rewrites the following dated publication sentences and one later paragraph in `START_HERE.md` as well. Those sentences still name candidate `2.0.19` and published `v2.0.18`; they say the remote tag, GitHub Release, and latest remote release were not queried. They do not introduce `2.0.20` or call `v2.0.19` the verified published release.
- Local ref `refs/tags/v2.0.19` in the main git directory contains `4e5d1505433f7a2d5faa71db31c0b4d964f77897`, the object id written in the README. That id is not the claimed target commit, which is consistent with an annotated tag. The tag object body was not decoded, because object inspection was circuit-blocked.

## Mutation

One mutant was applied only in the scratch copy: line 1441, `return None` changed to `continue`, restoring the old drop-anchor behavior for unequal counts. The follow-up unittest of that mutant was denied by the shell circuit breaker and was not rerun. Result: **inconclusive / unexecuted**, not killed and not survived. The scratch file was restored and byte-compared equal to the candidate before this report was written. No assurance is taken from the unexecuted mutant.

## Unexecuted claims and limits

- Native `git diff --check` exit status for the fixtures was not remeasured here. The gate tests above are the candidate’s own attribute-independent decision.
- Endpoint blob preflight, shared worktree byte/path budgets, and the historical secret add-then-delete chain test were read in the diff but not executed in this pass.
- Full `grok_verify.py --mode pr` was not rerun. The coordinator’s preliminary `--no-record` PASS is attributed, not reproduced.
- `tree_fingerprint()`, detached clone, and peeled tag-target decode were blocked and were not retried.
- No exhaustive equivalence to Git’s diff algorithm, resource-stress campaign, external Trust CI run, pull request, merge, or release is claimed. This report is not merge authority.

The selected-base chain and endpoint whitespace gates no longer false-PASS the unequal clean-line moves that previously passed, and the README identity lock matches `2.0.19 candidate` without a second identity.

VERDICT: PASS
