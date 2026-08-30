# Requirements — production-only human approvals

## Acceptance criteria

- [ ] AC-001: strict frozen `PromotionEnvelopeV1` canonical JSON and Ed25519 verification reject every malformed, unknown, tampered, wrong-scope or stale field.
- [ ] AC-002: accepted promotion exactly matches an HMAC-ingested merge fact independently corroborated through GitHub App API and a passed exact-SHA protected-branch/artifact attestation.
- [ ] AC-003: migration `004_production_promotions.sql` is additive, byte-identical in both trees, checksum-locked, least-privilege and safe on populated 001–003 databases.
- [ ] AC-004: acceptance, idempotent response and nonce/ID/payload replay semantics are atomic and deterministic across concurrent replicas and restarts.
- [ ] AC-005: one exact promotion can be consumed once; mismatch, expiry, policy rotation, dependency failure or concurrent replay causes zero production writes.
- [ ] AC-006: audit events are append-only, correlated, bounded and secret-free; metrics and alerts cover every denial and reconciliation gap.
- [ ] AC-007: the complete M2–M9 stack passes unit, contract, ephemeral PostgreSQL, restart/restore, role, concurrency, provenance, local shadow/deny-only and rollback evidence without any intermediate human gate or external write.
- [ ] AC-008: an externally deployed automated-only policy makes development validation, PR delivery and merge signature-free while preserving App-owned exact-SHA branch protection; after automated merge and protected-branch/artifact attestation, exactly one human `promotion:production` signature gates consume-once production deployment.

## Failure and edge cases

- Lost/duplicated/conflicting GitHub delivery; squash/rebase/merge SHA differences; branch advances after merge.
- Artifact substitution, missing/failed attestation, stale policy, invalid key lifecycle, future/expired envelope.
- Same/different idempotency key, promotion ID, nonce or payload digest under concurrent submission.
- Consume race, crash after consume, PostgreSQL outage/restart/restore and external reconciliation.
- Kill switch, trust-store/policy/GitHub/provenance outage, rate limiting and oversized input all deny.

## Non-functional requirements

- Security: server-side exact resource authorization, split credentials/roles, no private keys in service or agent, no fail-open path.
- Reliability: durable facts, bounded reconciliation, atomic transactions, consume-before-effect and explicit forward recovery.
- Performance: request body at most 16 KiB, bounded worker retries, index-backed exact lookup, query-plan evidence before rollout.
- Observability: stable reason codes, correlation chain, bounded metrics, audit durability and alerting on impossible/bypass states.
