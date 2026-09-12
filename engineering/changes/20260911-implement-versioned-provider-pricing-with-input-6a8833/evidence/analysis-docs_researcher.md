# Documentation and consumer-compatibility analysis

Route `6a88338ed69e`; read-only documentation/contract research. No product
files were changed.

## Current published contract surfaces

- `factory/contracts/openapi/factory-execution.v1.json` and
  `factory/contracts/openapi/factory-execution.v2.json` are the checked
  execution contracts. Both currently define `UsageProposal` and
  `UsageProposalRequest` with `price_table_digest`, input/output/reasoning
  token counts, a caller-supplied `cost_usd_micros`, and `output_bytes`.
  The v2 document is routed under `/v2/execution/*`, but its usage schema is
  not yet materially different from v1.
- `factory/src/adaptive_factory/protocol.py` has one event name,
  `usage.reported`, with an exact closed field set. There is no documented
  protocol-level v2 usage event/version discriminator. The two adapter
  translators (`adapters/codex.py` and `adapters/grok.py`) emit that same
  event, and their fixtures encode the legacy caller-cost shape.
- `factory/README.md` states that `/v1/execution/*` and `/v2/execution/*`
  expose six operations each and that v1/v2 are reviewed separately; it also
  describes runtime OpenAPI as disabled. This is the appropriate operator
  documentation anchor, but it currently says nothing about usage schema
  negotiation, cache-token buckets, derived cost, or v1 legacy accounting.
- The root README links the factory and its current-state summary, but does
  not enumerate execution usage schema versions. No separate
  `engineering/contracts/openapi` document describes the factory execution
  API; the factory-local contracts are authoritative for this surface.

## Required documentation and contract changes

1. **Keep v1 byte-compatible.** Do not add required fields to
   `factory-execution.v1.json`, change the v1 request shape, or reinterpret
   its adapter-supplied aggregate cost. Existing v1 producers, replayed
   events, fixtures, and durable rows must remain readable. Document the v1
   usage route as legacy aggregate accounting (input/output/reasoning only),
   not as a complete decomposition of historical usage.

2. **Make v2 an explicit closed contract.** In
   `factory-execution.v2.json`, revise both `UsageProposalRequest` and the
   resulting `UsageProposal` documentation/schema to describe five mutually
   exclusive billing buckets: `input_tokens`, `output_tokens`,
   `reasoning_tokens`, `cached_input_tokens`, and `cache_write_tokens`.
   Add the required closed `price_table` object and its schema/version and
   per-million-token micro-USD rates, alongside the lowercase SHA-256
   `price_table_digest`. The request must not accept provider-authored
   `cost_usd_micros`; the response/proposal may expose the server-derived
   calculated total for audit and budget projection.

3. **Document canonicalization and arithmetic in the v2 contract.** State
   the exact canonical JSON/digest rule (including duplicate-key, unknown
   field, numeric-type, Unicode, supported-version, and lowercase digest
   rejection), and the per-component integer rule
   `floor(tokens * rate / 1_000_000)`, summed across all five buckets. State
   that cache and reasoning subsets are not double-counted and that invalid,
   missing, mismatched, or overflowed pricing fails closed. OpenAPI prose is
   needed because JSON Schema alone cannot express these semantics.

4. **Choose and document a wire discriminator before publishing v2.** The
   current single `usage.reported` event cannot safely gain required fields:
   that would silently break existing adapters and fixtures. Either define a
   distinct `usage.reported.v2` event or add an explicit protocol version
   negotiated/advertised by `adapter.ready`; then document that legacy
   `usage.reported` rejects all v2-only fields and v2 rejects mixed/partial
   payloads. The chosen name/version must be reflected in the protocol
   contract, adapter conformance docs, API route mapping, and replay rules.

5. **Clarify token-budget semantics.** The v2 contract must explicitly say
   whether `token_units` includes all five buckets (the AI analysis recommends
   yes) and that `cost_usd_micros` is calculated server-side. Preserve the
   existing task limit units and distinguish token quantities from rates and
   USD-micro cost ceilings. Document that a matching digest proves snapshot
   identity/integrity, not that the submitted tariff is an independently
   trusted provider price catalog.

6. **Describe persistence and rollback compatibility.** Document that v1
   observations remain readable without invented component splits or price
   tables; v2 observations retain the table snapshot (or a durable
   resolvable equivalent), all five counts, representation/version, digest,
   and derived cost. Duplicate/replay equality must include every v2 fact,
   not just aggregate totals. The additive migration is forward-only; rollback
   is code/config rollback with new columns retained and no deletion or
   rewrite of historical observations.

## Consumer and fixture inventory to update with the contract

- OpenAPI contract tests in `factory/tests/test_openapi_contract.py` and API
  tests in `factory/tests/test_api.py` currently construct usage requests with
  `cost_usd_micros`; add v1 unchanged and v2 derived-cost/missing-cost,
  malformed price-table, and mixed-payload cases.
- Protocol/broker tests (`factory/tests/test_protocol.py`,
  `factory/tests/test_brokers.py`) and the Codex/Grok JSONL fixtures should
  cover both wire versions, explicit zero cache fields, rejection of a
  provider total, digest mismatch, and no double counting.
- PostgreSQL/replay coverage in `factory/tests/test_postgres_integration.py`
  currently calls the legacy direct `observe_usage` API and canonical
  `usage.reported`; document those calls as v1 compatibility fixtures and add
  a v2 round-trip plus conflicting duplicate component facts.
- `factory/README.md` should update its execution-contract paragraph and
  schema/migration status once migration 019 exists (the current text ends at
  exact schema 17 and M6 migration 018). It should link or name the v2
  pricing/accounting contract and state rollout order: additive/read support,
  dual-read server, v2 adapter enablement, then any v2-only provider policy.

## Compatibility conclusion

The safe documentation outcome is additive dual-read/dual-contract support:
v1 remains unchanged and readable, while v2 is an explicitly discriminated,
closed producer contract with a price-table snapshot and server-derived cost.
Updating only `factory-execution.v2.json` is insufficient; the protocol,
adapter conformance/fixtures, API request docs, replay semantics, persistence
projection, tests, and factory operator README must all describe the same
boundary. A v2 payload carrying `price_table` but no discriminator would be
ambiguous and should not be published.
