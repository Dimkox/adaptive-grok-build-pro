# Test plan — Implement versioned provider pricing with input, output, reasoning, cached-input and cache-write token accounting plus deterministic cost calculation and durable usage storage.

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
# Test plan

1. Pure pricing: canonical digest, exact rates, zero cache and floor division.
2. V1 replay remains accepted unchanged; V2 rejects forged totals and malformed
   price tables.
3. Broker idempotency includes every token component and calculated cost.
4. Migration/persistence preserves old rows and saves V2 cache components.
5. Contract/API tests expose V2 fields; full PR verifier runs after final docs.
