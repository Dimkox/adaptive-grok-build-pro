# Requirements — Fix GitHub issue #122: correct policy.example.json/runbook language so it clearly distinguishes illustrative approval scopes from deployed Trust CI policy and identifies where the active policy epoch is observed. Do not change deployed policy or Trust CI.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] The rollout instructions warn beside the sample-copy command that `policy.example.json` is illustrative and does not establish deployed approval scopes.
- [ ] The operator path links to the authenticated deployed-policy handoff and compares normalized `Policy.digest` with `/health/ready` `policy_digest`, then verifies the exact App-owned Check Run on the exact target SHA.
- [ ] The 2026-08-24 activation report is labeled historical, with instructions to re-verify current policy epoch and check state.
- [ ] Regression tests assert these documentation boundaries; sample policy remains valid JSON.
- [ ] No Trust CI source behavior, sample approval rules, deployed policy, holdout, trust store, or branch protection changes.

## Failure and edge cases

- `/health/ready` gives the policy digest, not the policy document; obtain the deployed document through the authenticated human-owned handoff described by Trust CI documentation.
- A historic digest/check name can be valid for its dated report while stale for current operation; never present it as a live value.
- The repository sample digest or past merged PRs do not establish current deployed scopes.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none identified by the analysis wave.
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
