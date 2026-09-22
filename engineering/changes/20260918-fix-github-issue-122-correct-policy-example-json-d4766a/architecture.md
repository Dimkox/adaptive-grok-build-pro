# Architecture — Fix GitHub issue #122: correct policy.example.json/runbook language so it clearly distinguishes illustrative approval scopes from deployed Trust CI policy and identifies where the active policy epoch is observed. Do not change deployed policy or Trust CI.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

`engineering/runbooks/trust-ci-rollout.md` copies `trust-ci/config/policy.example.json` to `runtime/policy.json` without an adjacent statement that the file is only a sample. `trust-ci/README.md` already says the example is illustrative and documents a stronger current-epoch check: compare the normalized digest of an authenticated deployed-policy handoff with `/health/ready`, then independently inspect the exact App-owned check in GitHub. `engineering/runbooks/trust-ci-activation-report.md` is explicitly dated 2026-08-24 but reports a check as `main`'s protected requirement in present tense.

## Proposed behavior

Keep policy sample data and Trust CI implementation untouched. Add a caveat beside the rollout copy command, link to the existing operator-safe verification procedure, and label the activation report as a historical snapshot with a current-state re-verification instruction.

## Components and boundaries

- Documentation surfaces: rollout runbook, Trust CI operator README, dated activation report, and a structural documentation test.
- Trust CI source/deployed authority: unchanged. The example JSON is not evidence of server policy; only the authenticated handoff and deployed health digest establish the current epoch.

## Data flow

Human administrator transfers the deployed policy through the authenticated human-owned channel -> operator computes canonical `Policy.digest` -> operator compares it with `/health/ready` `policy_digest` -> operator verifies the required App-owned check and owner on the exact GitHub SHA.

## API and event contracts

No API changes. `/health/ready` is referenced only as an existing read-only health endpoint.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none identified by the analysis wave.
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Do not edit the sample approval rules or claim they differ from current deployed policy; the current deployment was not freshly read. Clarify their illustrative status and document the existing operator verification path.

## Risks and mitigations
