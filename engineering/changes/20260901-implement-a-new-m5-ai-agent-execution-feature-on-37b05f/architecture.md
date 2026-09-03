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

The same local server publishes byte-identical M4 `factory-control.v1.json`, enrolled execution-v1, and additive strict execution-v2 artifacts. The six `/v1/execution/*` routes preserve their enrolled response contract; `/v2/execution/*` is a real selectable wire path with strict route-specific responses. Both terminal versions invoke the same server-owned proposal → trusted snapshot → atomic finalize saga, but v1 projects its legacy proposal-only response while v2 includes the canonical workspace result.

Successor 04 registers the five original M5 contract artifacts and adds bounded fail-closed comparator support for their rich constructs and declared references. It is clean and independently reviewed at `27b0ae6`; successor 05 adds v2 on that exact predecessor. Cumulative M4→successor-04 change size exceeds policy, so delivery must remain a sequence of immediate-predecessor PRs rather than a squash.

## Source components

- `execution_contracts.py`: frozen nested value objects, canonical packet digest, invocation and manifest contracts.
- `protocol.py`: bounded incremental JSON/JSONL parser and lifecycle state machine.
- `adapters/`: provider-native fixture translators and explicit conformance registry; no process/network invocation.
- `brokers.py`: note/artifact/usage/terminal validation and redaction.
- `workspace.py`: workspace/Git protocols, handle/path/environment policy, fake isolated runtime, host capability probe.
- successor migrations `014`-`016` after immutable M4 `013`: canonical execution packets/manifests/events/proposals/attestations/results and trusted finalization.
- migration `017`: PostgreSQL-17-only recovery jobs/claims/outcomes and atomic fixed metrics with a zero epoch and no historical backfill; M6 begins at `018`.
- store/service/API: explicit execution operations checked against task/run/owner/fence/packet/live allocation/deadline/budget.
- `contracts/openapi/factory-execution.v1.json` and `.v2.json`: compatible v1 plus additive strict v2 execution surfaces; `factory-control.v1.json` remains byte-identical M4 history.
- `factory/systemd/`: planned fixed inert source unit topology only; the directory and its four unit/parser-test files are not present yet.

## Trust and security

Packet control fields never originate from repository text or native provider events. Adapters have no database, scheduler, GitHub, deployment, fallback, or policy mutation capability. Repository tools receive an allowlisted environment with credential-pattern variables removed and a default-deny network declaration. The fake runtime proves broker behavior, not OS isolation; only a dedicated rootless host with the required kernel/tooling can satisfy the M5 credential/egress exit drills.

## Recovery and rollout

Recovery uses two work-conserving lanes and a limit of 2..100: raw nonterminal keyset discovery and due cleanup retries share bounded indexed work without starving either source. A 30-second monotonic invocation budget and PostgreSQL 17 transaction timeout cover setup, validation and mutation; the fresh cursor advances only through authoritatively processed rows and wraps after exhaustion. When M4 authority is gone, recovery appends the factual terminal stage/event, performs canonical M4 release, and schedules exact-handle workspace cleanup. It creates **zero synthetic execution proposals, workspace results or attestations**. Cleanup is at-least-once after claim expiry/crash: release must be deterministic/idempotent, `already_absent` is success, and stale fences cannot commit outcomes. The actual two-restart probe remains open, so this source behavior is not yet an M5 exit claim. Any accepted-M5 forward fix and the first M6 migration use `018+`.

The shipped server defaults `FACTORY_EXECUTION_ENABLED=false`: the legacy M4 API remains available while both six-operation execution surfaces—all 12 `/v1/execution/*` and `/v2/execution/*` paths—are absent. Enabling execution requires distinct, least-privilege runtime and artifact-attestor sessions plus an explicitly composed trusted profile registry, deterministic read-only artifact verifier, and trusted Git snapshot broker before the Unix socket is bound. This repository does not supply a live trusted Git/provider composition or rootless-host acceptance evidence, so enabled host composition remains blocked rather than falling back to fake brokers or ambient credentials.

## Decision ledger

1. New execution paths preserve M4 legacy semantics rather than overloading `/v1/claims`.
2. Pure packet/protocol contracts precede SQL/state integration so untrusted native data cannot define persistence semantics.
3. Provider support means exact-version fixture conformance, not a binary name or optimistic capability declaration.
4. OS isolation evidence is a separate host exit gate; fake-runtime success cannot satisfy it.
5. Rich contract inventory registration and bounded comparator support are isolated in frozen successor 04 so later v1 changes are evaluated old-to-new; added contracts never self-enroll after mutation.
6. Preserve M4 startup by omitting M5 routes unless a strict feature flag and all trusted execution dependencies pass startup checks; never expose a partially wired execution surface.
