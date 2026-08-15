# Release notes — Repair stale-route lockout and policy path matching

Library + hook + test change. No migration, no VERSION bump, no package.

- Next UserPromptSubmit picks up rematch and child-skip.
- Next PreToolUse picks up invocation matching.
- Leftover `active-route.json` is overwritten on the next non-follow-up user prompt.

Do not tag, merge, or upload artifacts as part of this change.
