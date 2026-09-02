# Test Plan — M5 Isolated Provider Execution

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | packet immutability, canonical digest, closed authority/provider/profile/policy/plan/limits | contract unit tests + JSON Schema fixtures |
| P0 | malformed/flooding/reasoning/identity/sequence/terminal JSONL | protocol adversarial unit tests |
| P0 | Codex/Grok exact-version native normalization and no fallback/live call | fixture conformance tests |
| P0 | traversal/symlink/shared-Git/credential/egress/cross-task/external-write denial | fake workspace/runtime adversarial tests |
| P0 | execution claim differs from legacy claim; fence/stage/proposal/orphan checks | service/API/store tests and additive migration checks |
| P0 | caller selection cannot assert eligibility/profile/policy/plan; exact trusted registry and role capabilities gate before claim | adapter/service tests |
| P0 | packet/start failure releases the M4 lease and capacity; forged grant role differs from durable run and fails closed | service tests + disposable PostgreSQL role regression |
| P0 | proposal sequence/max-events/terminal monotonicity, structured redaction, allowed paths, trusted artifact attestation | protocol/broker/service + disposable PostgreSQL tests |
| P0 | canonical SQL cross-binding, terminal-derived M4 transition, result-row/digest corruption rejection | migration/store + disposable PostgreSQL adversarial tests |
| P0 | execution orphan/cancel cleanup cannot leave M5 rows, capacity, or factual result in an ambiguous state | reconciliation/restart PostgreSQL tests |
| P0 | every execution request/response/event/nested object is closed and inventoried | JSON Schema/OpenAPI/architecture contract tests |
| P0 | byte-identical retained M4 control baseline plus additive execution OpenAPI inventories exactly six disjoint `/v1/execution/*` operation IDs, 6 required JSON bodies, 18 required request headers, 48 explicit response variants, 6 success correlation headers and 16 closed reachable component schemas | root structure + conservative architecture comparator tests |
| P0 | recovery emits one orphan stage/event only, cleans workspace first, preserves attestation/result tables and is keyset/idempotency safe | fake recovery + disposable PostgreSQL + actual restart probe |
| P0 | unit topology has fixed commands/users/hardening/limits and no activation path | systemd source parser tests |
| P1 | note/artifact/usage/terminal bounds, redaction, idempotency | broker tests |
| P1 | restart reconciliation is bounded, ordered and idempotent | fake store/recovery tests |
| P1 | low-cardinality execution metrics and docs/installer/architecture | integration and root structure tests |
| P1 | installer copies all M5 sources, four schemas, both same-server OpenAPI artifacts, fixtures/tests and exactly four inert units without activation/migration/runtime side effects | installer parity tests |

Every behavior follows observed RED -> minimal GREEN -> refactor. No test makes a live provider/network call or reads credentials. PostgreSQL/container checks run only where the existing disposable harness is available; this host's missing rootless isolation tooling is recorded as a blocked M5 exit, not converted into a skipped success.
