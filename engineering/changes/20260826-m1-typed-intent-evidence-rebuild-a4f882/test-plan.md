# Test plan — M1 Typed Intent Evidence Rebuild

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Malformed/unbounded spec and trust-boundary path attacks fail closed | focused validator + holdout tests |
| P0 | Existing signed schema-v1 attestations still verify | model/signing regression tests |
| P0 | Every acceptance criterion is mapped and stale receipts are rejected | receipt/verification tests |
| P1 | Generated spec, CLI JSON, digest, and coverage are deterministic | root unit tests |
| P1 | Complete repository remains green | PR verification + route reviews |

## Automated checks

- Unit: `python3 -m unittest tests.test_change_spec -v` and affected receipt/verification tests.
- Integration: root and Trust CI discovery suites.
- Contract: strict schema subset, CLI output, receipt JSON, attestation serialization/signature replay.
- E2E: `python3 scripts/grok_verify.py --mode pr` and external exact-SHA Trust CI after authorized push.
- Static analysis: compileall plus repository Ruff/Bandit profile.

## Manual checks

- Inspect final diff for accidental secrets, GitHub Actions, root packaging markers, and PR-controlled imports in trusted execution.
