# Architecture analysis — L5 multimodal landing dogfood

Route: `9f67efd2575c`
Inspected source: `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`
Inspected tree: `878fd39838d43131b05dfa5e553be11260237342`

## Recommendation

Implement L5 as a narrow additive orchestration layer over the existing factory,
semantic-validation, Trust CI, and delivery contracts. Do not add L5 values to the
closed M4 `TaskStatus`, alter migrations `001`-`018`, modify any existing v1/v2
OpenAPI document, or turn M9's exact in-memory adapter into a production adapter.
`L5 Landing Dogfood` is a feature name, not a new value in M8's closed
`L0`/`L1`/`L2` earned-autonomy model.

The only generated target is the existing static showcase subtree:
`side-projects/seo-landing-showcase/index.html` and `styles.css`. The current site
remains the active rollback artifact until a replacement has passed every gate.
The implementation reuses Python 3.11+, the installed FastAPI boundary, canonical
JSON/digests, M5 task packets and disposable workspaces, M6 independent semantic
validation, the existing Node/Chrome browser contract, M0 Trust CI, and M9 signed
artifact/delivery records. It introduces no framework, queue, database, provider
SDK, or deployment platform.

Two alternatives were rejected. Extending the M4 state graph or frozen control
contract would invalidate predecessor semantics. A standalone upload/generation/
deployment service would duplicate authentication, persistence, isolation, and
authority and would be a new platform. The additive bridge keeps each old contract
byte-compatible and makes the live boundary explicit.

## Runtime flow and trust boundaries

`authenticated upload -> quarantined blob reference -> pinned normalization ->
closed LandingSpecV1 -> M5 writer packet -> exact candidate SHA -> independent
hidden evaluation -> exact-PR-head Trust CI -> merged-SHA immutable artifact ->
human-authorized materializer -> HTTPS observation -> result`

- The upload API accepts bytes, never a URL or filesystem path. The quarantine
  broker verifies declared type against bounded magic/structure checks, stores
  mode-`0600` tenant-namespaced bytes outside Git/workspaces, and exposes only an
  immutable digest reference. Text, audio, image, PDF, and DOCX are data, never
  instructions.
- The normalization broker, not the writer workspace, owns the external model
  boundary. It receives the blob through a read-only port and returns strict JSON.
  Its credential is a runtime file reference and never enters a prompt, task
  packet, environment projection, result, log, or repository file.
- The writer sees only the closed spec. Its M5 `CapabilityPolicyV1` permits writes
  to the two showcase files, declares only the required artifact classes/tools,
  has `network_destinations=()`, and uses a disposable exact-base workspace. A
  trusted Git/workspace broker, never the model, derives the result SHA and diff.
- The evaluator runs read-only against that exact SHA with a different identity,
  role, context digest, and capability set. Hidden fixtures are mounted only in
  the evaluator environment; the writer receives bounded public reason codes or
  an M6 repair directive, never fixture bytes or hidden expected output.
- Local evaluation and route receipts are preflight evidence only. Selection for
  delivery requires the GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>`
  Check Run and its signed attestation on the exact PR head. A merge must then
  preserve the two-file subtree byte-for-byte; otherwise the artifact is refused
  and a new exact-head evaluation is required.
- The HTTPS materializer is outside the worker and outside M9's sealed fake
  adapter. It consumes the final M9 `needs_human` boundary plus a current
  `SignedArtifactRefV1` and separately verified production authority. A route,
  local receipt, agent statement, or local delegated grant cannot substitute for
  Trust CI or a required human-signed approval.

## Closed interfaces

The new checked contract is `factory/contracts/openapi/landing-dogfood.v1.json`;
existing OpenAPI files remain unchanged. It contains four operations:

- `POST /v1/landing-inputs`: one raw bounded body with required bearer,
  `Idempotency-Key`, `X-Correlation-ID`, `X-Repository-ID`, and media type; returns
  `202` plus `LandingJobRefV1`. No multipart filename, remote URL, or caller path is
  accepted.
- `GET /v1/landing-jobs/{job_id}`: tenant-authorized bounded state projection.
- `POST /v1/landing-jobs/{job_id}/cancel`: idempotent cancellation; it cannot erase
  immutable evidence or an already active release.
- `GET /v1/landing-jobs/{job_id}/result`: returns a result only in `live` or
  `rolled_back`; all other states return the closed pending/failure projection.

The handoff records are immutable, closed, versioned, canonically digested, and
tenant-bound:

- `LandingInputV1`: job/repository/site IDs, media kind/type, byte count, SHA-256,
  receive/expiry times, and quarantine reference digest. Allowlisted formats are
  UTF-8 text, WAV/MP3/Ogg audio, PNG/JPEG/WebP image, PDF, and non-macro DOCX.
- `LandingSpecV1`: input digest; fixed site ID; exact canonical HTTPS origin;
  locale/direction; title/description; an ordered bounded set of allowlisted
  section kinds; CTA; local asset references; robots/canonical policy; and spec
  digest. It cannot carry HTML, CSS, JavaScript, commands, tools, prompts, arbitrary
  URLs, analytics, forms, credentials, or authority claims.
- `NormalizationEvidenceV1`: input/spec digests plus exact provider, model,
  adapter/native version, prompt-template, role, tool-policy, output-schema,
  decoder, price-table, usage, and invocation digests. Exactly one normalization
  invocation is permitted per job; invalid output is terminal `rejected`.
- `LandingAttemptV1`: attempt ordinal, M4 task/run/fence, task-packet/workspace-
  result/diff digests, exact base/head SHAs, writer/context identity, evaluator
  decision/evidence digest, usage, times, and prior-attempt digest.
- `LandingResultV1`: site ID, exact HTTPS URL, checked PR head, merged SHA,
  `SignedArtifactRefV1`, Trust CI signed-attestation envelope digest, M9 evidence
  digest, materialization receipt/HTTPS observation digests, previous artifact,
  observed time, and result digest. It contains no token or private-key material.

L5 state is a derived append-only projection and does not change M4 state:

`accepted -> normalizing -> generating -> evaluating -> candidate_passed ->
awaiting_delivery_authority -> awaiting_trust_ci -> awaiting_merge ->
artifact_ready -> awaiting_materialization_authority -> materializing -> live`.

The sole loop is `evaluating -> generating` after an exact `repair` decision while
the next ordinal is at most three. Terminal states are `rejected`, `needs_human`,
`cancelled`, and `rolled_back`. Any digest, tenant, fence, authority, base/head,
or predecessor conflict fails closed to `needs_human`; no caller-supplied state is
trusted.

## Exactly five sequential implementation tasks

### Task 1 — Freeze intake contracts and quarantine boundary

Create the additive OpenAPI/JSON schemas, `landing_contracts.py`, bounded raw-body
router, tenant authorization, and a `LandingBlobStore` protocol with a private
temporary-filesystem test implementation. Reuse the existing bearer actor model
and correlation/idempotency rules; add `landing:submit`, `landing:read`, and
`landing:cancel` scopes without weakening repository checks. Stream with per-kind
and total limits, reject MIME/magic mismatch, active/macro DOCX, encrypted or
expansive archives, malformed PDF/image/audio headers, duplicate-key JSON, path
input, and quota exhaustion; logs contain IDs/digests/counts only.

Handoff: a valid request produces exactly one `LandingInputV1` and job ID; no later
task reads request bytes directly from HTTP. Acceptance: contract/runtime operation
parity passes; all five valid fixture kinds reach `accepted`; spoofing, oversize,
cross-tenant read/cancel, replay-with-different-bytes, and secret/raw-body logging
tests fail closed; cancellation schedules bounded quarantine deletion.

### Task 2 — Normalize every input into one pinned closed spec

Add `LandingNormalizer` and `NormalizationBroker` ports plus offline conformance
fixtures for each media kind. Bind one exact execution profile and all pipeline
digests before reading the blob, call the broker once, parse its bounded output,
and validate `LandingSpecV1` against fixed site/origin and local-asset policies.
Keep OCR/transcription/model implementation and credentials behind the port; do
not add media libraries or provider SDKs. After a successful spec/evidence write,
purge raw bytes according to the short configured retention while retaining only
the input digest and non-sensitive evidence.

Handoff: `LandingSpecV1` plus `NormalizationEvidenceV1`, both bound to the Task 1
input digest. Acceptance: every fixture kind yields the same canonical spec when
its semantic content is equivalent; model/prompt/version drift, unknown fields,
prompt injection attempting tools/policy/URL changes, invented claims, unsafe URL
schemes, and stale/deleted blobs are rejected; no credential or raw input appears
in durable output.

### Task 3 — Generate at most three isolated exact-SHA candidates

Add the L5 coordinator that translates the approved spec into the existing
`TaskIntakeV1`/`TaskPacketV1`, sets a cumulative worker-invocation ceiling of three,
sets automatic infrastructure retries to zero, and permits at most two M6 repair
children after the initial attempt. The same M5 writer identity is retained; each
attempt uses a fresh context and disposable workspace from the same exact base.
Only the two showcase files may change, output artifacts are HTML/CSS, environment
projection excludes credential-shaped names, and network/Git/external actions are
empty. The trusted broker snapshots and releases every workspace even on timeout,
cancellation, budget exhaustion, or worker loss.

Handoff: an append-only chain of one to three `LandingAttemptV1` candidate records,
each with a real exact result SHA; no mutable “best candidate” pointer exists.
Acceptance: the first invocation can produce a candidate, an eligible repair can
produce the next ordinal, a fourth invocation is impossible, concurrent/replayed
claims do not duplicate an ordinal, forbidden-path/network/secret/symlink writes
terminate, and the original checked-in landing remains unchanged outside candidate
workspaces.

### Task 4 — Select one exact SHA independently and seal its artifact

Run public static checks and the existing responsive/reduced-motion/keyboard
browser contract, then submit the exact candidate PR head to the independent Trust
CI evaluator with its external hidden holdout. Treat only a verified signed PASS
attestation whose repository, PR, base/head SHA, policy epoch, spec coverage, and
required scopes all match as selection. A repairable non-PASS may create the next
Task 3 attempt; attempt three without PASS becomes `needs_human`. The writer never
chooses or self-approves a candidate.

After protected merge, a trusted builder verifies that the selected head and
merged commit have identical bytes/modes for the two-site subtree, constructs one
deterministic content-addressed site archive plus sorted manifest/SBOM/provenance,
and obtains the external `signed_artifact_use` authority required to instantiate
the existing `SignedArtifactRefV1`. The artifact is write-once; it is distinct from
and must not restack `packages/adaptive-grok-build-pro-v2.0.13.zip`.

Handoff: one current `SignedArtifactRefV1`, its immutable archive, exact signed
Trust CI envelope digest, and the previous signed artifact. Acceptance: changed or
stale SHA/policy/signature/hidden-evidence/subtree bytes fail; two builds from the
same merged tree are byte-identical; no artifact is produced for a failed or local-
only verdict; the evaluator has no write/provider/deployment capability.

### Task 5 — Materialize reversibly and return verified HTTPS evidence

Add a `LandingMaterializer` port and sealed fake/local release-slot adapter in the
delivery package. It accepts only Task 4's current/previous signed artifacts, the
final nonproduction M9 evidence ending at `needs_human`, fixed site/origin/resource
configuration, and separately verified production authority. The operational
adapter is injected outside repository source. It stages into a digest-named,
non-writable release directory, verifies its manifest, atomically switches one
`current` pointer, and performs a bounded TLS-verified, no-redirect probe against a
fixed `/.well-known/adaptive-release.json`; it never accepts an arbitrary host or
path. Only then does the result endpoint return `https://therealaidarkfactory.online/`
and `LandingResultV1` with the signed Trust CI evidence.

Handoff: `live` or an exact `rolled_back` result. Acceptance: default configuration
and the repository fake cannot reach production; missing/expired/mismatched
authority or inactive M8/M9 evidence has zero external effect; activation serves
the selected digest over HTTPS; a failed probe atomically restores the previous
signed artifact; repeated activation/rollback is idempotent; the prior release is
never overwritten and no secret appears in response, receipt, or logs.

## Configuration and unavailable operational inputs

Repository source may safely fix or configure the five media kinds and byte/shape
limits, site ID and exact origin allowlist, two writable relative paths, input
retention, three-attempt ceiling, public evaluator rules, browser widths, time/
cost/token/output budgets, release-slot layout, probe path/timeouts, and feature
flag (default `false`). Tests use local blobs, fixture normalization, disposable
workspaces, synthetic signed envelopes clearly marked non-authoritative, and the
sealed materializer.

Repository source must not contain a provider endpoint credential, live provider
adapter/profile, hidden holdout bytes, Trust CI/GitHub App key, human approval key,
artifact-signing key, deployment credential, server content root, DNS/TLS key, or
production signer. Activation requires externally supplied exact provider/model/
adapter digests, an execution-eligible rootless isolation profile, the deployed
hidden evaluator and Trust CI policy, real signed artifact authority, factual M8
activation/currentness, M9 operational environment and recovery evidence, domain/
TLS ownership, and explicit production authorization. Until all are present, the
highest truthful state is `awaiting_materialization_authority`, never `live`.

## Recovery and rollback

- Before activation, disable the L5 feature flag, cancel the job, release its
  workspace, and purge the quarantined blob; the current showcase is untouched.
- After a failed materialization or HTTPS observation, atomically restore the exact
  previous signed release and verify its manifest/HTTPS observation before recording
  `rolled_back`. Never edit an active release directory in place.
- A spec, generator, evaluator, or contract defect is forward-fixed through a new
  commit and PR. That change invalidates prior exact-SHA evaluation, Trust CI,
  artifact, and materialization evidence; none may be rebound or reused.
- Loss of provider, evaluator, artifact authority, production authority, or M8/M9
  currentness stops progression without widening access. It does not delete the
  last known-good release.

The route's `scope_and_design_approval` remains a hard gate before Task 1. This
analysis neither approves the design nor authorizes push, PR creation, merge,
artifact signing, deployment, DNS/TLS mutation, or any other external write.
