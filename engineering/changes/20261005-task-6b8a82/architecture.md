# Architecture — Design public self-service Trust CI GitHub App for any installing repository worldwide: REST API/webhook authentication, tenant isolation, repository-scoped installation tokens and selected trusted verification profiles, per-tenant quotas and rollback. Architectural scope; analyze before implementation. Existing hosted deployment, policy, holdout, GitHub App registration and branch protection stay unchanged until exact separate operational delegation and external approvals. No GitHub Actions, no broad wildcard authorization, no secret/key reads.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

## Proposed behavior

## Components and boundaries

## Data flow

## API and event contracts

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

## Risks and mitigations
