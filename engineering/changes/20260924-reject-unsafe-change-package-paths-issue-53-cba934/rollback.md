# Rollback plan — Reject unsafe change-package paths (issue 53)

## Trigger conditions

Roll back only when a *legitimate* change-package call starts refusing: an ordinary task title is rejected (one containing `:` or a URL, for example), an existing package under `engineering/changes/` can no longer be opened or transitioned, or a refused call turns out to have written something. The intended refusals are not triggers — a title with a backslash, a drive prefix or a control byte, a hostile `route_id`/`created_at` in the route record, or a `change_id` that escapes `engineering/changes/` are exactly the defect class this change closes; a false positive on real input is the only rollback case, and `test_every_historical_package_name_is_still_acceptable` plus the punctuation tests exist to catch it before release.

## Application rollback

One `git revert` of the single product commit touching `.grok-stack/adaptive_grok/change.py` (its test module reverts with it), delivered as a new pull request and re-checked externally — matching the declared `forward_fix` strategy with `maximum_steps: 1`. There is no data migration, no generated artifact to unwind, no cache to invalidate and nothing renamed: the change adds no persisted field, and refusals happen before the first filesystem write, so a rejected call left no partial package to clean up. The 148 historical package directories were never modified, so reverting the code restores the previous behaviour over the same tree.

## Data recovery / forward-fix

Nothing to restore — this change removes no content and rewrites no package. Prefer the forward fix over the revert: narrow the offending rule in a follow-up commit (`TITLE_CONTROL_BYTES`, `DRIVE_PREFIX`, `ALLOWED_COMPONENT_PUNCTUATION` or the component list in `_derive_change_id`) rather than dropping the containment check in `package_dir`, which is the part that prevents an out-of-tree write. If a package was genuinely created with an unsafe name while the bug was live, leave it in place and handle the rename under issue #52 rather than ad-hoc cleanup.

## Verification after rollback

On the reverted tree, confirm the revert is complete by reproducing the pre-fix behaviour in a throwaway copy (`tests._support.project_copy`, never a real checkout): `start_change` again creates a package whose name contains a backslash or a control byte, and `transition(root, '../../outside', 'scoped', …)` again returns status `scoped` while rewriting the foreign `state.json`. Then confirm the rest of the workflow is intact: `scripts/grok_change.py` creates a package for a normal title, `transition` moves it through a legal status, and each `engineering/changes/**/state.json` still parses as JSON whose `change_id` matches its directory name. Close with `python3 scripts/grok_verify.py --mode pr` and the App-owned policy-epoch check on the revert's head SHA.
