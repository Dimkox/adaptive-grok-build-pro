# Test plan — Implement restart-safe qualified native result dispatch

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Composite identity mismatch, stale authority, duplicate claim and post-send crash never dispatch twice | Real PostgreSQL contention/restart tests |
| P0 | Malformed/duplicate/oversize/non-JSON/unbound response never becomes delivered | UDS client tests |
| P1 | Default-off configuration, private token/socket, timeout/lease margin and least privilege | Unit and PostgreSQL ACL tests |
| P1 | Admission stays dormant and all seven channels unavailable | Admission/schema tests |

## Automated checks

- Unit: result dispatcher/client/settings.
- Integration: migration 025, capability ACL, SKIP LOCKED, fences, finite budgets.
- Contract: qualification v2 and internal native-result-handoff v1 JSON Schemas.
- E2E: real UDS POST; PostgreSQL crash/restart followed by GET only.
- Static analysis: Ruff, architecture fitness, SQL safety and full PR verifier.

## Manual checks

- Confirm no TCP/provider/model dependency and no automatic outbox writer exists.
