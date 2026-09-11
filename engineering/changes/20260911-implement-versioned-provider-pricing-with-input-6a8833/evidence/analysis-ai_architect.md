# AI accounting analysis

Route: `6a88338ed69e`. Scope: read-only review of the approved design, implementation plan, protocol, broker, and durable usage path. No product files changed.

## Required semantic ruling

Treat `input_tokens`, `output_tokens`, `reasoning_tokens`, `cached_input_tokens`, and `cache_write_tokens` as mutually exclusive normalized billing buckets. `token_units` is their sum. This preserves the broker's existing additive interpretation of input/output/reasoning while extending it to cache categories. State this explicitly in the execution contract and pricing module: a producer must not supply an inclusive native input/output total alongside a separately billed subset.

Provider adapters own normalization of native provider usage into those buckets. When native usage reports inclusive totals, subtract known subsets exactly once; reject negative residuals and ambiguous overlapping categories. A reasoning token must not be charged once at output rate and again at reasoning rate. Cache-read and cache-write tokens must not additionally be charged at uncached-input rate. Do not silently infer unknown usage as zero: explicit zero is a fact, missing usage is incomplete evidence. This recommendation specifies the canonical boundary, not a claim that every provider exposes the same native schema.

## Price table and arithmetic

- Use a closed table schema with an exact integer version and five mandatory nonnegative integer rates in micro-USD per million tokens. Reject booleans, floats, numeric strings, missing keys, extra keys, unsupported versions, and negative quantities/rates.
- Canonicalize validated plain JSON using sorted keys and compact separators, with a stable UTF-8 encoding. Digest the complete versioned table and require exact lowercase SHA-256 agreement before pricing.
- Preserve the approved per-component rounding rule: sum `tokens * rate // 1_000_000` independently for all five components. Flooring the aggregate would produce different answers and is not interchangeable.
- Validate database-compatible integer bounds for individual stored quantities, their sum, and final cost. Python's unbounded intermediate multiplication is safe, but its result must never reach PostgreSQL outside the destination integer domain. Reject noncanonical/nonfinite values before arithmetic.
- A rate has different units from a task cost budget. Do not compare per-million-token rates directly with `max_cost_usd_micros`: enforce the resulting observed cost and total-token budget, plus a clearly documented independent representational/rate bound if required.
- A matching digest establishes table identity and tamper detection, not approved tariff provenance. The current scope can provide deterministic cost from submitted versioned rates; it must not claim that those rates are authenticated provider billing or independently trusted budget valuation. Authentic tariff selection would require a trusted catalog or packet-bound expected digest.

## Adapter, broker, and store boundaries

The adapter submits usage facts and the immutable table snapshot/digest; it cannot submit authoritative `cost_usd_micros`. The broker validates the full v2 payload and derives cost. Durable proposal reconstruction must preserve the same table and component values, so replay cannot accidentally restore the legacy caller-cost path. Internal store APIs that remain callable should either recompute from validated components/table or be explicitly limited to trusted prevalidated proposals.

For durable observations, include all components in both command-request digests and `(run_id, provider_call_id)` duplicate equality checks. Equal aggregate tokens/cost with a different component breakdown is conflicting evidence. Persist enough immutable table content, directly or through the durable execution event, to reconstruct pricing after the reporting producer disappears; a digest with no resolvable historical snapshot is insufficient for independent recomputation.

Legacy records contain only aggregate token units. Preserve their historical aggregate and cost without inventing a component decomposition. Default-zero additive columns may represent unavailable historical details; document this legacy interpretation and avoid applying a universal aggregate-equals-components invariant to old rows. Existing durable v1 facts should remain readable while only v2 accepts the new expanded producer contract.

## Focused acceptance cases

1. All five nonzero buckets yield exact expected cost and summed token units; explicit zero cache fields work.
2. Two fractional components demonstrate the specified per-component flooring.
3. Boolean, float, negative, oversized quantity/rate, extra/missing table key, unsupported version, and digest mismatch fail closed.
4. Caller-supplied total cost is rejected; price changes alter the digest and derived cost.
5. Cache or reasoning subsets cannot be double counted by the documented canonical adapter convention.
6. Replay of an identical observation is idempotent; redistributing equal total tokens among components conflicts.
7. Migration retains legacy aggregate/cost and new observations preserve components; budget rejection uses the computed cost and all five buckets.

## Shared decision for implementation

The implementer should record the exclusive-bucket normalization convention and integrity-versus-tariff-authenticity boundary in the durable change decision log. These choices make deterministic costs reviewable without coupling the accounting engine to live provider APIs or claiming provider billing verification that the submitted table cannot establish.
