# Requirements — M5 Isolated Provider Execution

## Acceptance criteria

- [ ] AC-001 canonical immutable packets bind task/run/repository/authority/provider/profile/policy/plan/output/limits and have a digest distinct from M4 intake identity.
- [ ] AC-002 a bounded closed JSON invocation and JSONL event parser rejects malformed, oversized, duplicate/non-monotonic, identity-mismatched, post-terminal, unknown-required, reasoning-bearing, and missing/duplicate-terminal streams.
- [ ] AC-003 Codex and Grok native fixture adapters normalize only allowlisted projections, never make live calls or silently fall back, and report explicit conformance eligibility.
- [ ] AC-004 note, artifact, usage, and terminal proposal brokers validate role, fence, packet, sequence, size, digest, provenance, retention, budget, and terminal semantics without storing chain-of-thought.
- [ ] AC-005 workspace/Git/runtime boundaries expose capability-shaped interfaces, sanitized environments and adversarial fake-runtime denial tests for traversal, symlink, shared Git, credential, egress, cross-task, and external-write attempts.
- [ ] AC-006 migrations `014`-`016` after immutable M4 `013` persist canonical execution packets/manifests/events/proposals/attestations/results without backfilling fabricated evidence; migration `017` adds PostgreSQL-17-only recovery jobs/claims/outcomes and atomic fixed metrics before any M6 migration `018`; runtime and artifact-attestor roles receive only their exact capabilities.
- [ ] AC-007 additive execution claims/stages preserve legacy `/v1/claims` and enrolled execution-v1 compatibility; `/v1/execution/terminal` and additive `/v2/execution/terminal` execute one server-owned, idempotent proposal → trusted snapshot → finalization saga, never accept a worker snapshot, and return their version-specific closed projection.
- [ ] AC-008 two-lane recovery scans 2..100 raw candidates with bounded indexed keyset work, work-conserving fresh/retry fairness and a 30-second transaction-wide budget; cancel/supersede projection, at-least-once exact-handle cleanup, fencing/history/restart behavior, zero fabricated proposal/result, zero-epoch/no-backfill metrics and fixed-cardinality atomic snapshots are proven on disposable PostgreSQL 17.
- [ ] AC-009 exactly four predefined inert source-controlled systemd units enforce fixed identities/topology/resource/security policy and pass static checks without installation, enablement or activation.
- [ ] AC-010 architecture, installer, README, recovery, provider eligibility and host-isolation limitations match the final source tree.
- [ ] AC-011 all locally feasible focused and repository checks pass on the final source tree; independent reviews/receipts remain parent-owned.

## Failure and edge cases

Unknown versions/fields/capabilities/providers, invalid UTF-8 or Unicode scalar values, excessive nesting/size/count/cost/time, native reasoning, missing usage, stale fence, invalid artifact path/digest, workspace escape, successful credential/egress probe, output after terminal, or incompatible native version fail closed. Provider absence never selects another provider. Cancellation, supersession and orphan recovery retain bounded safe evidence and never erase immutable packets/manifests. Workspace cleanup is intentionally at-least-once after claim expiry/crash: release is deterministic, idempotent and exact-handle-bound; a stale fence cannot commit an outcome. Recovery never fabricates an execution proposal, workspace result or attestation.

## Non-functional constraints

All limits are checked before expensive work and aggregated with M4 ceilings: at most 20 readers globally, 10 per repository, one writer, four hours, USD 25, and initial attempt plus two infrastructure retries. Integrated recovery requires PostgreSQL 17 so `transaction_timeout` bounds setup, validation and business statements together; PostgreSQL 15/16 must fail before migration `017` mutates schema state. Durable/logged data is allowlisted and redacted by construction. No secret value, raw native stream, unrestricted stdout/stderr, raw prompt, scratchpad, or private reasoning may cross the durable boundary.
