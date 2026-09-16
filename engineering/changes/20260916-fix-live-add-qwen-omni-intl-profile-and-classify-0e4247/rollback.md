# Rollback — qwen-omni-intl profile and probe classification

## Trigger conditions

Evidence that the international endpoint does not sustain the five media classes for the pinned model, or that the probe output change leaks anything the closed contract forbade.

## Application rollback

`git revert` the merge commit: the profile disappears from every enumeration and the probe returns to the two-key output. No data, host state or release record is involved, and no installation ever selected the profile.

## Data recovery / forward-fix

At most one forward step; if the intl model name changes, correct the profile rather than re-point the mainland binding.

## Verification after rollback

- `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_landing_live_executors` green with the added tests removed by the same revert.
- Exact-head App check SUCCESS on the rollback pull request.
