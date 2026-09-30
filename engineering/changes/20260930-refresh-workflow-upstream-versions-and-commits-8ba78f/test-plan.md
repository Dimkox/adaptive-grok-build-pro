# Test plan — Refresh workflow upstream versions and commits

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Stable tag/peeled commit and observed main cannot be conflated; README agrees with config. | `WorkflowSourceContractTests` |
| P0 | Current/old documents create no authority or eligible receipt. | Current samples plus adversarial tests |
| P1 | Spec Kit phase and parallel markers preserve dependencies; stable BMAD nested tasks parse. | `CurrentUpstreamFormatTests` |
| P1 | Superpowers Spec pointers stay opaque; BMAD main without tasks stays advisory. | Exact-revision characterization tests |

## Automated checks

- Focused: `python3 -m unittest tests.test_workflow_sources tests.test_workflow_artifacts tests.test_workflow_artifacts_adversarial -q`.
- Repository: `taskset -c 0-27 python3 scripts/grok_verify.py --mode pr`; inventory includes executable test/config paths outside the closed focused scope, so full PR scope is required.
- Review: coordinator dispatches both route-selected independent reviewers after verification.

## Manual checks

- Public source excerpts checked against immutable upstream raw URLs listed in `evidence/upstream-provenance.md`.
