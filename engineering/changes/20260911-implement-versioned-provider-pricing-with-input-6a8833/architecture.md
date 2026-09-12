# Architecture — Implement versioned provider pricing with input, output, reasoning, cached-input and cache-write token accounting plus deterministic cost calculation and durable usage storage.

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
# Architecture

V1 remains its existing aggregate usage protocol. V2 is explicit at the
protocol/API boundary and passes validated `UsageTokens` plus `PriceTableV1`
to the broker. The broker computes the integer micro-USD amount; the store
persists its component breakdown and calculated total atomically.

The price-table digest establishes canonical-content integrity only. Provider
tariff enrollment/provenance is out of this repository change and malformed
or unknown V2 price tables fail closed.

## Bounded implementation budget

The exact priced-usage delivery measures 1,685 factory AST units and 577
factory-test AST units. The two corresponding finite ceilings are calibrated
to 1,700 and 600 units respectively: enough for the measured additive V3
compatibility and PostgreSQL regression coverage, but still bounded. All
other factory, source, contract, line, and byte limits remain unchanged.
