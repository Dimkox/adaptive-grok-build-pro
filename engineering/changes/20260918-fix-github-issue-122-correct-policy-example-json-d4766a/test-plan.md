# Test plan — Fix GitHub issue #122: correct policy.example.json/runbook language so it clearly distinguishes illustrative approval scopes from deployed Trust CI policy and identifies where the active policy epoch is observed. Do not change deployed policy or Trust CI.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Runbook labels copied policy example as illustrative and links to live epoch verification | Structural documentation test and diff review |
| P1 | Dated activation report is marked historical and does not claim current state | Structural documentation test |
| P1 | Example JSON remains valid and unchanged in approval scope | JSON parse, repository diff review |

## Automated checks

- Unit: focused `tests.test_structure` regression.
- Integration: not applicable; no runtime behavior changes.
- Contract: parse `trust-ci/config/policy.example.json`; confirm unchanged.
- E2E: not applicable.
- Static analysis: `git diff --check`, route-selected PR verifier.

## Manual checks

- Review the operator wording does not imply `/health/ready` returns policy contents or that an old report is live.
