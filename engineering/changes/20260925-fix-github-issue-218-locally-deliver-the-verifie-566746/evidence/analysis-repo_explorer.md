# Repository analysis — issue #218 delivery candidate

Observed at `2026-09-25T20:07:35Z`. This analysis used only local Git objects, a disposable local clone, and read-only/focused checks. It performed no network or external action and changed no product file. The delivery worktree was being populated concurrently by the selected write owner; this report distinguishes immutable object facts from the observed staged state.

## Conclusion

There are two materially different meanings of “squash,” and they must not be conflated:

1. A full squash of `cb9af4073ba6c3d515145164d771c75ebdfa3224..68dfc70c5f58adcc927f731c5d88de09a1b4b242` is mechanically clean and exactly reproduces source tree `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`. It is not a bounded issue-#218 delta: it flattens 40 commits, 186 paths, and the preceding #227, #226, verifier-performance, #224, #222, and #220 work into the candidate.
2. The actual #218 tail is the two-commit range `9dedad01b17903a1faddf6fd3221c325115a839b..68dfc70c5f58adcc927f731c5d88de09a1b4b242`. It is 28 paths and `+2415/-55`, but it does **not** apply cleanly to the requested `cb9af407` base. Its first commit has eight content conflicts because the implementation was written against the stacked predecessor APIs and tests.

The currently staged tracked snapshot is the first form: at the observation above, both `git diff --cached --quiet 68dfc70c... --` and `git diff --quiet` returned `0`. Thus index and tracked worktree exactly match the source commit tree, while HEAD remains the requested base. The untracked delivery package is an expected additional evidence layer; once committed, whole-tree equality to the source is no longer expected, so equivalence must exclude only that exact delivery-package prefix.

Release-readiness ruling: mechanically feasible, but not yet a go decision. The full-source squash is deliberately broad and the route has a pending `scope_and_design_approval` human gate. A bounded #218-only candidate instead requires an explicit integration port and fresh verification; cherry-picking or applying the tail as though it were independent is unsafe.

## Immutable identities and ancestry

```text
delivery base/head before candidate commit:
  cb9af4073ba6c3d515145164d771c75ebdfa3224
delivery base tree:
  881cb6f0ad65ecd131904adf701829e8146b60e3
source implementation HEAD:
  68dfc70c5f58adcc927f731c5d88de09a1b4b242
source implementation tree:
  0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66
source implementation parent:
  0f25afa5f3a1c4db0e1ef384d5ede15af83710ff
issue implementation baseline:
  9dedad01b17903a1faddf6fd3221c325115a839b
merge-base(base, source):
  cb9af4073ba6c3d515145164d771c75ebdfa3224
commit count base..source:
  40
```

Reproduce:

```bash
git rev-parse \
  cb9af4073ba6c3d515145164d771c75ebdfa3224^{tree} \
  68dfc70c5f58adcc927f731c5d88de09a1b4b242 \
  68dfc70c5f58adcc927f731c5d88de09a1b4b242^{tree}
git merge-base \
  cb9af4073ba6c3d515145164d771c75ebdfa3224 \
  68dfc70c5f58adcc927f731c5d88de09a1b4b242
git rev-list --count \
  cb9af4073ba6c3d515145164d771c75ebdfa3224..68dfc70c5f58adcc927f731c5d88de09a1b4b242
git log --format='%H %P %s' --reverse \
  cb9af4073ba6c3d515145164d771c75ebdfa3224..68dfc70c5f58adcc927f731c5d88de09a1b4b242
```

The source sibling `/home/pall/grok-projects/adaptive-grok-build-issue218` was clean and resolved to the exact source HEAD/tree above when checked.

## Exact net-diff scope

| Range | Commits | Paths | Short stat | Meaning |
| --- | ---: | ---: | --- | --- |
| `cb9af407..9dedad01` | 38 | 169 | `+18691/-587` | stacked predecessor work |
| `9dedad01..68dfc70c` | 2 | 28 | `+2415/-55` | issue #218 implementation and evidence tail |
| `cb9af407..68dfc70c` | 40 | 186 | `+21093/-629` | full source tree to squash |

Commands:

```bash
git diff --shortstat <left>..<right>
git diff --name-status --no-renames <left>..<right>
git diff --numstat <left>..<right>
git diff --check <left>..<right>
```

The #218 tail consists of:

- three implementation files: `.grok-stack/adaptive_grok/{verification,util,receipts}.py`;
- five test/support files: `tests/{_support,test_change_receipts,test_hooks,test_package_status,test_verification_doctor}.py`;
- four repository guidance/history files: `README.md`, `QUICKSTART.md`, `decisions.md`, `mistakes.md`;
- sixteen files in the original #218 change package `engineering/changes/20260925-fix-github-issue-218-locally-close-the-verifier-3c65bf/`.

Eleven of those 28 paths were already changed by the predecessor stack:

```text
.grok-stack/adaptive_grok/receipts.py
.grok-stack/adaptive_grok/util.py
.grok-stack/adaptive_grok/verification.py
QUICKSTART.md
README.md
decisions.md
mistakes.md
tests/test_change_receipts.py
tests/test_hooks.py
tests/test_package_status.py
tests/test_verification_doctor.py
```

This overlap explains why the tail cannot be treated as an independent patch. In particular, the #218 receipt binding calls the evolved verification identity API; the verifier implementation is built on the preceding exact-head, fail-fast, and receipt behavior; and compatibility tests assume the predecessor fixture/API shapes.

## Clean-squash and tree-equivalence proof

The following was run in a local `--no-hardlinks` disposable clone checked out detached at the exact base; it did not mutate the delivery or source repositories:

```bash
git checkout --detach cb9af4073ba6c3d515145164d771c75ebdfa3224
git merge --squash 68dfc70c5f58adcc927f731c5d88de09a1b4b242
git write-tree
git rev-parse 68dfc70c5f58adcc927f731c5d88de09a1b4b242^{tree}
git diff --cached --shortstat
git diff --name-only --diff-filter=U
```

Observed:

```text
merge --squash exit: 0
squash index tree: 0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66
source tree:       0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66
unmerged paths: 0
short stat: 186 files changed, 21093 insertions(+), 629 deletions(-)
```

This proves full-source squash feasibility and byte-for-byte tracked-tree equivalence. It does not prove that the 186-path scope is approved.

The bounded-tail probe reset the disposable clone to `cb9af407` and ran:

```bash
git cherry-pick --no-commit 0f25afa5f3a1c4db0e1ef384d5ede15af83710ff
```

It exited `1` with these eight unmerged paths:

```text
.grok-stack/adaptive_grok/receipts.py
.grok-stack/adaptive_grok/verification.py
QUICKSTART.md
README.md
decisions.md
tests/test_change_receipts.py
tests/test_hooks.py
tests/test_package_status.py
```

The source commit's `util.py` and `test_verification_doctor.py` hunks auto-merged in this probe, but that is not evidence that they are semantically independent of the predecessor stack. A plain `git apply --check 9dedad01..68dfc70c` also failed. Therefore “squash just the last two commits onto cb9” is not a clean operation.

## Candidate equivalence checks

Before committing a full-source squash, the strongest cheap tracked-state check is:

```bash
git diff --cached --quiet \
  68dfc70c5f58adcc927f731c5d88de09a1b4b242 --
git diff --quiet
```

Both returned `0` at the recorded observation. After the delivery package is staged or committed, use a single explicit exclusion for that package:

```bash
delivery_change=engineering/changes/20260925-fix-github-issue-218-locally-deliver-the-verifie-566746
git diff --quiet \
  68dfc70c5f58adcc927f731c5d88de09a1b4b242..HEAD -- \
  . ":(exclude)$delivery_change/**"
test "$(git rev-list --count cb9af4073ba6c3d515145164d771c75ebdfa3224..HEAD)" = 1
test "$(git rev-parse HEAD^)" = cb9af4073ba6c3d515145164d771c75ebdfa3224
```

Also assert that every non-source path is inside the delivery package:

```bash
git diff --name-only \
  68dfc70c5f58adcc927f731c5d88de09a1b4b242..HEAD -- \
  . ":(exclude)$delivery_change/**"
```

Expected output is empty. A one-commit topology plus this empty product diff is stronger than comparing commit IDs, because the squashed candidate necessarily has a new commit ID and adds its own evidence package.

## Fast preflight commands and observed results

The following six regressions directly cover the security and whitespace behavior, range bounds, merge-parent traversal, persisted scan scope, and rejection of scanless PASS receipts:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_verification_doctor.VerificationTests.test_pr_secret_scan_rejects_secret_added_then_deleted_in_commit_chain \
  tests.test_verification_doctor.VerificationTests.test_pr_history_scan_fails_closed_when_commit_bound_is_exceeded \
  tests.test_verification_doctor.VerificationTests.test_history_scan_covers_every_merge_parent_edge \
  tests.test_verification_doctor.VerificationTests.test_pr_diff_check_rejects_intermediate_whitespace_repaired_before_head \
  tests.test_verification_doctor.VerificationTests.test_verify_records_receipt_for_active_route \
  tests.test_change_receipts.ReceiptTests.test_verification_pass_without_closed_scan_scope_is_insufficient
```

Observed against the source-equivalent staged snapshot: `Ran 6 tests in 6.813s`, `OK`.

Static and contract preflight:

```bash
ruff check \
  .grok-stack/adaptive_grok/receipts.py \
  .grok-stack/adaptive_grok/util.py \
  .grok-stack/adaptive_grok/verification.py \
  tests/_support.py \
  tests/test_change_receipts.py \
  tests/test_hooks.py \
  tests/test_package_status.py \
  tests/test_verification_doctor.py
python3 scripts/grok_spec.py validate \
  engineering/changes/20260925-fix-github-issue-218-locally-close-the-verifier-3c65bf/change-spec.yaml
git diff --check --cached
```

Observed: Ruff passed; typed spec passed with `18/18` criteria mapped and digest `6a586d395b3f16ed978e46e6a480c23b98346c35f0776d76844cb54289b9779e`; cached diff check passed.

These are fast preflights, not completion evidence. After scope approval, final package completion, and the one clean candidate commit, the route still requires full `python3 scripts/grok_verify.py --mode pr`, all four independent review kinds, fresh fingerprint-bound receipts, zero `grok_status` gaps, and the external App-owned exact-SHA Trust CI check before merge eligibility.

## Smallest safe delivery choices

- If the approved outcome is exact source-tree delivery including all predecessor fixes, keep the current full-source squash, document the 186-path/40-commit scope explicitly, add only this delivery package, prove product equivalence with the exclusions above, and run all final gates on the clean one-commit HEAD.
- If the approved outcome is issue #218 alone, do not use the current full squash and do not cherry-pick the two tail commits. Port the behavior through the single write owner against `cb9af407`, treating the 11 overlapping paths as integration work, then rerun the focused RED/GREEN contour and full gates. Exact equality with source tree `0914b5d6…` is neither possible nor desirable for that narrower choice.
