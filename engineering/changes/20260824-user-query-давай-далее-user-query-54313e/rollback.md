# Rollback plan — M0.3 bind main

## Trigger conditions

Docs/tests misstate live GitHub (claim unprotected, or claim PR #5 merged/green).

## Application rollback

Revert the documentation commit on this branch. Do not DELETE GitHub branch protection from an agent unless the user names that operation. Do not re-enable workflow `340420982`.

## Data recovery / forward-fix

Live protection object is outside the PR domain. Restore operator docs from git. Funnel/socat are host-local and must stay up.

## Verification after rollback

`GET branches/main/protection` still shows `app_id` 4694114; PR #5 still unmerged.
