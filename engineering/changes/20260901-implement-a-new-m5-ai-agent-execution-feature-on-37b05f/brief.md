# M5 Isolated Provider Execution

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains the approved slice and cannot create provider, credential, deployment, or merge authority.

Change ID: `20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f`
Route: `37b05f579320`
Final M4 root: `571cad7877431ac5ab5779b53fe9f7effd6859ce` (tree `9d29f25d3af4fc9f97bbb8b3d4970906b69338fd`)
Current successor: slice 01 checkpoint `9ba284eeeb21b36e8b484c9f25a5f7c8ea8077c1` (tree `177112f6a862d88cb867f92235b30ea6bad890ec`)

Navigation: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [schedule](schedule.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

## Problem and outcome

M4 can accept and lease durable work, but `/v1/claims` returns only a legacy lease whose `packet_digest` is the intake `intent_digest`. It has no immutable execution packet, provider identity, execution stage, note/artifact proposal, run manifest, or workspace handle. M5 adds an explicit execution path without changing that legacy meaning.

The locally achievable outcome is source and deterministic evidence for canonical packets, a provider-neutral bounded JSON/JSONL protocol, version-pinned Codex/Grok fixture adapters, proposal brokers, additive persistence/API integration, fake workspace/runtime isolation, restart/orphan recovery, metrics, documentation, and predefined systemd units. No provider is invoked and no unit is installed or activated.

## Scope

Full M5 scope: immutable `TaskPacketV1` and authority/profile/policy/plan/manifest contracts; bounded UTF-8 JSON/JSONL parsing; no-chain-of-thought projection; Codex `0.152.1` and Grok `1.0.17` fixtures; note/artifact/usage/terminal proposals; workspace and Git broker interfaces; fake-runtime adversarial tests; additive migration `014`; a new execution claim/stage API; recovery/metrics/docs/installer/architecture; static systemd hardening checks. Slice 01 contains only contracts/protocol, fixture adapters, brokers/workspace and their architecture ownership; the remaining scope belongs to explicit successors.

Out of scope: live provider/network calls, credentials, Trust CI or human-key access, systemd install/activation, OS package installation, push/PR/merge/deploy, M6 semantic validation, and any weakening of M4's one-writer or 20/10 ceilings.

## Approved rulings and gates

- The user approved the canonical model-agnostic factory design and continuous parallel execution. That satisfies the route's scope/design gate; it does not grant external actions.
- Exact final local M4 `571cad7877431ac5ab5779b53fe9f7effd6859ce` is the authoritative root for slice 01. Later slices use their immediately preceding bounded slice as the explicit fitness base; neither the inherited route base nor aggregate M5 head `141e51e7` is delivery authority.
- Codex candidate identity is `0.152.1` with distribution digest `b8201824…06f9`; Grok candidate identity is `1.0.17` with digest `82595e26…4568`. Grok remains ineligible until its complete required capability conformance is proven.
- This host has no `podman`, `bwrap`, `newuidmap`, `slirp4netns`, or `pasta`, and unprivileged user-namespace creation is denied with `EPERM`. The OS-isolation exit is therefore `BLOCKED` pending a dedicated rootless execution host; M5 exit must not be claimed here.
