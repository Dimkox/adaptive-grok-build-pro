# Rollback plan — issue #218 clean squash delivery

## Before commit

Abort by discarding this isolated worktree/index candidate through a separately authorized recoverable operation; source branch `68dfc70c...` and all predecessors remain untouched.

## After local commit, before external delivery

Delete or abandon only the isolated delivery branch, preserving the source branch and evidence. Do not rewrite a shared or protected branch.

## After delivery

Use a reviewed revert of the single squash candidate. No database, migration, deployed policy, Trust CI state, secret material, or external runtime recovery is involved.

## Verification after rollback

Confirm base tree identity, absence of candidate paths, clean worktree/index, and unchanged source refs. Never weaken scanners as rollback.
