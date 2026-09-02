# Architecture — M5 Isolated Provider Execution

## Boundary and compatibility

```text
M4 accepted intent + legacy lease
  -> explicit execution claim configuration
  -> immutable TaskPacketV1 + RunManifestV1
  -> workspace/Git broker capability
  -> selected provider fixture adapter
  -> bounded canonical JSONL events
  -> validated proposals + stage/terminal transaction
  -> M4 ready_for_human / typed retry or needs_human
```

`/v1/claims` remains an M4 control-plane lease with its legacy request-identity semantics. M5 adds `/v1/execution/claims`, `/v1/execution/stages`, and execution proposal endpoints with execution-only secret-free identity helpers; it does not infer provider or execution policy from the legacy claim. The six new routes are described by `factory-execution.v1.json` on the same local server, while byte-identical `factory-control.v1.json` remains a retained/deprecated compatibility baseline rather than full unified discovery. The execution claim first obtains the M4 fence/capacity lease, then builds and persists one immutable packet and manifest from the accepted intent plus a closed trusted selection. Failure before persistence releases the lease through the existing typed path.

## Source components

- `execution_contracts.py`: frozen nested value objects, canonical packet digest, invocation and manifest contracts.
- `protocol.py`: bounded incremental JSON/JSONL parser and lifecycle state machine.
- `adapters/`: provider-native fixture translators and explicit conformance registry; no process/network invocation.
- `brokers.py`: note/artifact/usage/terminal validation and redaction.
- `workspace.py`: workspace/Git protocols, handle/path/environment policy, fake isolated runtime, host capability probe.
- `recovery.py`: provider-neutral, database-neutral coordinator over narrow store/workspace capabilities; it owns no provider, Git, scheduler, network or external authority.
- migration `014`: append-only execution packets/manifests/events/proposals/stages, protected artifact attestations, factual results, fixed metrics and recovery capabilities after M4 migration `013`.
- store/service/API: explicit execution operations checked against task/run/owner/fence/packet/live allocation/deadline/budget.
- `factory/systemd/`: fixed source unit topology only.

## Trust and security

Packet control fields never originate from repository text or native provider events. Adapters have no database, scheduler, GitHub, deployment, fallback, or policy mutation capability. Repository tools receive an allowlisted environment with credential-pattern variables removed and a default-deny network declaration. The fake runtime proves broker behavior, not OS isolation; only a dedicated rootless host with the required kernel/tooling can satisfy the M5 credential/egress exit drills.

## Recovery and rollout

On restart, a bounded reconciler scans at most 100 incomplete manifests in `(updated_at, run_id)` order and selects only rows whose M4 run and allocation are both released. It cleans broker-owned fake workspace state before appending exactly one control-plane `orphaned` stage/event; it creates no terminal proposal and no WorkspaceResult fabrication. Rollout is source-only and feature-dark: migration/API/unit files are not applied, started, or enabled by this task. Migration `014` is still unpublished; after acceptance, forward-fix uses `015+` and never rewrites accepted evidence.

## Executable contracts and downstream boundary

The merged executable inventory is 22 nodes, 24 directed edges and eleven contracts; the additional non-M5 node/edge comes from the preserved M4 release-state tree. Its M5 wire boundary is exactly four closed schemas plus the additive six-operation execution OpenAPI fragment: task packet and invocation are core-produced, canonical execution events are core-consumed, and the factual workspace result is core-produced; provider-specific adapters exchange only the modeled JSON/JSONL data flows and gain no database, Git, scheduler or external authority.

M4 exact state, lease, fence, allocation and budget facts from final local predecessor `571cad7877431ac5ab5779b53fe9f7effd6859ce` bind `TaskPacketV1`, the provider profile and `RunManifestV1`; proposal/snapshot/result digests then form the factual M5 output. M6 Task 3 at `f3b2c0d07116686b27feab4b60166e8a7402d672` is paused and unintegrated until accepted-M5 restack, when its provisional migration must move to `015`. Restack must verify the exact bundle before defining an M6 semantic subject; provider facts and fake authority cannot substitute, and M5 never self-approves.

The roadmap-only chain is digest-bound: an M6 verdict may feed an M7 shadow ready-for-PR bundle; M7 cohort evidence may feed an M8 profile only after at least 30 human-accepted outcomes with demotion and an L2 ceiling; an exact M8 profile/artifact may feed M9 preview/staging/canary/recovery. Any predecessor SHA, schema, packet, manifest, proposal, result, policy or artifact digest change invalidates downstream evidence, and production remains human-owned.

## Decision ledger

1. New execution paths preserve M4 legacy semantics rather than overloading `/v1/claims`.
2. Pure packet/protocol contracts precede SQL/state integration so untrusted native data cannot define persistence semantics.
3. Provider support means exact-version fixture conformance, not a binary name or optimistic capability declaration.
4. OS isolation evidence is a separate host exit gate; fake-runtime success cannot satisfy it.
