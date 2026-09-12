# Integration analysis — versioned provider pricing and token accounting

## Scope and conclusion

The existing durable execution path is already the correct integration seam:
provider-native records are normalized into a closed `usage.reported` event,
accepted into a `UsageProposal`, persisted under `(run_id, provider_call_id)`,
and reconciled against the proposal at execution finalization.  The minimal
compatible implementation should preserve that seam, add the five token
components and a server-calculated cost to the proposal/store boundary, and
keep all v1 evidence readable.

There is one material compatibility trap: `/v1/execution/usage` and
`/v2/execution/usage` are currently decorators on the same handler, with the
same v1-shaped closed field set.  The event layer also has one fixed
`adaptive-factory.execution/v1` protocol version.  Editing only
`factory-execution.v2.json` would therefore create a published v2 contract
that the runtime neither distinguishes from nor validates differently than
v1.

## Current handoff

```text
provider fixture/native usage
  -> adapters/codex.py or adapters/grok.py (canonical `usage.reported`)
  -> protocol.py (closed payload shape and scalar types)
  -> service.commit_execution_proposal()
  -> ProposalBroker._usage() (budget checks, UsageProposal, idempotency input)
  -> store.commit_execution_proposal() (immutable execution_proposals body)
  -> API `/v[12]/execution/usage` response

separate accounting command
  -> API `/v1/usage-observations`
  -> FactoryService.observe_usage()
  -> PostgreSQLStore.observe_usage()
  -> factory.usage_observations + task aggregates

execution finalization
  -> SQL `factory.execution_finalize_commit()`
  -> proposal/body vs usage_observations equality check
```

Evidence:

- Adapters currently forward provider-supplied `cost_usd_micros` unchanged
  (`factory/src/adaptive_factory/adapters/codex.py:54-70`,
  `adapters/grok.py:55-61`).  Their fixtures also contain the old cost field.
- `protocol.py:65-77` and `brokers.py:423-465` require exactly the three
  legacy token components plus caller cost.  `UsageProposal.total_tokens`
  currently sums only those three fields (`brokers.py:104-123`).
- The execution API aliases both versions to one handler
  (`api.py:885-905`), and the independent `/v1/usage-observations` endpoint
  accepts an aggregate `token_units` and caller cost (`api.py:1040-1061`).
- Store persistence and duplicate comparison use only digest, aggregate cost,
  aggregate tokens and output bytes (`store.py:4220-4355`).  The durable
  schema is `003_budgets_kills_reconciliation.sql:14-28`.
- Finalization cross-checks the old three-component proposal sum against the
  aggregate durable column (`015_execution_canonical_persistence.sql:1275-1300`).

## Recommended staged compatible implementation

### 1. Introduce a pure, closed pricing value object

Add `pricing.py` with immutable `UsageTokens` and `PriceTableV1` values.
`UsageTokens` should contain `input_tokens`, `output_tokens`,
`reasoning_tokens`, `cached_input_tokens`, and `cache_write_tokens`; all are
non-negative Python integers.  The table should contain only a schema version
and the corresponding five integer micro-USD-per-million rates.  Serialize
the exact closed table object as sorted-key, compact UTF-8 JSON and bind its
SHA-256 to `price_table_digest`; calculate each component independently as
`tokens * rate // 1_000_000`, then sum the five floored components.  Reject
unknown schema/keys, booleans, negatives, malformed or nonmatching digests,
and totals above context/task limits.  No float conversion is permitted.

Keep `PriceTableV1` and token quantities free of credentials, prompts, native
stream content and model output text.  That agrees with the protocol's
existing private-stream denylist.

### 2. Make the execution contract truly version-selectable

Do not mutate `factory-execution.v1.json`, its v1 request shape, or historical
`execution_proposals` bodies.  Split the aliased usage endpoint into explicit
v1 and v2 handlers (the other endpoint aliases can remain unchanged).  The
v2 handler must accept exactly:

`grant, packet_digest, sequence, provider_call_id, price_table,
price_table_digest, input_tokens, output_tokens, reasoning_tokens,
cached_input_tokens, cache_write_tokens, output_bytes`.

It must reject `cost_usd_micros`; it validates the table/digest and passes the
server-derived cost onward.  The v1 handler retains the legacy closed fields
only, so an expanded producer cannot silently be treated as a legacy producer.
Document the v2 request/proposal schema with `additionalProperties: false` and
no caller-cost property.

The same discriminator must reach adapter/event processing.  Today
`CanonicalEvent.from_payload()` stamps one v1 protocol version, and
`store.commit_execution_proposal()` rejects any other version.  Use one
explicit contract-version argument/typed event variant at the service/broker
boundary (or introduce a protocol-v2 constant end-to-end); do not infer v2
from the presence of cache fields.  That gives adapters a deterministic rule:
legacy adapters emit v1 usage unchanged, whereas a v2 adapter emits the
expanded body with a price table and never a total cost.  It prevents a
malicious v1 payload from adopting v2 semantics merely by adding keys.

### 3. Price before proposal persistence; bind the derived facts

For v2, `ProposalBroker._usage` is the correct authority to construct
`UsageProposal`: validate `UsageTokens` and `PriceTableV1`, calculate the
cost, and populate the proposal with all five components, digest, derived
cost, output bytes and idempotency key.  Include every component and the
derived cost in `proposal_idempotency_key`; otherwise replay could conceal a
changed token breakdown.

The broker context budget check and `total_tokens` must use the sum of all
five components.  This preserves the existing budget unit meaning while
including cache traffic.  The API should return the derived proposal (and may
therefore expose the calculated cost), never accept it as input.

### 4. Extend the durable accounting command atomically

Add forward-only migration `019_usage_token_components.sql`.  Add five
non-negative `bigint NOT NULL DEFAULT 0` component columns to
`factory.usage_observations` (including all legacy components, not only the
two cache components) so old rows remain readable without a rewrite.  Retain
the legacy `token_units` aggregate to avoid breaking task aggregates and old
readers.  New writes set it to the five-field sum.

Change `FactoryService.observe_usage`, the `/v1/usage-observations` adapter
(prefer a new `/v2/usage-observations` command for the expanded body), and
`PostgreSQLStore.observe_usage` as one vertical unit.  The store must calculate
or receive only the already broker-calculated value from a trusted internal
value object—not a raw HTTP caller total.  Include all components in:

- command-replay request digest;
- `(run_id, provider_call_id)` duplicate equality comparison;
- insert/select statements; and
- the proposal-to-observation finalization equality predicate.

Keep the insert, reservation release, task-limit comparison, task aggregate
update, audit event and command receipt in the current transaction.  This
already supplies the needed atomicity; an outbox is not required because this
flow publishes no external event.

### 5. Stage rollout and recovery

1. Land pure pricing tests first; no runtime schema/API change.
2. Land v2-only protocol/API/broker behavior and contract tests, retaining v1
   adapters and routes exactly.
3. Apply migration plus store/finalization changes and PostgreSQL idempotency
   tests.  Only then enable a v2-capable adapter fixture.
4. Observe calculation rejection, `accounting_blocked`, duplicate conflicts,
   and task observed cost/tokens.  The existing metrics aggregate remains
   usable because `token_units` is retained.

Rollback is a source rollback that stops v2 producers.  The additive defaulted
columns are safe for the old reader; do not roll back or rewrite durable facts.

## Required regression coverage

- Exact integer pricing, per-component floor behavior, zero cache quantities,
  digest mismatch, unknown price schema/key, boolean/negative/overflow values,
  and a forged caller total rejected by v2.
- v1 accepts only the legacy payload; v2 accepts only the expanded body; a v1
  event/route cannot be upgraded by extra keys.
- Adapter fixtures prove no native total cost is forwarded by a v2 adapter and
  private reasoning text remains absent.
- Proposal serialization/idempotency includes all five token quantities;
  duplicate provider-call reuse with any different component fails.
- Migration shape preserves old rows with zero defaults; new row persistence,
  task budget aggregation, finalization equality, API response and OpenAPI
  schema agree on all components and the server-derived total.

## Non-goals and integration boundaries

This change should not alter reservation semantics, provider selection,
credentials, external provider invocation, pricing discovery, historical
backfill, or cross-service publication.  A price table is evidence supplied
by the versioned producer and cryptographically bound for reproducibility; it
is not a live provider-price lookup.
