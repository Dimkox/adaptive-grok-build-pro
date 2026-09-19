# Rollback plan — durable delivery of the #104 post-merge audit

## Trigger conditions

- Review shows a committed claim that is not reproducible at the SHA it cites (a false certification in prose).
- Evidence turns out to expose machine-local paths, host names or operator detail that should not be public.
- The diff is found to have modified or reordered existing `mistakes.md` content (violates INV-001 / FORBID-003).
- A concurrent owner's in-flight work on the same documents conflicts with the recovered entries.

## Application rollback

Documentation only: revert the single commit (or close the pull request before merge). Nothing to redeploy — no
artifact, service, flag, schema or contract state is involved. One step, matching the typed
`rollback.strategy = forward_fix`, `maximum_steps = 1`.

## Data recovery / forward-fix

No data mutation exists to recover. Two notes specific to a revert:

- The six recovered entries would return to living only in the primary working tree's uncommitted file, i.e. back to
  the loss risk this change removes; so a revert must be followed by re-delivery, not by silence.
- If a claim is wrong, the preferred action is a **forward-fix commit that corrects and labels it** — this package's
  own convention is to keep superseded measurements visible with their cause rather than erase them.

## Verification after rollback

1. `git log --oneline -3` shows the revert/absence of this commit and no other history change.
2. `git diff --stat HEAD -- mistakes.md` is empty and the file still contains every pre-existing entry exactly once.
3. `python3 scripts/grok_verify.py --mode pr` on the rolled-back head is green (it was green before this change, since
   no product file was ever touched).
4. Issue #146 and residuals R1–R4 remain open and unaffected — this package documents them and owns none of their fixes.
