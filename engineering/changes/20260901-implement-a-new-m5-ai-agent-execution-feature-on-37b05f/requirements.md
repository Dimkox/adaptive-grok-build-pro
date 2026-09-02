# Requirements — M5 Isolated Provider Execution

## Acceptance criteria

- [ ] AC-001 canonical immutable packets bind task/run/repository/authority/provider/profile/policy/plan/output/limits and have a digest distinct from M4 intake identity.
- [ ] AC-002 a bounded closed JSON invocation and JSONL event parser rejects malformed, oversized, duplicate/non-monotonic, identity-mismatched, post-terminal, unknown-required, reasoning-bearing, and missing/duplicate-terminal streams.
- [ ] AC-003 Codex and Grok native fixture adapters normalize only allowlisted projections, never make live calls or silently fall back, and report explicit conformance eligibility.
- [ ] AC-004 note, artifact, usage, and terminal proposal brokers validate role, fence, packet, sequence, size, digest, provenance, retention, budget, and terminal semantics without storing chain-of-thought.
- [ ] AC-005 workspace/Git/runtime boundaries expose capability-shaped interfaces, sanitized environments and adversarial fake-runtime denial tests for traversal, symlink, shared Git, credential, egress, cross-task, and external-write attempts.
- [ ] AC-006 additive migration `013` persists immutable execution packets/manifests/events/proposals/stages and the runtime role receives only execution-specific capabilities.
- [ ] AC-007 a new execution claim and stage path integrates with factual M4 while `/v1/claims` keeps its exact legacy contract and `packet_digest=intent_digest` meaning.
- [ ] AC-008 restart/orphan recovery terminates or reclaims incomplete execution manifests idempotently, preserves evidence, and exposes bounded low-cardinality execution metrics.
- [ ] AC-009 predefined source-controlled systemd units enforce fixed identities/topology/resource/security policy and pass static checks without installation or activation.
- [ ] AC-010 architecture, installer, README, recovery, provider eligibility and host-isolation limitations match the final source tree.
- [ ] AC-011 all locally feasible focused and repository checks pass on the final source tree; independent reviews/receipts remain parent-owned.

## Failure and edge cases

Unknown versions/fields/capabilities/providers, invalid UTF-8 or Unicode scalar values, excessive nesting/size/count/cost/time, native reasoning, missing usage, stale fence, invalid artifact path/digest, workspace escape, successful credential/egress probe, output after terminal, or incompatible native version fail closed. Provider absence never selects another provider. Cancellation and orphan recovery retain bounded safe evidence and never erase immutable packet/manifests.

## Non-functional constraints

All limits are checked before expensive work and aggregated with M4 ceilings: at most 20 readers globally, 10 per repository, one writer, four hours, USD 25, and initial attempt plus two infrastructure retries. Durable/logged data is allowlisted and redacted by construction. No secret value, raw native stream, unrestricted stdout/stderr, raw prompt, scratchpad, or private reasoning may cross the durable boundary.
