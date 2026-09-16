# Comparator fix for object-valued enum members (#104)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Problem

The local fitness analyzer understands only a closed JSON-Schema subset, by design: anything it cannot decide fails the gate. One blind spot made whole classes of contracts write-once: an `enum` whose members are objects — the shape this repo uses for *closed fact registries* (`landing-backend-capability.v1` declares every profile as its complete fact object; the failover OpenAPI `$ref`s it). Any edit returned `unsupported` → architecture fail → governance fail. #105 discovered this by being blocked by it.

## Fix

`_valid_enum_member`: members may be bounded opaque data values (string-keyed dicts / lists of finite scalars) charged to the same depth and node budget as the rest of analysis. Comparison already worked on canonical bytes, so direction semantics (superset, narrowing, duplication) now apply to objects exactly as to scalars. Nothing else in the subset moves.

## What the fix exposed (and what it deliberately does not decide)

With the analyzer able to judge: adding a profile fact is **compatible** under `consumer_accepts_old` and **incompatible** (`widened_producer_output`) under `producer_accepted_by_old` — and `rules.yaml` applies both to every json_schema contract. So declaring `qwen-omni-intl` inside v1 is honestly a producer break, not a tool artifact. This wave does not edit the contract or the rules; #104 keeps the remaining named choice (v2 coexistence vs consumer-only governance for fact registries).
