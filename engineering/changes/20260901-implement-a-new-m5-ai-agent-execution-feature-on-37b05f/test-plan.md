# Test Plan — M5 Isolated Provider Execution

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | packet immutability, canonical digest, closed authority/provider/profile/policy/plan/limits | contract unit tests + JSON Schema fixtures |
| P0 | malformed/flooding/reasoning/identity/sequence/terminal JSONL | protocol adversarial unit tests |
| P0 | Codex/Grok exact-version native normalization and no fallback/live call | fixture conformance tests |
| P0 | traversal/symlink/shared-Git/credential/egress/cross-task/external-write denial | fake workspace/runtime adversarial tests |
| P0 | execution claim differs from legacy claim; fence/stage/proposal/orphan checks | service/API/store tests and additive migration checks |
| P0 | unit topology has fixed commands/users/hardening/limits and no activation path | systemd source parser tests |
| P1 | note/artifact/usage/terminal bounds, redaction, idempotency | broker tests |
| P1 | restart reconciliation is bounded, ordered and idempotent | fake store/recovery tests |
| P1 | low-cardinality execution metrics and docs/installer/architecture | integration and root structure tests |

Every behavior follows observed RED -> minimal GREEN -> refactor. No test makes a live provider/network call or reads credentials. PostgreSQL/container checks run only where the existing disposable harness is available; this host's missing rootless isolation tooling is recorded as a blocked M5 exit, not converted into a skipped success.
