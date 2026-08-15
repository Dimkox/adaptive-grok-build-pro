# Requirements

- [x] Given a started agent, when SubagentStop runs once, then the agent leaves `active` and stdout is `{}` (no additionalContext)
- [x] Given the same agent_id, when SubagentStop runs again, then stdout is `{}` and history contains exactly one `stop` for that id
- [ ] Existing `test_subagent_lifecycle_is_recorded` stays green (start still records; stop still clears active)
