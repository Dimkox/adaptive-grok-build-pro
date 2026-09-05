# Integration architecture — local L5 runtime and reversible publisher

## Scope and baseline

This report is bound to predecessor `f3f8d7375a153393ffba3906165e8d625e45d4a1`,
tree `a8f8d71a745e69b12f630d73ba11e1cdca262c5e`, and route
`65b2018b786d`. It defines repository-local Stages 3 and 4 only. No provider
call, socket, hosting mutation, deployment, or production authority is part of
this change.

The current seams are individually strong but not composed:

- `LandingApplicationService` accepts only `InMemoryLandingJobStore`, performs
  the whole pipeline synchronously, and never durably records intermediate
  states or cancel command identity.
- `PrivateLandingBlobStore` has strong bounded-input and private-file checks,
  but its index is process-local and startup deliberately removes every prior
  blob as an orphan.
- `LandingCoordinator` already enforces the three-attempt writer/evaluator
  boundary, and `LandingArtifactPackager` already creates a deterministic
  20-member ZIP and sidecar through private exact-SHA clones and no-replace
  content-addressed installation.
- There is no concrete bridge from the service's `LandingArtifactBuilder` to
  `LandingCoordinator` and `LandingArtifactPackager`; API tests currently use a
  stub builder.
- `UnavailableLandingPublisher` is intentionally the only shipped publisher.
  M9's `DryRunController` is exact-type sealed to `FakeEnvironmentAdapter`, is
  process-local, and makes production unreachable. It must not be patched or
  reused as a hosting driver.

SQLite is acceptable here only as a new bounded single-operator L5 store. It
does not replace the PostgreSQL M4-M8 control plane, and PostgreSQL migrations
`001`-`018` remain byte-identical. Likewise, the published `v2.0.14` ZIP and the
frozen `landing-dogfood.v1.json` remain byte-identical.

## Stage 3 — restart-safe single-node pipeline

### Smallest component shape

Keep `LandingApplicationService` as the authenticated API facade, but replace
its concrete store check with a structural port and delegate processing to one
runtime object:

```python
class LandingJobStore(Protocol):
    def create_or_replay(
        self, source: LandingInputV1, *, command_key: str, request_digest: str
    ) -> LandingSubmitResult: ...
    def get(self, tenant_id: str, repository_id: str, job_id: str) -> LandingJobRecord: ...
    def claim(self, identity: LandingJobIdentity, *, now: datetime) -> LandingClaim | None: ...
    def transition(
        self, claim: LandingClaim, target: str, *, evidence: object | None = None
    ) -> LandingJobRecord: ...
    def complete_artifact(
        self, claim: LandingClaim, result: LandingArtifactResult
    ) -> LandingJobRecord: ...
    def cancel(
        self, identity: LandingJobIdentity, *, command_key: str, request_digest: str
    ) -> LandingJobRecord: ...
    def recover(self, *, now: datetime) -> LandingRecoveryResult: ...
    def retained_inputs(self) -> tuple[LandingInputV1, ...]: ...

class LandingPipeline(Protocol):
    def run(self, claim: LandingClaim, source: LandingInputV1) -> LandingJobRecord: ...
```

`InMemoryLandingJobStore` remains a test/offline implementation of this port.
`SQLiteLandingJobStore` is the runtime implementation. A single
`CoordinatedLandingBuilder` performs the missing bridge:

1. call the injected `LandingProvider` and validate the existing exact input,
   profile, request, and response bindings;
2. persist canonical `StaticLandingSpecV1` and
   `LandingProviderEvidenceV1` before deleting the raw blob;
3. call `LandingCoordinator.run(spec, profile_digest=...)`;
4. if `candidate_ready`, bind its final attempt and evaluation to the selected
   snapshot and call `LandingArtifactPackager.seal(...)` with a trusted,
   preconfigured artifact root;
5. pass the complete `LandingArtifactResult`, not merely `SiteArtifactV1`, to
   `complete_artifact` so ZIP, sidecar, manifest bytes, and database projection
   are checked together.

The runtime must commit `normalizing` with the current claim before invoking
the provider; therefore a persisted `accepted` record proves that no provider
call was started by this runtime.

The runtime receives provider, workspace, renderer, evaluator, packager,
SQLite path, quarantine root, and artifact root only from trusted composition.
No request may choose an executable, Git source, output directory, host, path,
credential, or transport. Default server composition remains
`UnavailableLandingProvider` unless an explicitly configured local profile is
injected; Stage 3 itself performs no model/network call.

### Durable state and filesystem invariant

Use the standard-library `sqlite3` module; do not add a datastore dependency.
The database and its WAL/SHM files live under one absolute host-owned `0700`
directory outside the repository. Reject symlinks or non-owned/non-regular
database files, bind/recheck directory identity around open, create under
`umask 0077`, and enforce database mode `0600`. Each connection enables
`foreign_keys=ON`, `journal_mode=WAL`, `synchronous=FULL`,
`trusted_schema=OFF`, and a finite `busy_timeout`; mutations use bounded
`BEGIN IMMEDIATE` transactions.

Use a private L5 schema/version table, not the PostgreSQL migration loader.
Minimum tables are:

- `landing_jobs`: composite identity `(tenant_id, repository_id, job_id)`,
  canonical input/spec/provider records, current state, version, claim epoch,
  cancellation marker, artifact digest, bounded terminal reason, and times;
- `landing_commands`: unique `(tenant_id, repository_id, action, command_key)`
  with canonical request digest and canonical result, covering submit and
  cancel replay;
- `landing_events`: append-only per-job sequence, previous-event digest,
  from/to state, evidence digest, reason, and timestamp;
- `landing_attempts` and `landing_evaluations`: immutable canonical records,
  unique by job and ordinal/digest, capped at three attempts;
- `landing_artifacts`: immutable canonical `SiteArtifactV1`, manifest bytes,
  deterministic ZIP/sidecar names and creation time. Paths are reconstructed
  below trusted artifact root; absolute/caller paths are never stored.

Every canonical record is parsed again through its `from_json`/`from_dict`
constructor on read. The current projection and event append occur in one
transaction. A transition supplies an exact claim epoch and expected version;
a cancelled or recovered job therefore rejects a stale worker completion.

The existing quarantine can be extended with an optional bounded
`retained_records` input. At startup it adopts only SQLite-referenced,
unexpired blobs whose filename, ownership, mode, link count, length, and digest
match the canonical `LandingInputV1`; default empty input preserves the current
"remove all startup orphans" behavior. File creation/fsync precedes the job
commit; an unreferenced crash-left blob is safely swept.

Artifact installation and directory fsync precede the SQLite artifact/job
commit. On startup, referenced ZIP/sidecar pairs are rehashed and their exact
sidecar content and manifest binding are checked. Known-pattern unreferenced
pairs are bounded garbage and may be removed after reconciliation; unknown
files are never followed or deleted. Missing or conflicting referenced bytes
terminalize the job as `needs_human`/integrity failure rather than being
silently rebuilt.

### State machine and restart ruling

The external v1 state vocabulary is retained:

```text
accepted -> normalizing -> generating -> evaluating -> artifact_ready
                         -> provider_unavailable | rejected | needs_human
generating <-> evaluating               (maximum three persisted attempts)
any non-cancelled state -> cancelled     (explicit cancel is the sole superseder)
```

`artifact_ready`, provider failure, rejection, and `needs_human` are immutable
except that the existing v1 cancel behavior may tombstone them as `cancelled`.
Cancellation increments the claim epoch and hides the artifact from the job
result but never mutates or reuses immutable CAS bytes.

Restart behavior is deliberately fail-closed:

| Persisted condition | Reconciliation |
| --- | --- |
| `accepted` plus exact retained blob | Safe to claim and start; the provider has not yet been invoked. |
| stale `normalizing` | `needs_human(provider_outcome_ambiguous)`; never automatically repeat a possibly completed Codex/provider call. |
| stale `generating` or `evaluating` | `needs_human(local_run_interrupted)` for this MVP, preserving the actual three-attempt ceiling. A later resumable coordinator may replace this without changing the store port. |
| complete referenced artifact | Revalidate and retain `artifact_ready`; do not rerun provider/coordinator. |
| installed but unreferenced CAS pair | Remove as bounded orphan; do not infer a job result from filenames. |
| cancelled/terminal job | Replay the stored projection with zero provider, workspace, or CAS effect. |

This is restart-safe, not falsely resumable: no job remains stuck and no
ambiguous external operation is borrowed or repeated.

### API compatibility

The existing `202` submit and GET/cancel/result bodies need no semantic change;
`live_url` remains `null`. Persist and enforce the cancel idempotency key, which
the current service discards. A repeated key with the same canonical request
returns the recorded result; the same key with different input/action material
returns `409 idempotency_conflict` before provider or filesystem work.

Do not edit the frozen v1 OpenAPI source pins. The runtime source remains the
trusted current SHA/tree constants. Voice remains unsupported by the selected
MVP provider: audio may follow the published intake contract to a closed
`provider_unavailable`/rejected result, but it must never invoke Codex or fall
back to another model. Removing audio media types from v1 would be a breaking
contract change and is not required for Stages 3-4.

## Stage 4 — transport-injected reversible publisher

### Boundary and interfaces

Preserve `UnavailableLandingPublisher` and its exact zero-transport surface.
Add a separate library-only `ReversibleLandingPublisher`; do not inject it into
`factory.server` in this change. The repository ships no HTTP/FTP/SFTP/cPanel
transport. Tests provide the only concrete transport and patch socket/process
creation to prove zero external capability.

The publisher consumes a verified artifact source rather than caller paths:

```python
class LandingArtifactSource(Protocol):
    def load_verified(self, artifact_digest: str) -> VerifiedLandingBundle: ...

class LandingHostingTransport(Protocol):
    def observe_active(self) -> HostingSnapshot: ...
    def observe_staged(self, release_id: str) -> HostingSnapshot | None: ...
    def stage(
        self, release_id: str, members: tuple[VerifiedMember, ...], *, operation_id: str
    ) -> HostingSnapshot: ...
    def activate(
        self, release_id: str, *, expected_active_digest: str, operation_id: str
    ) -> None: ...
    def restore(
        self, snapshot_id: str, *, expected_active_digest: str, operation_id: str
    ) -> None: ...
```

The transport is constructed from trusted target configuration; methods take
no URL, docroot, username, credential, shell command, or arbitrary path.
`HostingSnapshot` is a closed immutable value containing target/config digest,
opaque snapshot identity, sorted member path/digest/size records, tree digest,
and capture time. `release_id` and `operation_id` are deterministically derived
from publication/artifact/action digests.

The service operations are explicit and independently replayable:

```python
prepare(artifact_digest, *, target_config_digest, command_key) -> Publication
stage(publication_id, *, command_key) -> Publication
activate(publication_id, *, command_key) -> Publication
observe(publication_id) -> Publication
restore(publication_id, *, command_key) -> Publication
reconcile(publication_id) -> Publication
```

`prepare` revalidates ZIP, sidecar, manifest, all 20 regular non-executable
members, total size, and source/artifact identities before touching transport.
It then captures and durably binds an exact restorable baseline. An absent,
unrestorable, changing, or oversized baseline fails closed.

### Publication transitions and effects

Persist a small append-only publication ledger, using the same SQLite hardening
rules but a separate store/namespace from job state:

```text
prepared -> staging -> staged -> activating -> activated -> observed
                                             activated -> restoring -> restored
                                              observed -> restoring -> restored
any integrity/current-state ambiguity -> needs_human
```

- **Stage:** use content-addressed `release_id`; copy only manifest-declared
  validated members. It must not change the active snapshot. Replay verifies
  the existing staged digest and uploads only provably absent identical members.
- **Activate:** compare-and-swap against the exact baseline digest and perform
  one transport operation. Persist `activating` before the call. Afterward,
  observe: exact candidate means `activated`; exact baseline means no effect and
  remains explicitly retryable; any third/mixed tree is `needs_human`.
- **Observe:** read-only. It reaches `observed` only when active member/tree
  digests exactly equal the candidate. It does not imply public HTTPS,
  indexability, or indexing.
- **Restore:** permitted only with the bound baseline snapshot and when current
  active bytes are exactly candidate or already baseline. Compare-and-swap on
  candidate digest, invoke one restore, then observe exact baseline. Unknown
  bytes are never overwritten or deleted.
- **Reconcile:** performs observations only. Interrupted `staging` may resume
  exact missing members; interrupted `activating`/`restoring` is resolved from
  observed candidate/baseline state and never blindly repeats a mutation.

Every mutating action has a durable command row: same action/key/request returns
the prior result with zero transport calls; changed material conflicts. Store
intent before transport, result after transport, and never hold a SQLite write
transaction across a transport call. The fake transport must support injected
crash points before effect, after effect/before receipt, CAS mismatch, partial
stage, changed baseline, and exact replay.

This port maps cleanly to a later cPanel/LiteSpeed adapter: verified members can
be uploaded to a versioned release, active state can be observed, and activation
can use a proven atomic docroot/pointer primitive. If the actual cPanel account
cannot provide atomic compare-and-swap plus a restorable snapshot, that future
adapter must report `unsupported`; fake tests cannot prove the hosting control
plane. LiteSpeed requires no special authority in this source slice.

Real transport composition remains a later security-sensitive change requiring
exact target configuration, secret handle, TLS/egress policy, action/resource
grants for stage/activate/restore, and live recovery evidence. None is simulated
by local receipts.

## Exact likely file plan

Stage 3:

- add `factory/src/adaptive_factory/landing_sqlite_store.py`;
- add `factory/src/adaptive_factory/landing_runtime.py` containing the concrete
  provider/coordinator/packager bridge;
- change `landing_service.py` to depend on the store/runtime ports and persist
  cancel identity;
- minimally extend `landing_intake.py` for validated retained-record adoption;
- change `settings.py` and `server.py` only for explicit absolute local state,
  quarantine, artifact, and exact-source configuration while keeping the
  unavailable default;
- do not add `resources/019_*.sql` and do not edit the frozen v1 OpenAPI.

Stage 4:

- leave `delivery/src/adaptive_delivery/landing_publisher.py` backward
  compatible;
- add `landing_publication_contracts.py`, `landing_publication_store.py`, and
  `landing_reversible_publisher.py` under `delivery/src/adaptive_delivery/`;
- keep `FakeLandingHostingTransport` in tests, not product composition.

Repository inventories in `tests/test_structure.py` and the relevant
`architecture/system.yaml` / `architecture/rules.yaml` path declarations must
be updated additively for real new source files. Published package artifacts are
not edited in place.

## Critical focused tests

1. `factory/tests/test_landing_sqlite_store.py`: fresh schema, reopen/replay,
   composite tenant isolation, canonical-record tamper rejection, submit/cancel
   key conflict, stale claim/fence, immutable artifact rows, WAL/path modes, and
   bounded lock failure.
2. `factory/tests/test_landing_runtime.py`: provider -> coordinator -> exact
   20-member artifact; `needs_human` branch; no fourth attempt; blob purge only
   after durable normalized checkpoint; crash/reopen at every phase; ambiguous
   provider is never repeated; existing artifact is never rebuilt.
3. Extend `test_landing_intake.py`: referenced blob adoption, expired/tampered
   reference rejection, and unreferenced orphan cleanup without following links.
4. Extend `test_landing_api.py`: persistence across app recreation, exact replay
   has zero provider calls, changed-body conflict, durable cancel replay,
   tenant/repository isolation, voice causes zero Codex calls, and `live_url`
   remains null.
5. Extend `test_server.py`: disabled/default composition remains unavailable;
   all local paths must be absolute, private, outside Git, and supplied as one
   complete configuration.
6. `delivery/tests/test_landing_reversible_publisher.py`: invalid artifact fails
   before transport; stage leaves baseline active; stage replay is zero/finite
   effect; activation CAS; after-effect/before-receipt reconciliation; exact
   observation; restore and restore replay; changed/mixed active tree fails
   without overwrite.
7. `delivery/tests/test_landing_publication_store.py`: reopen every transitional
   state, command conflicts, append-only evidence chain, stale version rejection,
   and canonical snapshot validation.
8. Preserve and extend `test_landing_publisher.py` to prove the default
   unavailable publisher still inspects neither artifact nor transport and that
   no production transport implementation is shipped.

Focused tests should use temporary private directories and deterministic fake
time/transport only. No full suite, network probe, external Codex execution,
hosting mutation, or live/indexed claim belongs to this analysis or its Stage 4
implementation evidence.
