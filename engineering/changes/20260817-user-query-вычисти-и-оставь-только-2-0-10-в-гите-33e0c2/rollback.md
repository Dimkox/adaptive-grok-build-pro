# Rollback

Uncommitted deletes only. Recover from `git status` / reflog is unnecessary if nothing was committed.

If a tracked file was restored: `git restore` already put HEAD back.

Do not force-push.
