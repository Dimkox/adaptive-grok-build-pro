# Test plan — M2-A Executable Architecture

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Malformed/ambiguous/unsafe architecture input fails closed | `tests/test_architecture_model.py` |
| P0 | Secret/trust/workspace/mixed-change rules cannot be weakened | `tests/test_architecture_fitness.py`, security review |
| P0 | Post-risk cannot fall and exact evidence cannot use the stale route base | fitness tests, verification receipt |
| P1 | Contract/migration/job/network/import/budget categories are explicit and conservative | fitness/model tests, data/test reviews |
| P1 | Diagrams and CLI output are reproducible | model tests, `diagram --check` |
| P1 | Installer never overwrites a target model | installer tests, release review |

## Automated checks

- Unit: both architecture modules plus existing root discovery.
- Contract: strict schemas and existing HTTP/envelope baselines.
- Compatibility: M1 spec/receipt behavior and unconfigured installed consumer.
- Static: Ruff, Bandit, compileall, AST fitness, `git diff --check`.
- Integration: `grok_verify --mode pr --no-record --json`, then exact-fingerprint receipts.

## Manual checks

- Inspect all five generated views and architecture diff for truthfulness.
- Confirm no changed path under `trust-ci/**` relative to the adoption base.
- Confirm docs describe M2-A as local/source-ready only and identify M2-B/deployment gaps.
