# M5 Isolated Provider Execution

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains the approved slice and cannot create provider, credential, deployment, or merge authority.

Change ID: `20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f`
Route: `37b05f579320`
Current normal-restack checkpoint predecessor: `56e12b2b394436ee227c66d78b1caba8f7317c78`
Original Tasks 1-6 source: `141e51e75b2bb337fa3bb1544639c6c46c287309`

Navigation: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md) ↔ [schedule](schedule.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).

## Problem and outcome

M4 can accept and lease durable work, but `/v1/claims` returns only a legacy lease whose `packet_digest` is the intake `intent_digest`. It has no immutable execution packet, provider identity, execution stage, note/artifact proposal, run manifest, or workspace handle. M5 adds an explicit execution path without changing that legacy meaning.

The locally achievable outcome is source and deterministic evidence for canonical packets, a provider-neutral bounded JSON/JSONL protocol, version-pinned Codex/Grok fixture adapters, proposal brokers, additive persistence/API integration, fake workspace/runtime isolation, restart/orphan recovery, metrics, documentation, and predefined systemd units. No provider is invoked and no unit is installed or activated.

## Scope

In scope: immutable `TaskPacketV1` and authority/profile/policy/plan/manifest contracts; bounded UTF-8 JSON/JSONL parsing; no-chain-of-thought projection; Codex `0.152.1` and Grok `1.0.17` fixtures; note/artifact/usage/terminal proposals; workspace and Git broker interfaces; fake-runtime adversarial tests; additive migration `014` after M4 `013`; a new execution claim/stage API; recovery/metrics/docs/installer/architecture; static systemd hardening checks.

Out of scope: live provider/network calls, credentials, Trust CI or human-key access, systemd install/activation, OS package installation, push/PR/merge/deploy, M6 semantic validation, and any weakening of M4's one-writer or 20/10 ceilings.

## Approved rulings and gates

- The user approved the canonical model-agnostic factory design and continuous parallel execution. That satisfies the route's scope/design gate; it does not grant external actions.
- Tasks 1-6 source at `141e51e75b2bb337fa3bb1544639c6c46c287309` is locally normal-merged on current M4 checkpoint predecessor `56e12b2b394436ee227c66d78b1caba8f7317c78` (tree `e5d49d98230ba25bcb5c75e5125e85a75f4dd213`). This is provisional local integration only; a newer M4 exact SHA requires another normal merge, and no M4/M5 acceptance, delivery, push or external authority is claimed.
- Historical Task 5 checkpoint `161199bb163e0ba84ac1b32010be87f113df5e86` remains source evidence only. The migration-collision RED proved duplicate `013`; this restack preserves M4 `013_persisted_infrastructure_retry_limit.sql` and moves M5 to contiguous `014_execution_plane.sql` with fresh checksum/upgrade/restart verification required.
- Codex candidate identity is `0.152.1` with distribution digest `b8201824…06f9`; Grok candidate identity is `1.0.17` with digest `82595e26…4568`. Grok remains ineligible until its complete required capability conformance is proven.
- This host has no `podman`, `bwrap`, `newuidmap`, `slirp4netns`, or `pasta`, and unprivileged user-namespace creation is denied with `EPERM`. The OS-isolation exit is therefore `BLOCKED` pending a dedicated rootless execution host; M5 exit must not be claimed here.
- A trusted live Git snapshot broker is also `BLOCKED`. M6 Task 3 is provisional at `f3b2c0d07116686b27feab4b60166e8a7402d672` and remains quarantined until accepted-M5 restack; its migration must move to `015`. No compatibility, semantic verdict or self-approval is claimed; provider facts are not authority and production remains human-owned.
