# Test plan — Factory Linux installer from Liqvera prototype

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Unsafe/tampered archive causes zero target/runtime effects | focused unit/acceptance tests |
| P0 | Failed health/update preserves prior pointer and data | lifecycle tests |
| P0 | Purge requires exact target-bound confirmation token | removal tests |
| P1 | Same release is idempotent and status/logs are bounded/redacted | lifecycle tests |

## Automated checks

- Unit: manifest, archive, path, state, token, transition helpers.
- Integration: temporary-root install/update/reversal/removal using a fake runtime adapter.
- Contract: CLI JSON/error/status schema and manifest schema.
- E2E: packaged fixture through verify->stage->health->switch, no live Docker required.
- Static analysis: route `base` and `contracts` profiles.

## Manual checks

- 
