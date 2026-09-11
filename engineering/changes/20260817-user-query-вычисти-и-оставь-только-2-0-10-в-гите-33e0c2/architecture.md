# Architecture — clean to 2.0.10

No product behavior change. Working tree must match `975ccb2` plus this package’s own files if they stay untracked.

Commands (path-limited):

```bash
git restore -- \
  engineering/changes/20260816-system-reminder-background-subagent-01a00cea-6b8-70b284/state.json \
  engineering/changes/20260816-the-user-sent-a-message-while-you-were-working-u-e61f9d/state.json
# plus the 8fe260 state.json
# then rm untracked sibling evidence files only
```

Do not `git clean -fd` at repo root.
