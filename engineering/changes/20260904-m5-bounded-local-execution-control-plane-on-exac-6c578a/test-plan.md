# Test plan — M5 bounded local execution control plane on exact M4 67dc4dd

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | M4 migrations/control contract and lifecycle remain unchanged | M4 unit, OpenAPI, service and PostgreSQL regressions |
| P0 | Fresh/schema-13 transactional upgrade through `014`-`017` | Focused migration and disposable PostgreSQL 17 tests |
| P0 | Immutable packet/manifest identity and exact replay | Contract, service and persistence tests |
| P0 | Closed offline adapter/protocol boundary | Schema, protocol, adapter and fixture tests |
| P0 | Authentication, repository isolation, owner/role/fence enforcement | API, service and PostgreSQL negative tests |
| P0 | Trusted snapshot/attestation and atomic terminal result | Broker, workspace and persistence tests |
| P0 | Disabled startup and complete-composition fail-closed behavior | Server, API and runtime-capability tests |
| P0 | Bounded factual recovery across two restarts | Recovery and disposable PostgreSQL restart tests |
| P1 | Additional provider versions, fleet/load tuning, retention and broader defense-in-depth | Optimization backlog; not a reopening condition |

## Automated checks

- Unit: execution contracts, protocol, adapters, brokers, workspace, recovery, models, service, API and server.
- Integration: isolated disposable PostgreSQL 17 for migrations, roles, persistence, finalization, races, cleanup and two real restarts; no shared database.
- Contract: exact M4 17-operation document plus separate closed execution v1/v2 documents and four JSON Schemas.
- E2E: deterministic local claim-to-terminal and stale-run recovery with injected trusted profiles/brokers only.
- Static analysis: route-selected base/contracts/data/AI profiles and architecture fitness on the frozen tree.

## Manual checks

- Confirm no shipped adapter exposes invocation, subprocess, credential, network, or fallback capability.
- Confirm execution-disabled startup retains the complete M4 UDS surface and execution-enabled startup rejects incomplete composition before socket exposure.

## Stop rule

Block only for a reproducible core-flow failure, authority or tenant-isolation bypass, data loss/corruption, or mandatory verifier failure. Record other findings once for later optimization without repeating the acceptance cycle.
