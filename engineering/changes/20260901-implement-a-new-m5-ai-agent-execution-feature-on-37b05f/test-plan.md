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
| P0 | proposal sequence/max-events/terminal monotonicity, structured redaction, allowed paths, trusted artifact attestation | protocol/broker/service + direct `factory_runtime` disposable PostgreSQL tests, including indexed last-sequence/terminal plans |
| P0 | canonical SQL cross-binding, terminal-derived M4 transition, result-row/digest corruption rejection | migration/store + disposable PostgreSQL adversarial tests |
| P0 | two-lane 2..100 raw recovery page, keyset wrap/fairness, 30-second aggregate bound, authoritative tuple, cancel/supersede projection and at-least-once exact-handle fenced cleanup | coordinator/store plus disposable PostgreSQL 17 concurrency/plan tests |
| P0 | actual two-restart runtime/attestor drill retains failure/success history, reclaims with a higher cleanup fence, preserves evidence, rejects late work and fabricates zero proposal/result/attestation | self-contained disposable PostgreSQL 17 restart probe passed at exact checkpoint `3940267`: 273 tests run, 272 passed, one expected fresh-cluster-only skip; session feedback exists, but repository-bound exact-head review/receipts remain pending |
| P0 | byte-identical M4 control and enrolled execution-v1 contracts plus additive execution-v2 have disjoint closed routes; v1/v2 terminal invoke one atomic/resumable service saga and return version-specific projections | root structure, architecture contract, API/service and real PostgreSQL tests |
| P0 | unit topology has fixed commands/users/hardening/limits and no activation path | systemd source parser tests |
| P1 | note/artifact/usage/terminal bounds, redaction, idempotency | broker tests |
| P1 | recovery metrics have zero migration epoch/no backfill, one stable atomic fixed-cardinality snapshot and least-privilege ACL/plan shape | schema upgrade, catalog/ACL, race and forced-generic EXPLAIN tests |
| P1 | installer copies all M5 sources, four schemas and both same-server OpenAPI artifacts without activation/migration/runtime side effects | installer and root structure tests |
| P1 | low-cardinality execution metrics and docs/architecture | integration and root structure tests |

Every behavior follows observed RED -> minimal GREEN -> refactor. No test makes a live provider/network call or reads credentials. PostgreSQL checks require a freshly created isolated PostgreSQL 17 database/container; never reuse Trust CI, reviewer, shared or production state. This host's missing trusted rootless broker/isolation tooling is recorded as a blocked M5 exit, not converted into skipped success.
