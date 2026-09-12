# Architectural analysis — versioned provider pricing

Route: `6a88338ed69e`
Scope: read-only analysis of provider-price versioning, canonical digesting, and deterministic integer cost.

## Findings

The existing durable usage boundary is aggregate-only. `usage.reported` and
`UsageProposal` accept `price_table_digest`, input/output/reasoning counts,
and an adapter-supplied `cost_usd_micros`; `total_tokens` is their three-way
sum. The Postgres observation stores only that aggregate count and cost.
Although `factory-execution.v2.json` has OpenAPI version `2.0.0`, its usage
schemas retain this legacy shape. The event protocol itself is pinned to
`adaptive-factory.execution/v1`. Therefore adding required fields to the
current payload without a discriminating wire version would silently break
existing adapters and fixtures rather than provide the stated v2-only path.

## Recommended compatibility design

1. Preserve the existing execution/v1 `usage.reported` payload and its
   aggregate durable facts exactly. Introduce a separate closed v2 usage
   representation (either an explicit event/protocol version negotiated at
   `adapter.ready`, or a distinct `usage.reported.v2` event). Do not use an
   optional `price_table`: a payload that contains it must require every v2
   field, and a legacy payload must reject every v2-only field. This avoids
   ambiguous partial accounting.
2. Make the v2 value carry `price_table` and its `price_table_digest`, plus
   `input_tokens`, `output_tokens`, `reasoning_tokens`,
   `cached_input_tokens`, `cache_write_tokens`, and `output_bytes`. It must
   omit adapter-provided `cost_usd_micros`; the broker/service derives it.
   Keep a server-returned calculated cost in the proposal/result and durable
   record for audit, not as a provider assertion.
3. Retain v1 reader support in every replay, duplicate comparison, API, CLI,
   and persistence projection. V2-only producers should be enabled only after
   the v2 OpenAPI and protocol contract are published. Updating just the
   `factory-execution.v2.json` schema is insufficient because protocol.py,
   brokers.py, api.py, service.py, the Codex adapter, and SQL procedures all
   currently enforce and/or construct the old closed field set.

## Canonical price-table identity

Use the repository's `canonical_json` serialization (sorted keys, UTF-8,
compact separators) over a strictly validated, NFC-normalized plain mapping.
Before hashing, reject duplicate JSON keys, unknown fields, floats/bools,
negative values, non-ASCII/invalid identifiers, and any schema version other
than the explicitly supported price-table version. Hash the complete closed
table—including `schema_version`, provider/model identity if pricing is
model-specific, currency/unit, and all five integer micro-USD-per-million
rates—with SHA-256. Compare the lowercase hex digest using a constant closed
field set; never calculate from a table selected only by a digest.

Domain separation is advisable (`sha256("adaptive-factory.price-table/v1\\0"
+ canonical_json(table))`) because the repository's generic `canonical_digest`
is otherwise reused for unrelated structures. The exact domain string and
canonical form must be fixed in the OpenAPI prose/schema and implementation
tests. If compatibility requires the generic digest, document that deliberate
choice and use it consistently across producer, broker, API, and SQL.

## Deterministic cost and limits

For each component, calculate `floor(tokens * rate_microusd_per_million /
1_000_000)` with integer arithmetic and sum the five quotients. Do not divide
after summing products: it has different rounding semantics. Enforce bounded
nonnegative integers before multiplication and explicitly reject a product or
sum exceeding signed 64-bit storage/task ceilings; Python's unbounded integers
do not protect the PostgreSQL `bigint` boundary. Cached-input and cache-write
tokens should be included in monetary cost but excluded from the existing
`token_units` total unless the task-limit contract is deliberately versioned
to redefine the budget semantic. The design must state that distinction.

Validate the table digest and derive cost at the first trusted boundary
(broker/service) before releasing reservations. Persistence should receive
only the validated components, canonical table/digest, and calculated total
within the existing idempotent transaction. Duplicate identity checks must
compare every v2 component and the table identity, not merely aggregate cost
and token units; otherwise different provider facts can collide.

## Migration and rollout

Add a forward-only migration with nonnegative `input_tokens`,
`output_tokens`, `reasoning_tokens`, `cached_input_tokens`, and
`cache_write_tokens` columns plus a version/representation discriminator.
For legacy rows, preserve `token_units` and aggregate `cost_usd_micros` as
authoritative historical facts, set the new cache counts to zero, and mark
the representation legacy rather than fabricating a price table or component
split. Nullable component columns or an explicit `usage_schema_version=1`
make that distinction visible to readers. A non-null default of zero for all
components would falsely assert a known decomposition for historical rows.

Roll out in this order: deploy/read migration; deploy server that understands
both forms and still accepts v1; publish/enable v2 adapters; then require v2
for newly configured pricing-capable providers. Rollback is source/config
revert with the new columns retained; do not rewrite or delete observations.
Missing, malformed, unsupported, or digest-mismatched v2 pricing must block
further provider dispatch and leave an audit reason, never be treated as zero
cost.

## Required acceptance evidence

- Cross-language/canonical fixtures prove equal digests under key ordering and
  reject alternate Unicode, unknown fields, duplicate keys, floats, and
  digest mismatch.
- Boundary tests prove the adapter cannot supply the final total, exact
  per-component flooring (including residual fractions), overflow rejection,
  zero cache values, and budget-limit rejection.
- Contract/replay tests cover v1 acceptance unchanged, v2 acceptance, no
  mixed payload, and idempotent duplicate equality across all v2 facts.
- Migration tests cover an existing v1 row, a v2 write/read round-trip, and
  rollback-reader behavior with the expanded table.

## Decision

Treat price-table semantics as a versioned provider-accounting contract, not
as a cosmetic extension of the existing v2 OpenAPI document. The smallest
safe vertical change is additive dual-read/dual-contract support with server
calculation and immutable facts per observation.
