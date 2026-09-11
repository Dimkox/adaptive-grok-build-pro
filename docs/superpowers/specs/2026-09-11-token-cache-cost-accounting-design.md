# Versioned token-cache cost accounting

## Goal

Persist provider usage as separate input, output, reasoning, cached-input and
cache-write token quantities, and derive cost deterministically from an
immutable, digest-bound price table.

## Contract

`usage.reported` gains `cached_input_tokens`, `cache_write_tokens`, and a
closed `price_table` object containing schema version and per-million-token
integer micro-USD rates. Its SHA-256 canonical digest must equal
`price_table_digest`. The server calculates `cost_usd_micros` with floor
division of each component; adapters may not supply a total cost.

The change uses execution protocol v2 on a new HTTP v3 usage route. Existing
v1 and published HTTP v2 records and payloads remain readable; only protocol
v2 producers may submit the expanded usage payload.

## Persistence

A forward-only migration adds nonnegative token-component columns to
`factory.usage_observations`; existing observations receive zero cache fields
and their legacy aggregate remains intact. The runtime writes every component,
the calculated total, and the digest atomically under its existing idempotency
key. Task budget enforcement continues to use total token units and the
calculated total cost.

## Safety and rollout

The price table carries no credential or prompt content. Unknown schemas,
digest mismatch, negative values, overflow, or a rate/cost above task limits
fail closed. No backfill rewrites historical provider facts. Rollback is a
source revert; the added nullable/defaulted columns are harmless to the
previous reader.

## Evidence

Tests cover exact pricing, zero cache values, malformed/digest-mismatched
tables, protocol/broker rejection, idempotent persistence, OpenAPI schema, and
the migration's before/after shape.
