# Test plan — Implement new Factory runtime behavior for bounded pre-model result envelopes and deterministic result-channel sanitization, based on source commit aa53f300d and stacked on PR2c; add the closed schemas, Python feature modules and regression tests, excluding persistence and dispatch from this slice

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Structured Authorization/nested canary never escapes | Result broker tests and mutation review |
| P0 | Duplicate keys and invalid/unbounded limits fail closed | Result broker tests |
| P0 | Every runtime channel is unavailable and non-consuming | Result broker tests |
| P1 | Envelope and qualification structural/semantic parity | Factory/root schema tests |
| P1 | Existing PR2c/persistence behavior is unchanged | Full PR verifier including PostgreSQL |

## Automated checks

- Unit: focused result broker and semantic contract suites.
- Integration: architecture/inventory bindings and unchanged predecessor pins.
- Contract: both Draft 2020-12 schemas plus Python semantic admission.
- E2E: full `grok_verify.py --mode pr` on final stacked tree.
- Static analysis: architecture, governance, ruff, bandit and secret scan.

## Manual checks

- Inspect final diff against `aa53f300d^..aa53f300d` and confirm source hazards are repaired rather than copied.
