# Requirements — Fix incomplete Grok port

## Acceptance criteria

- [x] Given a clean checkout, when `python3 -m unittest discover -s tests` runs, then all tests pass (80/80)
- [x] Given a clean checkout, when `python3 scripts/grok_doctor.py` runs, then there are no FAIL items
- [x] Given `python3 scripts/install_into.py <target>`, when the target has a custom `.grok/agents/custom.toml`, then that file remains and managed agents/config are installed
- [x] Given a conflicting `.grok/config.toml`, when install runs without `--force`, then it exits non-zero
- [x] Given UserPromptSubmit with a Bitrix bug prompt, when the hook runs, then an active route is written and stdout contains `ADAPTIVE CODEX ROUTE`
- [x] Given PreToolUse for `terraform destroy`, when the hook runs, then permission is denied
- [x] Given Stop without receipts, when the hook runs, then the stop is blocked for missing/stale evidence
- [x] Given `.env`, when git status is checked, then it stays untracked

## Failure and edge cases

- Follow-up prompts (`делай`) reuse the active route
- `project_copy` must not leak this workspace's runtime route into harness copies
- Hook stdin accepts both snake_case and camelCase envelopes

## Non-functional requirements

- Security: PreToolUse continues to block secrets, Bitrix core, destructive git, unapproved production/MCP writes
- Reliability: hook scripts exit 0 with JSON even when there is no active route (except Stop gate)
- Observability: doctor lists each managed agent/skill
