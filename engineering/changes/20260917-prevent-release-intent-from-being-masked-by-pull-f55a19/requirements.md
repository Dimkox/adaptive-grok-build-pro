# Requirements — Release intent classification (#123)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Acceptance criteria

- [x] Release prompt pairs with and without `pull request` wording retain identical high-risk release gates, reviewers, evidence, and skills.
- [x] Explicit review prompts including “review pull request” remain reviews.
- [x] A release installer bugfix remains a bugfix if it mentions a PR.
- [x] Route schema remains v1.

## Failure and edge cases

- Prompt mentions merged pull requests as a report detail but is still a release task: release intent wins over delivery wording.
- Prompt explicitly asks to review a PR and does not ask for release: review intent remains.
- Prompt asks to fix release installer behavior: bugfix precedence remains.
- Prompt matches multiple intents: never remove risk-bearing release controls solely because a delivery keyword appeared.

## Governance context

The route is workflow selection metadata. Local grants and the deployed App-owned Trust CI check remain separate controls; this change does not enforce or change them.

## Non-functional requirements

- Security: release tasks retain existing high-risk review and human-gate metadata.
- Reliability: table-driven tests assert the complete route contract.
- Compatibility: no serialized route schema change.
- Observability: route context continues to print the retained gates and selected intent.
