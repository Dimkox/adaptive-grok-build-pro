# Test Plan — M9 Staged Delivery and Recovery

The source-only checkpoint runs each scenario under strict TDD; a scenario is claimed only after its witnessed RED and fresh GREEN evidence.

Task 1 contract evidence is implemented: the exact command first failed because `adaptive_delivery.contracts` was absent, then passed 11 tests after the minimal contract module was added. Task 2 evaluator evidence is implemented from missing-evaluator and old-window/fresh-capture REDs; three bounded-input cases now bring its focused suite to 16 tests. Task 3 recovery evidence is implemented from a missing-module RED followed by 9 tests for exact binding, least-authority action selection, same-stage decrease, exact prior artifact and decision-time expiry. Task 4 controller evidence now has 31 tests: its review-remediation RED reproduced ordinary adapter/evidence mutation, global class patching, a two-thread duplicate append, unwitnessed import, contradictory recovery reasons, record-time expiry and unbounded sequence materialization. All 67 source-only tests pass; Task 5 schema/architecture/repository integration remains pending and blocked.

| Priority | Scenario | Required evidence |
| --- | --- | --- |
| P0 | every closed record rejects unknown/missing fields, malformed SHA/digests, noncanonical time, bad exposure and unbound authority | contract unit + JSON Schema tests |
| P0 | exact artifact/SBOM/provenance/M8 profile/cohort/policy/holdout/image/environment/prior-artifact mismatch denies | table-driven evaluator tests |
| P0 | missing, stale, duplicate, contradictory, nonfinite or reordered observations deterministically deny with stable sorted reasons | property/table unit tests |
| P0 | each health/error/latency/security/business threshold passes at boundary and denies one unit beyond | evaluator unit tests |
| P0 | state order is preview→staging→bounded canary→needs_human; no skip, reverse or production method | controller/adapter tests |
| P0 | recovery only halts, selects an earlier same-stage exposure, or restores the exact bound prior artifact | recovery mutation tests |
| P0 | concurrent identical steps append/apply once; reviewed adapter and private tuple surfaces fail closed on ordinary mutation | controller concurrency and mutation tests |
| P0 | record-time promotion/current/prior-artifact expiry prevents effect and evidence | controller authority-boundary tests |
| P0 | non-empty prior chains fail closed until independently witnessed; digest-only evidence cannot authorize restart | controller import tests |
| P0 | authority remains opaque and source contains no crypto/key/network/subprocess/provider/connector/production path | structure + security scans |
| P1 | observation, evidence and fake-effect collections are independently capped at 128 without generator/unbounded iteration | evaluator/controller unit tests |
| P1 | metrics/audit expose only closed labels, digests, times and aggregates, never bodies/PII/secrets | redaction/contract tests |
| P1 | schemas, architecture inventory/diagrams, README and roadmap remain consistent | repository structure/architecture tests |

## Focused commands

```bash
PYTHONPATH=delivery/src python3 -m unittest discover -s delivery/tests -p 'test_*.py' -v
python3 -m unittest delivery.tests.test_evaluator delivery.tests.test_recovery -v
python3 scripts/grok_architecture.py validate
python3 scripts/grok_architecture.py diagram --check
python3 scripts/grok_verify.py --mode pr
```

No test may generate or verify a signature, contact a network, execute a command, create an environment or claim recovery proof. Opaque authority fixtures contain only bounded reference fields and externally verified status is not simulated by repository cryptography.
