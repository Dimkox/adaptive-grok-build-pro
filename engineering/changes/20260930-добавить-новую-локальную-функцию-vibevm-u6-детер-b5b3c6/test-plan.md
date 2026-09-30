# Test plan — Добавить новую локальную функцию VibeVM U6: детерминированный package graph resolver, lock cache offline replay, bounded unpack projection, boot checks, atomic generations, scoped caches, export fallback и тесты

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Resolver/cache/materializer rejects cycle, conflict, digest/origin/revocation, missing offline bytes and archive escape/bounds | `factory/tests/test_vibevm_runtime.py` |
| P0 | Atomic generation compare-and-swap, frozen snapshots and qualified rollback | `factory/tests/test_vibevm_runtime.py` |
| P1 | Idempotent boot reconciliation, tenant isolation and native export/fallback | `factory/tests/test_vibevm_runtime.py` |

## Automated checks

- Unit: resolver, identity and boot behavior.
- Integration: real temporary filesystem cache, ZIP projection, generations and rollback.
- Contract: JSON Schema validation and closed exported generation document.
- E2E:
- Static analysis: route verifier.

## Manual checks

- None for the source-only default-off contour; live CLI qualification remains out of scope.
