# M5 Isolated Provider Execution

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains the approved slice and cannot create provider, credential, deployment, or merge authority.

Change ID: `20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f`
Route: `37b05f579320`
Implementation base: `460a8a01a6394cac710b4e3f9eea3d94d4beef89`

Navigation: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [schedule](schedule.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

## Problem and outcome

M4 can accept and lease durable work, but `/v1/claims` returns only a legacy lease whose `packet_digest` is the intake `intent_digest`. It has no immutable execution packet, provider identity, execution stage, note/artifact proposal, run manifest, or workspace handle. M5 adds an explicit execution path without changing that legacy meaning.

The locally achievable outcome is source and deterministic evidence for canonical packets, a provider-neutral bounded JSON/JSONL protocol, version-pinned Codex/Grok fixture adapters, proposal brokers, additive persistence/API integration, fake workspace/runtime isolation, restart/orphan recovery, metrics, documentation, and predefined systemd units. No provider is invoked and no unit is installed or activated.

## Scope

In scope: immutable `TaskPacketV1` and authority/profile/policy/plan/manifest contracts; bounded UTF-8 JSON/JSONL parsing; no-chain-of-thought projection; Codex `0.152.1` and Grok `1.0.17` fixtures; note/artifact/usage/terminal proposals; workspace and Git broker interfaces; fake-runtime adversarial tests; additive migration `013`; a new execution claim/stage API; recovery/metrics/docs/installer/architecture; static systemd hardening checks.

Out of scope: live provider/network calls, credentials, Trust CI or human-key access, systemd install/activation, OS package installation, push/PR/merge/deploy, M6 semantic validation, and any weakening of M4's one-writer or 20/10 ceilings.

## Approved rulings and gates

- The user approved the canonical model-agnostic factory design and continuous parallel execution. That satisfies the route's scope/design gate; it does not grant external actions.
- Exact current M4 review base `460a8a01a6394cac710b4e3f9eea3d94d4beef89` is authoritative for this stacked slice. The initial `94fc5ad878e6b15df6418303caada49a3b93bf4c` anchor is superseded for implementation and retained only as conflict-free restack lineage; the inherited route still records an earlier program base.
- Separate local M4 candidate `01a10f5` is not this branch's parent, not pushed and not merged. Task 5 checkpoint `161199bb163e0ba84ac1b32010be87f113df5e86` is provisional source evidence; M5 must restack and regenerate evidence after M4 settles.
- Codex candidate identity is `0.152.1` with distribution digest `b8201824…06f9`; Grok candidate identity is `1.0.17` with digest `82595e26…4568`. Grok remains ineligible until its complete required capability conformance is proven.
- This host has no `podman`, `bwrap`, `newuidmap`, `slirp4netns`, or `pasta`, and unprivileged user-namespace creation is denied with `EPERM`. The OS-isolation exit is therefore `BLOCKED` pending a dedicated rootless execution host; M5 exit must not be claimed here.
- A trusted live Git snapshot broker is also `BLOCKED`. M6 paused at `5c5c371` still consumes the old `61db79f` bridge and lacks current result fields and exact linkage, so no compatibility, semantic verdict or self-approval is claimed; provider facts are not authority and production remains human-owned.
