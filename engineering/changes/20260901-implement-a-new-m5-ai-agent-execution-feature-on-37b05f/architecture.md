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

`/v1/claims` remains an M4 control-plane lease. M5 adds `/v1/execution/claims`, `/v1/execution/stages`, and execution proposal endpoints; it does not infer provider or execution policy from the legacy claim. The execution claim first obtains the M4 fence/capacity lease, then builds and persists one immutable packet and manifest from the accepted intent plus a closed trusted selection. Failure before persistence releases the lease through the existing typed path.

The same local server publishes two bounded contract artifacts: byte-identical M4 baseline `factory-control.v1.json` for legacy control operations and additive `factory-execution.v1.json` for exactly the six M5 `/v1/execution/*` operations. The control artifact is retained/deprecated as a baseline, not presented as unified discovery; route and operation-ID sets are disjoint and the wire namespace remains `/v1`.

Slice 02 deliberately does not yet add the five rich M5 artifacts to `architecture/system.yaml`. Exact-predecessor fitness reports `unsupported added-contract baseline semantics` because the conservative comparator cannot baseline their `const`, `uniqueItems`, and reference constructs. The artifacts remain present, directly validated, collision-tested and installer-owned; explicit registration plus conservative tool support is a mandatory slice-04 integration gate and cannot be replaced by hiding the contracts or weakening policy.

## Source components

- `execution_contracts.py`: frozen nested value objects, canonical packet digest, invocation and manifest contracts.
- `protocol.py`: bounded incremental JSON/JSONL parser and lifecycle state machine.
- `adapters/`: provider-native fixture translators and explicit conformance registry; no process/network invocation.
- `brokers.py`: note/artifact/usage/terminal validation and redaction.
- `workspace.py`: workspace/Git protocols, handle/path/environment policy, fake isolated runtime, host capability probe.
- successor migration `014` after immutable M4 `013`: append-only execution packets/manifests/events/notes/artifacts and execution-stage constraints/functions.
- store/service/API: explicit execution operations checked against task/run/owner/fence/packet/live allocation/deadline/budget.
- `contracts/openapi/factory-execution.v1.json`: closed additive six-operation execution fragment; `factory-control.v1.json` remains byte-identical M4 history.
- `factory/systemd/`: fixed source unit topology only.

## Trust and security

Packet control fields never originate from repository text or native provider events. Adapters have no database, scheduler, GitHub, deployment, fallback, or policy mutation capability. Repository tools receive an allowlisted environment with credential-pattern variables removed and a default-deny network declaration. The fake runtime proves broker behavior, not OS isolation; only a dedicated rootless host with the required kernel/tooling can satisfy the M5 credential/egress exit drills.

## Recovery and rollout

On restart, a bounded reconciler scans at most 100 incomplete manifests in deterministic key order. A manifest with no live matching M4 lease becomes `orphaned`, gains one safe terminal proposal, releases broker-owned workspace state, and cannot accept later events. Rollout is source-only and feature-dark: migration/API/unit files are not applied, started, or enabled by this task. Slice 01 contains no migration; successor slice 02 adds migration `014`, and any accepted-M5 forward-fix uses `015+` without rewriting M4 `013` or M5 `014`.

The shipped server defaults `FACTORY_EXECUTION_ENABLED=false`: the legacy M4 API remains available and the six M5 routes are absent. Enabling execution requires distinct, least-privilege runtime and artifact-attestor sessions plus an explicitly composed trusted profile registry, deterministic read-only artifact verifier, and trusted Git snapshot broker before the Unix socket is bound. This repository does not supply a live trusted Git/provider composition or rootless-host acceptance evidence, so enabled host composition remains blocked rather than falling back to fake brokers or ambient credentials.

## Decision ledger

1. New execution paths preserve M4 legacy semantics rather than overloading `/v1/claims`.
2. Pure packet/protocol contracts precede SQL/state integration so untrusted native data cannot define persistence semantics.
3. Provider support means exact-version fixture conformance, not a binary name or optimistic capability declaration.
4. OS isolation evidence is a separate host exit gate; fake-runtime success cannot satisfy it.
5. First-time rich contract inventory registration waits for an explicit integration/tool-support slice because current fitness fails closed on unsupported baseline semantics; direct contract tests remain mandatory meanwhile.
6. Preserve M4 startup by omitting M5 routes unless a strict feature flag and all trusted execution dependencies pass startup checks; never expose a partially wired execution surface.
