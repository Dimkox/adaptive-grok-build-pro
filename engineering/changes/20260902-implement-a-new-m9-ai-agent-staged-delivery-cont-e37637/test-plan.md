# Test Plan — M9 Staged Delivery and Recovery

The source-only checkpoint runs each scenario under strict TDD; a scenario is claimed only after its witnessed RED and fresh GREEN evidence.

Task 1 contract evidence is implemented: the exact command first failed because `adaptive_delivery.contracts` was absent, then passed 11 tests after the minimal contract module was added. Task 2 evaluator evidence is also implemented: its focused command first failed because `adaptive_delivery.evaluator` was absent; a review-found old-window/fresh-capture case then failed against capture-only freshness; the repaired evaluator passes 13 focused tests plus the unchanged 11 contract tests. Task 3 recovery evidence is implemented from a missing-module RED followed by 9 tests for exact binding, least-authority action selection, same-stage decrease, exact prior artifact and decision-time expiry. Controller and Task 5 integration scenarios remain pending.

| Priority | Scenario | Required evidence |
| --- | --- | --- |
| P0 | every closed record rejects unknown/missing fields, malformed SHA/digests, noncanonical time, bad exposure and unbound authority | contract unit + JSON Schema tests |
| P0 | exact artifact/SBOM/provenance/M8 profile/cohort/policy/holdout/image/environment/prior-artifact mismatch denies | table-driven evaluator tests |
| P0 | missing, stale, duplicate, contradictory, nonfinite or reordered observations deterministically deny with stable sorted reasons | property/table unit tests |
| P0 | each health/error/latency/security/business threshold passes at boundary and denies one unit beyond | evaluator unit tests |
| P0 | state order is preview→staging→bounded canary→needs_human; no skip, reverse or production method | controller/adapter tests |
| P0 | recovery only halts, selects an earlier same-stage exposure, or restores the exact bound prior artifact | recovery mutation tests |
| P0 | authority remains opaque and source contains no crypto/key/network/subprocess/provider/connector/production path | structure + security scans |
| P1 | evidence chain is contiguous, digest-bound, replay-safe and capped at 128 | controller unit tests |
| P1 | metrics/audit expose only closed labels, digests, times and aggregates, never bodies/PII/secrets | redaction/contract tests |
| P1 | schemas, architecture inventory/diagrams, README and roadmap remain consistent | repository structure/architecture tests |

## Focused commands

```bash
python3 -m unittest discover -s delivery/tests -p 'test_*.py' -v
python3 -m unittest delivery.tests.test_evaluator delivery.tests.test_recovery -v
python3 scripts/grok_architecture.py validate
python3 scripts/grok_architecture.py diagram --check
python3 scripts/grok_verify.py --mode pr
```

No test may generate or verify a signature, contact a network, execute a command, create an environment or claim recovery proof. Opaque authority fixtures contain only bounded reference fields and externally verified status is not simulated by repository cryptography.
