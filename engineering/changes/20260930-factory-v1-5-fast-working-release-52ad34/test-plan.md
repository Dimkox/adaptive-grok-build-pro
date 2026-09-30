# Test plan — Factory v1.5 fast working release

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Closed schemas remain compatible and new contracts reject unsafe/unknown input | contract/unit suites |
| P0 | Decision/result replay is idempotent and state evidence stays bound | unit/PostgreSQL integration |
| P0 | Qualification never reports Apple/M8/external trust as passed | contract/API tests |
| P1 | Context digest is deterministic and bounded | context contract tests |
| P1 | ML artifacts are observation-only and honestly not qualified | prediction tests |

## Automated checks

- Unit: new context/decision/result/prediction/qualification modules.
- Integration: store transaction and API composition; PostgreSQL when capability exists.
- Contract: every new JSON Schema plus old-reader regression.
- E2E: one synthetic intake-to-qualification trace with unavailable external authority.
- Static analysis: route `base` and `contracts` profiles through `grok_verify`.

## Manual checks

- Inspect generated qualification JSON and release report for explicit exclusions/deferred gates.
