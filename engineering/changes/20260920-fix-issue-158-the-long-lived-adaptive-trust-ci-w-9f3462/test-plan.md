# Test plan — Fix issue #158: the long-lived adaptive-trust-ci worker accumulates unreaped [git] defunct children (measured 4 over ~24h, NRestarts=0), so every subprocess path must reap on all outcomes including the accepted 'zombie_only' classification; locate the real leak empirically rather than assuming a missing wait, add a test whose control fails on current code, and keep exit-status classification and all attestation/policy semantics untouched.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | | |
| P1 | | |

## Automated checks

- Unit:
- Integration:
- Contract:
- E2E:
- Static analysis:

## Manual checks

- 
