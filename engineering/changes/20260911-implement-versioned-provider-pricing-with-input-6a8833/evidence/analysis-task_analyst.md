# Acceptance and compatibility analysis

## Scope and current baseline

The design source is `docs/superpowers/specs/2026-09-11-token-cache-cost-accounting-design.md`.
The current implementation stores only aggregate `token_units` and provider-supplied
`cost_usd_micros` in `factory.usage_observations` (migration 003), while the broker,
execution API, v1 worker API, and canonical persistence SQL all validate and persist
that same legacy shape. In particular, `/v1/execution/usage` and `/v2/execution/usage`
are currently aliases, and the internal execution proposal remains contract version 1.

## Backwards-compatibility ruling

- Existing v1 durable rows must remain readable without changing their historical
  aggregate cost/token facts. A forward migration should add nonnegative cache-input
  and cache-write columns with zero defaults (or nullable columns normalized to zero at
  read time), and must not recompute or overwrite legacy rows.
- v1 producers must continue to submit the legacy payload and must not be forced to
  provide a price table. The expanded payload is v2-only; therefore the implementation
  needs an explicit version boundary rather than relying on the current v1/v2 route
  aliases. Either reject expanded fields on v1 and require them on v2, or introduce a
  clearly bound v2 proposal/contract discriminator. Accepting a v2 payload through a
  v1 path would undermine the stated compatibility guarantee.
- Existing readers/metrics that use `token_units`, `cost_usd_micros`, and
  `output_bytes` must see identical values for historical and newly recorded calls;
  total token units should be defined as input + output + reasoning + cached-input +
  cache-write only if that is the intended budget semantic. The design says budget
  enforcement continues to use total token units, so this choice must be made explicit
  and tested (cached tokens may be billed but are not always equivalent to billable
  input tokens).
- Provider adapters may not submit a total cost in v2. The server must calculate and
  persist it; retaining a client-supplied cost field for v2 creates a compatibility and
  trust ambiguity. If the legacy v1 field remains accepted, its trust/validation rules
  must stay isolated from v2.

## Migration and backfill constraints

- Migration is forward-only and additive. Preserve the existing unique key
  `(run_id, provider_call_id)`, grants/revokes, metrics triggers, and all foreign keys.
  The runtime role needs insert/select access to new columns but no update privilege on
  immutable observations, consistent with migration 005.
- Existing observations receive zero cache fields and retain their original aggregate
  cost, token count, provider-call identity, and price-table digest. Do not infer cache
  splits or rewrite historical provider facts; there is no safe source for such a
  backfill.
- The migration must be ordered after the current schema version and be safe for a
  reader during rollout. A previous binary should still read the table and continue
  writing legacy rows (assuming the new columns have defaults). A new binary must not
  require v2 columns when reading legacy rows.
- Any canonical proposal/persistence comparison must account for the new columns and
  price-table digest while preserving the old row shape. Idempotent replay must compare
  every v2 component, price-table digest, and calculated cost; same idempotency key or
  provider-call ID with different values must fail closed rather than create a second
  observation.
- Rate and arithmetic bounds need to be database-safe as well as Python-safe. Integer
  micro-USD rates, multiplication, sum, and floor division must not overflow bigint or
  silently wrap. Unknown price-table schema, noncanonical digest, negative values, and
  cost/rate over task limits must leave accounting blocked and no partial observation.

## Observable acceptance criteria

The implementation should make these externally testable outcomes true:

1. A valid v2 report containing input, output, reasoning, cached-input, and cache-write
   counts plus a closed price table is accepted; the server recomputes cost by floor
   division per component, stores all components, stores the canonical table digest,
   and returns the durable observation identity.
2. Replaying the same idempotency key returns the same result without a second row.
   Reusing it (or the provider-call ID) with any changed component, table, digest, or
   calculated cost is rejected deterministically.
3. A v2 report with a malformed/unknown price-table schema, digest mismatch, negative
   or non-integer count/rate, arithmetic overflow, or a cost/token/output limit breach
   is rejected and marks accounting blocked; no usage row or budget release is
   committed as if the report succeeded.
4. A legacy v1 report remains accepted under its documented rules, and an existing
   v1 row can be read after migration with cache fields equal to zero. A v1 request
   carrying v2-only fields is rejected as a closed payload, not silently downgraded.
5. Budget totals, terminal finalization, metrics, history, and reconciliation continue
   to agree with durable observations. A completed run still requires usage and zero
   unreleased reservations; calculated v2 cost feeds the same task limits.
6. OpenAPI/schema artifacts describe the v2 shape, forbid adapter-supplied total cost,
   and leave v1 examples/clients valid. Contract tests must exercise both route
   versions, not just the currently aliased handlers.

## Test and review risks

- Unit tests can pass while SQL canonicalization or migration ordering is wrong;
  include a real migration before/after shape test and PostgreSQL persistence test.
- Exact pricing is vulnerable to rounding drift. Test each component independently,
  floor behavior for sub-micro-dollar products, zero cache fields, large bounded
  values, and sum/overflow boundaries.
- Digest tests must canonicalize object key order and reject semantically equivalent
  but byte-different tables unless the documented canonical JSON algorithm says they
  are equivalent. Assert the digest binds the complete table, schema version, and all
  rates.
- Broker, API, and SQL currently duplicate required-field and budget validation. Test
  malformed payloads through each boundary, including unknown fields, missing cache
  fields, extra legacy cost fields, negative integers, booleans-as-integers, and v1/v2
  route differences.
- Idempotency tests must cover same-key replay after restart, provider-call duplicate,
  changed payload replay, and concurrent duplicate submissions. Verify no reservation
  is released or task total incremented twice.
- Existing fixtures and integration probes hard-code the old usage shape and aggregate
  token totals; update them deliberately and retain at least one legacy fixture to
  prove backward readability. Avoid changing unrelated landing-provider usage fields,
  which are a separate contract.
- Security review should confirm price tables contain no prompt/provider secret data,
  raw tables are not logged, and error/audit records retain only bounded identifiers,
  digests, and typed failure reasons.

## Release/rollback implication

Rollout should be staged as additive schema first, then readers, then v2 producers.
Source rollback is safe only while the migration's additive columns/defaults remain;
do not attempt destructive schema rollback. If v2 accounting is disabled, fail closed
for v2 reports and keep v1 processing available. The post-deploy check must compare
legacy totals and row counts before/after and verify no historical row was rewritten.
