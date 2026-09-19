# Test plan — Fix issue #124: require code/test reviewers to perform mutation testing in a private scratch copy outside the reviewed worktree, preserve the reviewed tree as read-only, and report which claims were executed with commands/output plus reviewed-tree-modified:no and scratch path. Update reviewer briefs/templates and tests.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Both code/test briefs prohibit in-tree mutation and require scratch-only mutations | structural tests over reviewer briefs |
| P0 | Reviewer report template requires snapshot/fingerprint, scratch path, commands/results, and `reviewed tree modified: no` | structural test over evidence README/report template |
| P1 | Reviewer TOML configurations preserve read-only sandbox mode | structural test over `.toml` role configs |
| P1 | Trusted parent, permissions, dirty-tree snapshot and before/after fingerprint behavior remain accurately documented | static contract assertions and current implementation behavior probes |

## Automated checks

- Unit: focused structural tests under `tests/test_structure.py` and relevant reviewer/route contract test modules.
- Integration:
- Contract:
- E2E:
- Static analysis:

## Manual checks

-
