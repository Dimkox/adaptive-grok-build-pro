# Architecture — M3-M9 production delivery continuation

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

M2-A is locally source-ready. M3 contains only an uncommitted partial Task 1 and one focused test is red. M4 has a plan but no `factory/`; M5–M9 are design/roadmap only.

## Proposed behavior

Complete M3 as a repository-local intent-plane validator and publish a closed, exact-state governance handoff. Continue later milestones only in roadmap order and separate PRs.

## Components and boundaries

- M3 governance registries are untrusted repository input.
- The M3 validator owns schema, lifecycle, conflict, digest, projection, and handoff logic; it owns no runtime service or external capability.
- M4 PostgreSQL factory state remains separate from `trust_ci.*` and consumes versioned M1/M2/M3 handoffs.
- M5 adapters and workspaces remain behind capability brokers; M6 validation is independent; M7 shadow evidence precedes M8 autonomy; M9 delivery never expands merge or production authority.

## Data flow

`candidate registries → bounded validation → deterministic governance digest → exact GovernanceHandoffV1 → M4 intake gate`. Later: `protected merge → signed preview → staging → signed promotion request → canary metrics → human production promotion or automatic halt/rollback`.

## API and event contracts

- M3: four closed JSON schemas and `GovernanceHandoffV1`.
- M4+: contracts are introduced only by their own milestone specs and PRs.

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Complete M3 before creating M4–M9 implementation branches.
- Restore the missing reviewed factory design before using the M3 plan.
- Treat the user's current message as scope/design approval for continuation, not external Trust CI or production authority.

## Risks and mitigations

- Divergent local milestone branches: merge only through exact-SHA PR checks after rebasing on protected main.
- Unproven dirty Task 1: recover with focused RED/GREEN evidence and independent review.
- Scope collapse: one milestone per branch/PR and an explicit handoff gate.
- Production impact: M3 has none; later production operations require exact delegated actions and rollback evidence.
