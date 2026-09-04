# Architecture — M8 earned autonomy on exact M7 00e0e4f

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Exact M7 provides immutable blocked handoff bundles and deterministic shadow outcomes/cohort evaluation. It deliberately has no durable acceptance/currentness authority and grants no operational capability.

## Proposed behavior

Add a pure M8 layer that consumes the actual M7 records through a thin bridge, binds them to closed factual task evidence, computes a bounded profile and one-level recommendation, and supports deterministic fail-closed L0 demotion. No runtime activation is added.

## Components and boundaries

- `m7_autonomy_bridge.py`: validates an M8-owned provider mapping, parses actual M7 bundles/cohort, recomputes the M7 aggregate/evaluation, enforces one-to-one sorted identities, and permanently reports acceptance/currentness unavailable.
- `autonomy.py`: owns only M8 tuple, cohort evidence, profile, recommendation, and demotion semantics.
- `m7-autonomy-bridge.v1.schema.json`: a closed envelope that references existing M7 schemas rather than copying producer definitions.
- `earned-autonomy.v1.schema.json`: closed M8 record shapes and bounds.
- No store, service, API, broker, provider adapter, database, background process, credential, or network client is introduced.

## Data flow

1. Actual M7 bundles and one cohort are parsed and their producer identities recomputed.
2. M8 provider mapping is checked against the M7 cohort key while provider and validator identities remain separate.
3. Closed task evidence binds each bundle/outcome pair to task, run, exact result head, human receipt, attestation, time, quality, safety, cost, and latency facts.
4. Evaluation builds a fresh profile, applies fixed gates in deterministic order, and emits only a one-level recommendation requiring separate activation.
5. A demotion trigger independently selects the highest-priority fact and returns a halted L0 profile plus a non-operative decision.

## API and event contracts

This phase adds two version-1 JSON Schemas and no HTTP operation or event. The bridge references the six canonical M7 schema IDs and accepts no M7 aggregate/evaluation, acceptance, or currentness assertion from callers.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: closed-contract, deterministic evidence, local factory isolation, and human activation boundaries.
- Applicable canonical example IDs/versions: M7 six version-1 schemas plus M8 bridge and earned-autonomy version 1.
- Open or overdue debt IDs: none created; factual cohort collection and activation are explicitly deferred milestone work.
- Expected governance handoff or receipt impact: exact-head verification and route-selected reviews/receipts remain deferred beyond the bounded source checkpoint.

## Bitrix-specific impact

- Modules/events/agents/components affected: none.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: none.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Do not import canonical `m7_autonomy_wire.py`; replace it with a thin bridge over the actual M7 classes and evaluator.
- Serialize only bridge inputs. M7 aggregate and evaluation are recomputed properties and cannot be supplied by a caller.
- Keep both external acceptance and currentness hard-unavailable, so synthetic/local source cannot qualify or activate autonomy.

## Risks and mitigations

- Duplicated producer authority: eliminated through imports and external schema references to actual M7 contracts.
- Synthetic evidence mistaken for autonomy: blocked M7 bundle and unavailable acceptance/currentness prevent qualification; documentation labels fixtures synthetic.
- Authority escalation: L2 ceiling, one-level recommendation, separate activation, no external-action flag, and deterministic L0 halt are fixed contracts.
