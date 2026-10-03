# Rollback plan — Fix issue123 router intent precedence: explicit operational intent survives pull-request and review wording; exclude negated quoted and historical mentions and preserve ordinary routes.

## Trigger conditions

Wrong operational selection, lost ordinary route compatibility or weakened reviewer/evidence/gate obligations discovered during review or aggregate acceptance.

## Application rollback

Before merge, repair the isolated B branch and repeat verification/review. After merge, revert the responsible B PR through a new pull request; do not rewrite shared history or edit the preserved dirty source worktree.

## Data recovery / forward-fix

No persistent data migration or deployed-system action. One source forward fix or PR revert restores the prior router behavior; runtime grants/receipts must be regenerated for the new exact tree.

## Verification after rollback

Run router/hooks/reasoning compatibility plus full PR verification and independent selected reviews. Retain external exact-head Trust CI and signed approval requirements for merge.
