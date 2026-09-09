# Architect analysis — bounded M5 local execution control plane

## Recommendation

Implement one additive, disabled-by-default execution control plane on exact M4
`67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4`, reusing the reviewed M5 source lineage through
`3940267ac5754ad07a047894102015d33eb759b1`. The bounded outcome is durable control and evidence for an
offline execution lifecycle; it is not a live provider launcher, host-isolation claim, deployment, or external
operation.

The minimum coherent vertical path is:

```text
authenticated repository-scoped worker
  -> existing M4 claim / lease / fence / budget authority
  -> trusted offline ExecutionSelectionV1
  -> immutable TaskPacketV1 + RunManifestV1
  -> bounded canonical stages and proposals
  -> trusted snapshot/attestation boundary
  -> one fenced terminal result + existing M4 disposition
  -> bounded restart recovery and exact-handle cleanup
```

Migrations `014`-`017` are one inseparable schema unit: `014` establishes execution records, `015` replaces
provisional persistence with canonical validation and separate attestor authority, `016` drops only the two
constraints superseded by `015`, and `017` adds fenced recovery and fixed-cardinality metrics. Importing only a
prefix would preserve known provisional weaknesses.

## Components and boundaries

| Boundary | Reused canonical source | Bounded responsibility |
| --- | --- | --- |
| Immutable contracts | `execution_contracts.py`; four execution JSON Schemas | Closed packet, manifest, workspace-result and digest domains; M5 packet identity remains distinct from M4 intent identity. |
| Untrusted output | `protocol.py`, `adapters/` fixtures | Strict bounded JSON/JSONL projection; exact-version offline conformance only; no subprocess, SDK, network call or fallback. |
| Capability brokers | `brokers.py`, `workspace.py` | Validate notes, artifact references, usage and terminal proposals; expose opaque workspace handles and deterministic test doubles, not OS-isolation authority. |
| Durable authority | migrations `014`-`017`, additive portions of `store.py` and `recovery.py` | Row-locked task/run/owner/fence/allocation/packet/deadline checks, append-only evidence, exact replay, terminal uniqueness and bounded recovery. |
| Application/API | additive portions of `models.py`, `state.py`, `service.py`, `api.py`, `server.py`, `settings.py`, `admin.py`, `migrations.py` | Reuse M4 authentication and authorization, keep execution disabled by default, and fail startup closed when trusted dependencies or distinct DB capabilities are absent. |
| Wire contracts | `factory-execution.v1.json` and `factory-execution.v2.json` | Six logical operations: claim, stage, note, artifact, usage and terminal. Retain both already-written projections over common handlers; v1 is compatibility-shaped and v2 returns the strict result-bearing terminal projection. Add no third surface and do not merge them into the M4 control document. |

`repository_id` is the existing tenancy boundary. This slice must not invent a stronger organization/user tenant
model: every execution mutation derives the repository from the locked M4 task and checks it against the actor's
repository set. A request-supplied task, run, owner, packet, workspace or repository identifier never grants
authority.

The built-in Codex and Grok adapters remain offline fixtures and `execution_eligible=false`. Tests may inject a
closed test-only trusted profile and deterministic brokers to exercise the lifecycle. The packaged server must
not synthesize that composition: `FACTORY_EXECUTION_ENABLED=false` remains the default, and enabling without the
registry, snapshot broker, artifact broker, separate attestor connection and readiness checks fails before the
Unix socket is exposed.

## Critical invariants

1. **M4 is monotonic authority.** The existing task state, lease, owner, role, fence, capacity, deadline, budget,
   kill switch and transition policy remain authoritative. M5 can further restrict them but cannot bypass or
   enlarge them.
2. **M4 identity is preserved.** Legacy `task.packet_digest == accepted_intent.intent_digest` and `/v1/claims`
   remain unchanged. `TaskPacketV1.packet_digest` is a separate domain-bound digest and is never written back as
   the legacy packet digest.
3. **Repository isolation is end-to-end.** Actor scope, repository authorization, current owner, live allocation,
   task/run identity, fence and opaque workspace handle must all agree in service and SQL before mutation.
4. **Evidence is immutable and replay is exact.** Packets/manifests are insert-once; stages/proposals/results and
   recovery outcomes append. The same idempotency key may return only byte-equivalent prior output; conflicting
   reuse fails closed.
5. **Provider output has no authority.** Native records can propose only closed, bounded canonical events. They
   cannot select provider/policy/stage, mutate M4, supply a trusted snapshot, expose secrets/raw streams/private
   reasoning, or initiate external actions.
6. **Terminalization is fenced.** At most one terminal proposal, stage and workspace result exist for a run; a
   stale owner/fence or unavailable/mismatched trusted snapshot/attestation commits nothing.
7. **Recovery is factual.** Loss of M4 authority may append `orphaned`/`cancelled`, release M4 allocation and queue
   exact-handle cleanup. It never fabricates a provider proposal, attestation or successful workspace result.
8. **No operational capability is implied.** Source, fixtures, fake brokers and disposable PostgreSQL evidence do
   not establish live provider, credential, network, workspace, rootless-host, deployment or merge authority.

## Finite acceptance criteria

These nine criteria are the complete local acceptance boundary; additions require an explicit scope change.

1. **AC-001 — M4 non-regression.** Migrations `001`-`013` remain byte-identical, the M4 control OpenAPI remains
   byte-identical (baseline SHA-256
   `566209fdcf4db042ba4b7fa0c349d3308b86832208849dd4cbe3b8bf86ecec9e`), all existing 17 control operations retain
   their schemas/behavior, and a legacy claim still returns the intent digest.
2. **AC-002 — contiguous safe schema.** A fresh database and an exact M4 schema-13 database migrate transactionally
   to `014`-`017`; checksum drift, PostgreSQL below 17, unsafe role membership, non-empty canonicalization gates,
   timeout or partial failure leaves the prior schema/evidence unchanged.
3. **AC-003 — immutable execution identity.** Given one live M4 grant and trusted selection, claim creates exactly
   one canonical packet and manifest bound to task/run/repository/owner/role/fence, exact SHAs, authority digests,
   provider profile, capability policy, ordered plan, acceptance IDs, workspace handle and limits. Changed input
   changes the digest; conflicting replay is rejected.
4. **AC-004 — offline provider neutrality.** Exact Codex/Grok fixture versions project only allowlisted canonical
   events under protocol bounds. Unknown versions/events/fields, malformed or oversized streams, identity or
   sequence mismatch, hidden-reasoning fields, post-terminal data and provider fallback fail closed. No product
   path executes a provider or network call.
5. **AC-005 — authorization and tenancy.** Every execution route requires an authenticated worker with
   `task:execute`, owner equality and repository authorization. Cross-repository, cross-task, cross-run,
   cross-workspace, stale-fence and reader-write attempts return a closed denial and leave durable state unchanged.
6. **AC-006 — closed API surface.** With execution disabled, all M5 routes are absent and M4 remains usable. With
   complete injected test composition, the six v1/v2 logical operations match their separate closed OpenAPI
   artifacts, body limits and idempotency rules; provider-native commands, environment values and secrets are not
   accepted.
7. **AC-007 — durable proposal/finalization.** Stages and note/artifact/usage/terminal proposals persist in strict
   sequence under the live fence and budget. A server-owned terminal operation verifies trusted evidence, writes
   one immutable result and maps to the existing M4 `ready_for_human`, typed retry/dead/needs-human policy
   atomically; crash/replay yields one outcome.
8. **AC-008 — bounded restart recovery.** On disposable PostgreSQL 17, a restart with nonterminal work discovers at
   most 2..100 indexed candidates per call within the 30-second budget, fences concurrent claims, preserves live
   work, terminalizes stale work factually, and records deterministic at-least-once cleanup where
   `already_absent` is success. A second restart proves durable replay and no duplicate/synthetic evidence.
9. **AC-009 — exact-tree evidence.** Focused contract, protocol, adapter, broker, service/API, migration,
   persistence and recovery checks pass; existing M4 regression checks pass; final PR-mode verification and every
   route-selected independent review are bound to the same clean source/artifact fingerprint. No live/external
   check is counted as local acceptance evidence.

## Conflict policy for porting `3940267` onto `67dc4dd`

1. Exact M4 wins every overlap. Do not merge or cherry-pick the canonical branch wholesale. Migrations `001`-`013`
   happen to be byte-identical between the two heads, but the canonical M4 control OpenAPI is not (canonical digest
   `83f180e664d199fe37ded7b02d60b9e40f44ce777e0244c680a435bd3a975db4`); keep the `67dc4dd` artifact.
2. Copy add-only M5 modules/contracts/fixtures/migrations from canonical source, then manually graft only M5 symbols
   into overlapping factory files. Begin each overlap from `67dc4dd`; never replace current `store.py`, `api.py`,
   `service.py`, policy/hooks, architecture engine, tests or state documents with the older canonical whole file.
3. If a canonical M5 expectation conflicts with current M4 behavior, adapt the M5 seam and its test. Do not weaken
   current M4 authorization, history, accounting, API, verifier, packaging or authority-composition behavior.
4. Preserve the canonical closed execution contracts once selected. A necessary contract change must be explicit
   and versioned; it must not silently mutate v1. Runtime routes and OpenAPI artifacts are checked bidirectionally.
5. Do not import canonical release ZIPs, runtime receipts, route IDs, stale milestone status or historical docs.
   Update current documentation from final facts, then rebuild the package from the final clean source only.

## Forward recovery and rollback

- **Before packet persistence:** release the acquired M4 grant through its existing typed failure path. If cleanup
  cannot be recorded, return failure and leave reconciliation evidence; never continue with an unbound manifest.
- **After packet persistence:** retry only with the exact command/idempotency key. Stale authority routes the run to
  recovery, which appends a factual terminal event, releases capacity and retries exact-handle cleanup under a new
  recovery fence.
- **Migration failure:** all `014`-`017` application is transactional and timeout-bounded. Stop on any precondition
  failure; retain schema 13 and its checksums.
- **Application rollback before any persistent apply:** revert the unmerged M5 source or keep execution disabled;
  M4 continues unchanged.
- **Application rollback after schema 17 exists:** first stop new execution claims, reconcile outstanding runs and
  preserve all execution tables. Disable M5 routes and forward-fix application/schema with migration `018+`.
  Never down-migrate, drop execution evidence, rewrite `001`-`017`, or reuse evidence from another SHA.

## Explicitly deferred

- live provider invocation, executable discovery and new native/provider versions;
- actual workspace/Git mutation, credential issuance, network egress and binary artifact storage;
- rootless/container isolation qualification, systemd installation/activation and host deployment;
- dynamic provider routing/fallback, fleet scheduling, HA/load testing, pricing feeds and retention GC;
- M6 semantic verdict/repair, pull-request creation, Trust CI, merge, release and production actions;
- a tenant hierarchy beyond the existing repository-scoped authorization boundary.

These deferrals do not weaken the nine local criteria; the disabled-by-default boundary prevents them from being
mistaken for capabilities supplied by this change.
