# Test plan

- New: `test_agents_md_starts_with_self_learning` in `tests/test_structure.py`.
- Assert the first `##` heading is the self-learning section.
- Assert `engineering/decisions.md` and `engineering/mistakes.md` appear before `## Mandatory entrypoint`.
- Assert the two user-required verbs: log a worth-the-effort decision (≤ 3 sentences); record a mistake by root cause, not symptom.
- Existing structure tests must still pass.
