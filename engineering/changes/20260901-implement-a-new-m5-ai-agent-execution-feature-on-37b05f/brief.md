# M5 Isolated Provider Execution

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains the approved slice and cannot create provider, credential, deployment, or merge authority.

Change ID: `20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f`
Route: `37b05f579320`
Current M4 local candidate: `9727bc30c82bb44a86db0ef5b62e507b5527207a` (source `3b1f9a5`, tree `5feb9a7`); PR #21 still contains failed `571cad7`, so accepted M4 remains absent.
Frozen M5 predecessor: successor 04 contract enrollment/comparator `27b0ae619cacf0d9ddeed15c60212800ff6009ca` (tree `1a4e3f8`) on exact predecessor `8a7be8a`; local tests/fitness pass, while session reviewer feedback has no checked-in report or route receipt.
Current successor: successor 05 runtime/recovery/additive-v2 on exact `27b0ae6`, product/restart checkpoint `3940267` (tree `4646582`); the two-restart PostgreSQL-17 proof passes locally, while repository-bound exact-head review/verifier receipts remain open.

Navigation: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [schedule](schedule.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

## Problem and outcome

M4 can accept and lease durable work, but `/v1/claims` returns only a legacy lease whose `packet_digest` is the intake `intent_digest`. It has no immutable execution packet, provider identity, execution stage, note/artifact proposal, run manifest, or workspace handle. M5 adds an explicit execution path without changing that legacy meaning.

The locally achievable outcome is source and deterministic evidence for canonical packets, a provider-neutral bounded JSON/JSONL protocol, version-pinned Codex/Grok fixture adapters, proposal brokers, additive v2 plus compatible v1 execution APIs, atomic trusted terminal finalization, fake workspace/runtime isolation, restart/orphan recovery, metrics and documentation, followed by exactly four planned inert systemd units in successor 06. No provider is invoked and no unit is installed or activated. The self-contained M5 probe now passes across two actual PostgreSQL-17 restarts with exact runtime/attestor capabilities, durable cleanup history and zero fabricated proposal/result/attestation. Four inert unit sources/tests plus installer/configuration parity are absent successor-06 work, and the live rootless-isolation exit remains blocked.

## Scope

Full M5 scope includes immutable execution contracts, bounded protocol parsing, fixture-only adapters, proposal/workspace brokers, migrations `014`-`017`, compatible v1 plus additive strict v2 HTTP contracts, trusted snapshot finalization, two-lane recovery/atomic metrics, installer/architecture/docs parity and static systemd hardening. Successor 04 freezes contract enrollment/comparator; successor 05 owns runtime/recovery/v2; successor 06 owns the pending inert systemd/installer/configuration/final-doc slice. M6 begins at `018`.

Out of scope: live provider/network calls, credentials, Trust CI or human-key access, systemd install/activation, OS package installation, push/PR/merge/deploy, M6 semantic validation, and any weakening of M4's one-writer or 20/10 ceilings.

## Approved rulings and gates

- The user approved the canonical model-agnostic factory design and continuous parallel execution. That satisfies the route's scope/design gate; it does not grant external actions.
- Current M4 candidate `9727bc3` is local only. Every M5 successor uses its immediately preceding bounded successor as the explicit fitness base. Cumulative M4→successor-04 exceeds the architecture size budget, so a squash/cumulative PR is prohibited; neither the inherited route base nor an aggregate WIP head is delivery authority.
- Migrations `014`-`017` have never been accepted, published or deployed. `015` expands canonical persistence, `016_contract` removes only superseded provisional constraints, and PostgreSQL-17-only `017` adds recovery/metrics with no historical metric backfill. No synthetic attestation, terminal proposal or result and no universal production-upgrade claim is permitted; M6 starts at `018`.
- Exact-predecessor fitness requires external `architecture`, `data`, and `security` scopes for this red-risk tree; the change package also retains its release scope. No external data approval exists for this local checkpoint, so that gate is explicitly blocked and no local test, receipt, or agent review substitutes for it.
- Codex candidate identity is `0.152.1` with distribution digest `b8201824…06f9`; Grok candidate identity is `1.0.17` with digest `82595e26…4568`. Grok remains ineligible until its complete required capability conformance is proven.
- This host has no `podman`, `bwrap`, `newuidmap`, `slirp4netns`, or `pasta`, and unprivileged user-namespace creation is denied with `EPERM`. The OS-isolation exit is therefore `BLOCKED` pending a dedicated rootless execution host; M5 exit must not be claimed here.
