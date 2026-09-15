# Rollback plan — fix(verify): reject same-inode CAS tampering by content digest, not by filesystem ctime granularity

## Trigger conditions

- A future change to the CAS makes one of these two scenarios pass while the product silently accepts a same-inode content change (i.e. the digest comparison stops firing).
- A reviewer shows that the removed ctime precondition was in fact load-bearing for detecting a specific attack that the expected-digest comparison does not cover.

## Application rollback

`git revert` this single commit. It changes only `tests/test_workflow_artifacts_adversarial.py`, `mistakes.md` and this change package, so reverting restores the previous test exactly and touches no product behavior, no schema and no runtime state.

## Data recovery / forward-fix

No migration, no stored-state and no external effect is involved, so there is nothing to recover. If the rollback is needed because a real detection gap was found, the forward fix is a stronger test plus a product repair in `.grok-stack/adaptive_grok/workflow_artifacts.py` under its own change package — not a re-addition of the timestamp precondition, which cannot be satisfied on every supported filesystem.

## Verification after rollback

- `python3 -m unittest tests.test_workflow_artifacts_adversarial` reflects the reverted expectations.
- `python3 scripts/grok_verify.py --mode pr` PASS on the rolled-back tree.
- The App-owned `adaptive-trust-ci/verified@06ecf1c875bc` check SUCCESS on the rollback pull-request head before merging.
