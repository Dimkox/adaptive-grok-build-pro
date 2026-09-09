# Repository inventory — L5 local runtime and next-stage composition

## Binding and conclusion

This read-only inventory is bound to route `65b2018b786d`, predecessor
`f3f8d7375a153393ffba3906165e8d625e45d4a1`, and tree
`a8f8d71a745e69b12f630d73ba11e1cdca262c5e`. The branch is two commits ahead
of `origin/main` (`33206fa06ae4b5bfb390cb68bbf233800d2902ab`); the only worktree content not in
the predecessor is the untracked active change package.

The landing vertical already has strong closed contracts, private bounded intake,
an exact-source two-file renderer, an independent three-attempt evaluator loop,
and deterministic artifact sealing. It does **not** yet have a real Codex adapter,
a concrete coordinator-to-packager builder, restart-safe job/artifact state, or a
reversible publisher. Those are the minimum additive seams for Stages 2–4.

The M4–M9 lineage can supply most of the durable control/evidence model for the
later issue-to-PR proof, but it cannot execute that proof as shipped: issue
ingestion, an execution-eligible Codex runner, a real isolated writable Git
workspace, branch publication, PR creation, and human-decision ingestion are
absent. Trust CI begins only after a PR exists. cPanel hosting is downstream and
is not a substitute for that product-stage gate.

## Existing landing vertical

| Concern | Reusable implementation | Current gap/coupling |
| --- | --- | --- |
| Contracts | `factory/src/adaptive_factory/landing_contracts.py`: `LandingInputV1`, `StaticLandingSpecV1`, provider/attempt/evaluation/artifact evidence; closed JSON parsing, digests, same-origin CTA rules, input ceilings. | Audio is part of the published v1 intake. Keep it compatible and reject it in the selected provider; do not remove it from v1. `static-landing-spec.v1.schema.json` requires computed `spec_digest`, so it is not a valid direct model-output schema. |
| Intake | `landing_intake.py:75-308`: private `0700` root, regular `0600` content-addressed blobs, shape checks, digest rechecks, bounded expiry/purge. | Its record index is in memory and `_sweep_startup_orphans()` deletes all prior owned blobs. Durable jobs therefore cannot survive restart until referenced-record adoption replaces unconditional sweeping. |
| Provider | `landing_provider.py:66-210,213-526`: exact executable path/SHA profile, unavailable default, no-shell fixed command, sterile environment, process-group timeout, concurrent bounded output, strict fixture JSONL decoding. | `FixedCommandLandingProvider` implements a proprietary fixture protocol and reports `fixture_ready`; it is not native Codex. `adapters/codex.py` only translates fixture events and is explicitly `execution_eligible=False`. The installed CLI exposes image attachment but no PDF/DOCX attachment; these need deterministic local extraction. |
| Renderer/workspace | `landing_renderer.py:24-30,328-705`: current landing SHA `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree `f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`, writes only `index.html` and `content.css`, private `--no-local --no-hardlinks` clone, detached exact checkout, source/tree/object/mode guards, deterministic commit. | This workspace is correctly landing-specific. It should not be generalized into the arbitrary issue-repository executor needed by the later proof. |
| Coordination/evaluation | `landing_coordinator.py:22-213` and `landing_evaluation.py:25-194`: independent writer/evaluator identities, a maximum of three candidates, closed repair reasons, bound pass/repair/needs-human results. | Results exist only for the duration of the synchronous call. Each attempt and evaluation needs a durable checkpoint before the next effect. |
| Artifact | `landing_artifact.py:35-60,73-82,83-277,279-881`: exact source/candidate materialization, protected 20-member inventory, deterministic ZIP/manifest/uppercase sidecar, no-replace installation, full provenance and digest binding. | The service protocol returns only `SiteArtifactV1`; no concrete builder composes workspace, coordinator and `LandingArtifactPackager`, and no durable CAS/job link retains the full `LandingArtifactResult`. |
| Service/API | `landing_service.py:96-320` and `api.py:480-617`: tenant/repository/job binding, exact source gate, authenticated submit/read/cancel/result routes, unavailable behavior. | Constructor accepts only concrete in-memory/blob classes. Submit runs provider through artifact synchronously under a process lock, persists only accepted/final, collapses unexpected errors to an unclassified `needs_human`, purges the blob, and discards cancel idempotency. API returns the final state under HTTP 202 rather than queuing durable work. |
| Composition | `settings.py:71-130`, `server.py:126-212`, `factory/pyproject.toml:5-17`: Unix-socket FastAPI server and optional quarantine path. | Server always requires the M4 PostgreSQL store and actors file. Landing composition is in-memory plus `UnavailableLandingProvider`; there are no SQLite, CAS, exact source, Codex profile, or landing-only entrypoint settings. Decide explicitly whether the local MVP retains this PostgreSQL dependency or add a narrow landing-only composition rather than silently claiming SQLite-only startup. |
| Delivery | `delivery/src/adaptive_delivery/landing_publisher.py`: the only publisher ignores the artifact and raises `publication_unavailable`. | There is no transport, baseline snapshot, staging, compare-and-swap activation, observation, reconciliation, or restore. M9 `FakeEnvironmentAdapter` is a sealed dry-run deployment boundary, not a hosting transport, and must remain unchanged. |

The repaired predecessor invariants are already correct: renderer `1.0.1`, protected
source `index.css`, two generated paths, 20 deploy members, and frozen published
OpenAPI/package bytes. The new implementation should compose them rather than
reimplement them.

## Smallest coherent deltas

### Stage 2 — exact Codex normalization

Add a dedicated `factory/src/adaptive_factory/landing_codex.py`; do not alter the
fixture decoder into a second protocol. Reuse `LandingProvider.normalize` and the
bounded subprocess mechanics, but give the adapter a sealed, operator-owned
profile that fixes the resolved regular executable and SHA-256, exact CLI/model,
prompt/tool/output-schema/decoder digests, argv, timeout and output ceilings.
Default composition remains unavailable.

Add a facts-only `landing-normalization-draft.v1` schema containing only the
model-selectable copy fields. Trusted code supplies input/source/site/provenance
fields and computes `StaticLandingSpecV1.spec_digest` locally. Decode native JSONL
for one supported CLI version, reject unexpected tool activity/output, retain no
reasoning or raw stderr, and record a truthful `normalized`/failure disposition
rather than `fixture_ready`.

Media adapters should be explicit and fail closed:

- strict UTF-8 text is normalized in process;
- a validated image is supplied through the CLI's single image attachment seam;
- safe DOCX text is extracted deterministically from the already-validated OOXML;
- PDF requires a separately pinned, bounded extractor (none exists in current
  dependencies); without it PDF is `needs_human` before Codex;
- audio/voice returns unsupported before reading the blob or invoking Codex.

The local `codex 0.153.4` binary observed during inspection is
`/home/pall/.codex/packages/standalone/releases/0.153.4-x86_64-unknown-linux-musl/bin/codex`,
SHA-256 `56ef98ab4032d317ab26e9b5e5a175650717351edb16ed9cde0cb6d1734d62da`.
This is environment evidence, not a checked-in default. A later activation must
prove an actually no-tool/sterile execution capability; `--sandbox read-only`
alone still allows model-requested reads and is not that proof.

### Stage 3 — restart-safe single-operator runtime

Introduce structural `LandingJobStore`/blob/runtime ports and keep the in-memory
implementations for existing tests. Add `landing_sqlite_store.py` using stdlib
`sqlite3` under one trusted absolute private runtime root. Minimum durable data is:

- composite tenant/repository/job identity, immutable canonical input, state,
  revision, lease/fence, bounded reason and timestamps;
- submit/cancel command key plus canonical request/result digest;
- immutable normalized spec/provider evidence and each of at most three
  attempt/evaluation checkpoints;
- immutable artifact/manifest metadata and a job-to-artifact link to private CAS;
- append-only state events.

Every mutation must compare expected revision/fence. Persist `normalizing` before
the external provider call and the validated normalization result before purging
input. On restart, only untouched `accepted` work is safe to claim. A stale
`normalizing` job becomes `needs_human/provider_outcome_ambiguous`; never replay a
possibly completed Codex call. Interrupted local generation/evaluation may also
fail closed for this MVP. Reopen revalidates canonical contracts plus ZIP,
sidecar, manifest and CAS bytes before exposing `artifact_ready`.

Add `landing_runtime.py` with the missing concrete bridge:

```text
provider -> StaticLandingSpecV1 checkpoint
         -> ExactGitLandingWorkspace/LandingCoordinator (<=3 attempts)
         -> LandingArtifactPackager
         -> atomic CAS install + SQLite artifact/job commit
```

`PrivateLandingBlobStore` should adopt only referenced, unexpired, mode/owner/link/
length/digest-valid records supplied by the durable store; it may still remove
known-pattern unreferenced orphans. Caller-controlled executable/model/source,
filesystem roots and output paths remain forbidden.

### Stage 4 — fake-transport reversible publication

Keep `UnavailableLandingPublisher` byte-compatible and the server unwired. Add a
separate reversible publisher, closed publication/snapshot contracts, and a small
durable ledger. Its injected transport receives only validated members and opaque
content-derived release/operation IDs; destination, credentials and paths come
from trusted construction, never the artifact or request.

Required sequence is `prepare -> stage -> activate -> observe -> restore`, with
read-only reconciliation. `prepare` revalidates all artifact bindings and captures
an exact restorable baseline; `stage` cannot change active bytes; `activate` and
`restore` compare-and-swap against exact tree digests. Persist intent before a
transport call, observe after an ambiguous interruption, and never overwrite a
third/mixed state. The only implementation in this route should be a deterministic
test fake. No cPanel/FTP/SFTP/HTTP client, secret reader, `live_url`, or public-host
claim belongs in the MVP.

## True next-stage proof: reusable M4–M9 path and gaps

The intended proof is a separate external-integration route, not an extension of
the landing hosting adapter:

```text
signed/authorized external issue snapshot
  -> M4 durable task, lease, budget, kill/reconcile
  -> M5 exact execution packet and isolated writer result
  -> M6 independent semantic evidence and deterministic verdict
  -> M7 exact evidence bundle
  -> delegated branch push + automatic PR creation
  -> existing Trust CI exact-SHA App-owned check
  -> independently captured human accept/reject
```

Reusable today:

- M4 `FactoryService`/PostgreSQL store already provide authenticated intake,
  exact authority material, durable leases/fences, idempotency, budgets, usage,
  kill and bounded reconciliation.
- M5 `FactoryService.claim_execution()` (`service.py:421-515`) constructs an
  exact-base/head, route/change/profile/tool-policy-bound `TaskPacketV1` through
  an injected eligible registry. Proposal, artifact attestation and exact
  workspace-result finalization are durable (`service.py:574-839`).
- M6 `semantic_bridge.py`, semantic role stores and
  `semantic_adjudication.adjudicate()` bind requirements, workspace result,
  holdout/review evidence and independent validator identities, then fail closed
  to pass/repair/needs-human.
- M7 evidence contracts join M4/M5/M6, but `ReadyForPrBundleV1` deliberately has
  status `blocked_pending_durable_lookup`; `OperatorHandoffProposalV1` requires
  `external_capability="absent"` and manual human review
  (`shadow_contracts.py:494-618`). It is evidence, not a PR client.
- M8 cohort/autonomy logic is not required for one proof and cannot be inferred
  from it: evaluation requires at least 30 human merged acceptances and an
  observation window/baseline (`shadow_evaluation.py:165-190`), while the bridge
  explicitly reports external acceptance/currentness unavailable
  (`m7_autonomy_bridge.py:167-173`).
- M9 deliberately exposes only non-production fake delivery effects. It supplies
  control-pattern examples, not GitHub or hosting authority.
- Trust CI already verifies a PR exact head in an isolated checkout, runs holdout
  policy, and publishes an App-owned Check Run. Its webhook accepts only
  `pull_request` events (`trust-ci/.../webhooks.py:22-66`); its App token asks for
  `checks:write`, `contents:read`, `pull_requests:read`, and its GitHub client only
  creates/updates checks and branch protection. It cannot read issues, push a
  branch, create a PR, merge, or record a partner decision.

Missing, therefore required in the later route:

1. A GitHub issue-source adapter that captures repository, issue ID/version,
   author/trust classification, body digest, exact default-branch SHA and
   acceptance criteria. Web content is untrusted data. Current `/v1/tasks` is
   generic authenticated local intake, not webhook issue ingestion.
2. An execution-eligible Codex worker that invokes the model and speaks the M5
   event/proposal protocol. Existing Codex/Grok adapters only translate fixtures.
3. A real isolated workspace/Git broker: private no-local exact checkout,
   allowlisted writable paths/commands, resource and egress boundary, tests,
   exact diff/result snapshot, cleanup and recovery. `FakeWorkspaceBroker` has
   policy-validation value but `FakeGitBroker` permits only status/diff/show and
   forbids write/fetch/push/PR operations (`workspace.py:297-390`).
4. A validator runner that actually executes repository-specific tests and
   produces M6 evidence. The M6 contracts/stores/adjudicator persist and judge
   supplied evidence; they do not create it.
5. A separately privileged Git publisher/PR adapter. It needs exact current-head
   grants for the named repository/ref and PR resource, push-with-lease/no-force,
   idempotent find-or-create behavior, and a returned PR number/URL/head SHA.
   This capability must be outside the model workspace and cannot be smuggled
   through M7's currently absent external capability.
6. A Trust CI status/currentness reader and human-decision adapter that accept
   only the configured App ID/check name on the exact current PR head, then bind
   merged-accepted or rejected/closed evidence. A new commit invalidates the
   decision chain. The factory must never fabricate a human approval or key.

Thus the lineage is composition-ready at the contract/control level, not at the
external-effect level. The smallest honest next-stage vertical adds those narrow
adapters around M4–M7 and reuses deployed Trust CI unchanged. It stops after the
human accept/reject observation. Hosting starts only afterward under its own
route, exact target/action grants, credentials and rollback proof.

## Exact likely file/test plan

Stage 2:

- add `factory/src/adaptive_factory/landing_codex.py`, packaged prompt and
  facts-only JSON schema;
- minimally extend provider evidence dispositions/profile validation and
  `settings.py`/`server.py` for an explicit private profile, while preserving the
  unavailable default;
- add `factory/tests/test_landing_codex.py`; retain existing fixture-provider
  tests unchanged except additive contract cases.

Stage 3:

- add `factory/src/adaptive_factory/landing_sqlite_store.py` and
  `landing_runtime.py`;
- change `landing_service.py` to use ports and durable commands/claims;
- extend `landing_intake.py` for validated retained-record adoption;
- add explicit runtime/quarantine/artifact/source settings and, only if
  SQLite-only operation is intended, a narrow landing-only entrypoint;
- add `test_landing_sqlite_store.py`, `test_landing_runtime.py`, and focused API,
  intake and server restart/idempotency tests.

Stage 4:

- add delivery publication contracts/store/reversible publisher modules while
  leaving `landing_publisher.py`'s unavailable path intact;
- add deterministic fake-transport and publication-store tests only; keep no
  real transport in product composition.

Critical focused coverage is: exact provider profile/argv and zero hidden retry;
text/image/DOCX plus PDF/audio fail-closed cases; no fourth coordinator attempt;
restart at every durable boundary; ambiguous provider not repeated; submit/cancel
replay/conflict and tenant isolation; stale worker rejection; CAS tamper/missing
artifact rejection; fake stage has no active effect; activation/restore CAS;
after-effect-before-receipt observation; mixed target state needs human. Existing
renderer/artifact/API tests remain the regression set for exact source, protected
paths, 20 members, deterministic ZIP/sidecar, and `live_url: null`.

Do not add PostgreSQL migration `019`, edit frozen landing OpenAPI v1 or published
`v2.0.14` packages, widen renderer write paths, move model/evaluator into one
identity, reuse M9 dry-run classes as a host driver, or add a concrete network
transport. New source modules must be added to repository structure and
architecture inventories.

## Evidence commands

Inspection used `git status --short --branch`, `git rev-parse HEAD HEAD^{tree}`,
`git log`/`git diff --name-status`, scoped `rg`, and line-numbered reads of the
files named above. Local `codex --version`/`codex exec --help` facts were inspected
without invoking a model. No test suite, provider call, workspace build, network
request, database mutation, application-code edit, branch operation, or external
write was performed.
