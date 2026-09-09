# Architecture — M7 bounded shadow handoff on exact M6 c6d48ff

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Exact M6 exposes deterministic semantic-validation facts but has no M7 handoff bundle or shadow-cohort evaluator. M4 remains control authority, M5 remains execution authority, and M6 remains semantic-verdict authority.

## Proposed behavior

Add an isolated pure M7 layer. It accepts only closed, producer-accurate M4-M6 bridge values, recomputes their nested identities, creates a content-addressed bundle that remains blocked pending durable lookup, and evaluates closed human-outcome facts into a non-operative recommendation.

## Components and boundaries

- `shadow_contracts.py`: immutable bridge, bundle, outcome, and cohort values plus all cross-milestone identity and authority checks.
- `shadow_evaluation.py`: deterministic aggregate recomputation and fixed eligibility thresholds.
- Six JSON Schemas: machine-readable parity for every externally representable M7 input and bundle.
- M4-M6 modules remain upstream fact producers and are not modified. M7 has no store, service, server, provider, broker, credential, or transport adapter.

## Data flow

1. Canonical M4 control, M5 execution, and M6 semantic facts are parsed independently.
2. M7 recomputes verdict, envelope, bridge, evidence, proposal, and bundle identities and rejects stale or invented authority.
3. The pure bundle is emitted as `blocked_pending_durable_lookup` with fixed manual instructions and no external capability.
4. Separately collected, digest-only human outcomes form one exact cohort tuple.
5. The evaluator recomputes the aggregate, applies fixed thresholds, and emits either `blocked` or `eligible_for_human_l2_review`.

## API and event contracts

This phase adds six closed JSON Schema contracts and no HTTP route, event producer, consumer, queue, or database record. Version 1 meanings are additive and do not change existing M4-M6 APIs.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing closed-contract, deterministic evidence, human authority, and external-action isolation rules.
- Applicable canonical example IDs/versions: the six M7 version-1 schemas.
- Open or overdue debt IDs: none created; durable lookup and real-outcome acquisition remain later milestone work.
- Expected governance handoff or receipt impact: full verification and route-selected independent review receipts are deferred beyond this bounded source checkpoint.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Preserve canonical final M7 semantics by importing only the ten proven add-only product paths from `4df2516b`; do not import historical lineage or documentation.
- Treat `blocked_pending_durable_lookup` and `external_capability=absent` as fixed contract values, not runtime flags.
- Require evaluator input to be a validated cohort and recompute its aggregate internally so a caller cannot authorize a recommendation with forged summary metrics.

## Risks and mitigations

- Producer-shape drift: bind separate packet and head identities and recompute M6 verdict and envelope digests.
- Synthetic evidence mistaken for earned autonomy: label all focused fixtures synthetic and make real human outcomes an explicit deferred gate.
- Authority escalation: closed schemas omit remote fields and the only successful recommendation is human level-2 review.
