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
| P1 | Installer packages valid examples but never manages marker/model/rules, including under force | installer/manifest tests |
| P1 | K16 remains exactly 120 decorative inventory edges and links point to real architecture authority | structure tests |

## Automated checks

- Unit: both architecture modules plus existing root discovery.
- Contract: strict schemas and existing HTTP/envelope baselines.
- Compatibility: M1 spec/receipt behavior and unconfigured installed consumer.
- Static: Ruff, Bandit, compileall, AST fitness, `git diff --check`.
- Integration: `grok_verify --mode pr --no-record --json`, then exact-fingerprint receipts.

## Task 5 command set

```bash
python3 -m unittest -v tests.test_installer tests.test_manifest_package tests.test_structure
python3 scripts/grok_spec.py validate --change-id 20260826-m2-executable-architecture-015603 --gate --json
python3 -m unittest discover -s tests
python3 -m compileall -q .grok-stack/adaptive_grok scripts
python3 scripts/grok_architecture.py diagram --check
python3 scripts/grok_verify.py --mode pr --no-record --json
git diff --name-only 25bfbe59ea188d9687b20a9caad19e7db3d031f8...HEAD -- trust-ci
```

## Manual checks

- Inspect all five generated views and architecture diff for truthfulness.
- Confirm no changed path under `trust-ci/**` relative to the adoption base.
- Confirm docs describe M2-A as local/source-ready only and identify M2-B/deployment gaps.
- Compare receipt `active_architecture_binding` base selection with verification `_architecture_base` on the exact final tree before final review closure.
