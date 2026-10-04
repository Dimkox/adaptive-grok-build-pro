# Test plan

- Extend `test_agents_md_starts_with_self_learning` (or add a sibling) so it:
  - requires `(ROOT / 'decisions.md').is_file()` and `(ROOT / 'mistakes.md').is_file()`
  - requires `log it in decisions.md` and `record it in mistakes.md` before `## Mandatory entrypoint`
  - fails if the live bullets still say `engineering/decisions.md` / `engineering/mistakes.md`
- Existing heading-order assert (`## Agent self-learning` first) stays.
- Red on current tree, green after the move.
