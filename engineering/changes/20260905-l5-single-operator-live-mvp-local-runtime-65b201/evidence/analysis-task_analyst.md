# Task analysis — L5 single-operator MVP and next-stage proof

## Binding and ruling

This analysis is bound to route `65b2018b786d` and frozen predecessor
`f3f8d7375a153393ffba3906165e8d625e45d4a1`, tree
`a8f8d71a745e69b12f630d73ba11e1cdca262c5e`. The predecessor binds the landing
source to `699010380f4f90a0193a9c22090c35e6aded7d2c`, tree
`f7dbbd80c6e95d2a365109d937f5be76d8fe0bd4`, protects source-owned `index.css`,
and permits generated writes only to `index.html` and `content.css`. The
published `v2.0.14` ZIP remains immutable at
`b03c64e67ac757f7d84abfed407cbd0ace2771afd960c67e24684099b3cc0264`; this
change does not rebuild or replace it.

The authoritative product-stage ruling is **Stage 3/5 — Offline Technical
Preview**. Adding an execution-capable provider, local persistence, and a
reversible fake-host control boundary makes that preview usable by one local
operator, but does not itself advance the product stage and must not be called
Shapiro L5. The next-stage Definition of Done is one real, evidence-bound
design-partner loop in a separate disposable/test repository. Publishing a
landing through cPanel/HTTPS is downstream product materialization and is not a
substitute for that software-production loop.

## User-observable result

For the repository-local MVP, one authenticated operator submits a bounded
`text/plain`, supported image, or safe DOCX body to the existing landing API,
polls the same job after a process restart, and receives either:

- `artifact_ready` plus the digest of a deterministic private ZIP/sidecar bound
  to the exact landing source, input, provider profile, candidate, evaluation,
  and at most three attempts; or
- a stable fail-closed terminal state and reason, with no fallback, target
  mutation, or repeated ambiguous provider call.

The default server composition still returns `provider_unavailable`, and the
v1 result still has `live_url: null`. Fake publication evidence may show
`prepared -> staged -> activated/observed -> restored`, but it never proves a
network call or public deployment.

For the separate next-stage proof, the observable result is stronger: a real
design-partner issue in another repository becomes an automatically opened PR
whose exact head contains model-authored code, passes that repository's tests,
semantic gate, and App-owned exact-SHA Trust CI check, and is then accepted or
rejected by the human partner. Humans may supply the issue and final decision;
they do not write or repair the candidate code.

## MVP acceptance criteria

### AC-01 — Frozen identities and zero ungranted effect

- The predecessor source tuple, two-path renderer write set, 20-member deploy
  inventory, migrations `001`-`018`, frozen non-deployed landing OpenAPI v1,
  and both tracked `v2.0.14` package files remain byte-identical.
- No test or default composition invokes an external model, network, GitHub, or
  hosting transport. No request field can select an executable, model, source
  repository, source SHA/tree, output path, host, credential, or transport.

### AC-02 — Execution-capable exact Codex provider, disabled by default

- Trusted local configuration can select exactly one Codex CLI profile bound to
  the absolute regular executable, executable SHA-256, adapter/model identity,
  fixed argv, prompt/tool/schema/decoder digests, timeout, and output ceilings.
  Invocation uses no shell, no inherited credential environment, bounded
  stdin/stdout/stderr, and kills the complete child process group on timeout.
- Offline conformance uses a deterministic fake executable; this route does not
  make a live Codex call. Missing configuration, executable drift, malformed or
  oversized output, timeout, unsupported media, or profile mismatch terminates
  as `provider_unavailable`, `rejected`, or `needs_human` with no alternate
  provider and no second attempt hidden inside the adapter.
- Primary MVP normalization succeeds for strict UTF-8 text, at least one
  allowlisted image shape used by the dogfood fixture, and a DOCX whose bounded
  OOXML extraction follows no external relationship, macro, embedded package,
  traversal path, or active content. Extracted text and image content remain
  untrusted input and cannot alter system/tool policy.
- PDF and voice/audio are capability-declared. If no reviewed bounded extractor
  exists, they fail closed before Codex invocation. Their failure is acceptable
  for this MVP and must not be disguised as successful normalization.

### AC-03 — Existing generation/evaluation boundary is really composed

- A valid provider result round-trips through `StaticLandingSpecV1`, then the
  existing exact-source workspace, renderer, independent evaluator, and
  artifact packager. The writer cannot be its own evaluator.
- One initial candidate plus no more than two evidence-directed repairs are
  persisted. There is no fourth provider, writer, or evaluator invocation.
- Success requires the exact source/candidate SHA and tree, exactly the allowed
  generated paths, a passing bound evaluation, and byte-validated ZIP,
  sidecar, manifest, and `SiteArtifactV1`. Any binding mismatch produces no
  `artifact_ready` result.

### AC-04 — Restart-safe single-operator runtime

- Local state lives under one explicitly configured absolute, owned, non-link
  runtime root outside the repository. SQLite and private artifact/input files
  are created under restrictive permissions; SQLite enables foreign keys,
  bounded busy handling, WAL, and full synchronization or startup fails.
- Submit and cancel idempotency survive process recreation. Same key plus same
  canonical request returns the same result with zero provider/workspace calls;
  changed material returns `409 idempotency_conflict`. Every lookup and mutation
  is bound to the complete tenant/repository/job identity.
- A committed normalization result is durable before raw input purge. After an
  uncertain crash during a real provider call, restart records
  `needs_human/provider_outcome_ambiguous` and does not call the provider again.
  Interrupted purely local generation/evaluation may also fail closed for this
  MVP rather than claim resumability.
- Artifact bytes are fsynced and revalidated before the database can expose
  `artifact_ready`. Restart retains exact committed results; missing, changed,
  cross-tenant, or conflicting bytes fail closed and are never silently rebuilt
  or overwritten. A stale pre-cancel worker cannot commit.
- Recovery scans are finite. No background retry loop or automatic retry of a
  terminal/ambiguous job is introduced.

### AC-05 — Reversible publication logic proved only through fake transport

- The product ships a transport port and deterministic fake transport, not a
  concrete network/cPanel implementation and not default server composition.
- `prepare` validates the complete artifact before transport and binds an exact
  restorable baseline. `stage` leaves active bytes unchanged. `activate` uses a
  compare-and-swap against that baseline. `observe` accepts only the exact
  candidate. `restore` accepts only the bound candidate/baseline pair.
- Same command replay makes zero additional transport calls. Crash after effect
  but before receipt is reconciled by observation, not blind repetition.
  Changed/mixed/unknown active state becomes `needs_human` without overwrite or
  deletion. The fake proves control semantics only, not real-host capability.

## Four sequential handoffs

| Handoff | Input | Required output and finite gate |
| --- | --- | --- |
| **H1 — frozen source -> operational provider boundary** | Exact `f3f8d737...` predecessor and existing `LandingProvider` contracts | Execution-capable, trusted-config-only Codex adapter/profile; offline fake-executable conformance; text/image/DOCX primary cases pass; PDF/audio explicitly supported or fail closed. Default remains unavailable. Stop on unpinnable executable/protocol, unsafe extraction, inherited authority, or silent fallback. |
| **H2 — provider -> durable local runtime** | Typed `StaticLandingSpecV1` plus bound `LandingProviderEvidenceV1` | One-process SQLite state, durable idempotency and cancellation, persisted stage evidence, private retained input/CAS, exact coordinator/packager bridge, deterministic artifact result after restart. Stop on duplicate ambiguous provider calls, tenant escape, stale-worker commit, lost committed state, or artifact corruption. |
| **H3 — runtime artifact -> fake reversible host adapter** | Verified artifact digest and private bundle | Durable publication intent plus fake transport evidence for validate, baseline, stage, CAS activation, observation, reconciliation, and exact restore. No socket/network implementation. Stop if staging can alter active state, replay repeats a mutation, unknown live bytes are overwritten, or exact restore cannot be proved. |
| **H4 — local preview -> separate exact-grant design-partner dogfood** | Exact reviewed/merged source, operational provider configuration, and a separately approved external disposable/test repository | One issue -> real Codex or Claude -> isolated workspace/branch -> model-authored change -> focused tests and semantic gate -> automatically created PR -> App-owned Trust CI SUCCESS on the exact up-to-date head -> human accept/reject. Use a bounded repair ceiling of three candidate attempts. This is a separate route and external action; no current local receipt or landing-host grant authorizes it. |

H4 additionally requires an installed/configured GitHub App and deployed Trust
CI repository policy for the design-partner repository; the current repository's
check cannot be presumed portable. It also requires exact current-SHA grants for
model data transfer, branch push and PR creation, plus separately supplied
credential handles. Any later cPanel stage/activate/restore needs its own exact
target/action grants, hosting credential handle, current-site snapshot, and
rollback identity, but is not part of the next-stage DoD.

## Critical blocking cases versus deferred work

Only these findings reopen the MVP after its final review wave:

1. a primary text, image, or safe-DOCX core flow cannot reach a correctly bound
   artifact in offline conformance;
2. provider/process/path/model/transport authority can be caller-selected,
   credentials leak, or a default/network/external effect becomes reachable;
3. tenant/repository isolation, idempotency, cancellation fencing, or the
   three-attempt ceiling can be bypassed;
4. a restart loses committed state, repeats an ambiguous model call, exposes an
   uncommitted/tampered artifact, or corrupts immutable evidence;
5. fake activation can overwrite a changed baseline, or exact restore/reconcile
   is not demonstrably safe.

Deferred, non-blocking optimization includes voice transcription; safe PDF
extraction when not available; richer OCR/layout quality; additional provider
or model adapters; automatic fallback; multi-host workers, distributed leases,
queues, HA, load/soak tuning, large-cohort metrics, retention automation,
online backup orchestration, and a real cPanel/FTP/SFTP transport. UI polish,
DNS/TLS/WAF changes, public indexing, and production cost optimization are also
downstream. A deferred item becomes blocking only if shipped behavior claims it
or its absence creates one of the critical failures above.

## Evidence ceiling and stop conditions

- During implementation, run only the focused test file/case affected by the
  current handoff. After a failure, rerun that failed/affected scope only when a
  source change requires it; do not restart unrelated passing groups.
- Freeze every tracked source, contract, state, and evidence-template change
  before the expensive gate. Then run exactly one final
  `python3 scripts/grok_verify.py --mode pr` and one parallel wave of the four
  route-selected code/test/security/data reviews. A source repair after that
  invalidates the evidence and permits one affected repair/reverification cycle;
  review nits go to backlog rather than expanding acceptance.
- This route stops locally after H3 is exact-head verified, reviewed, and has
  zero evidence gaps. It neither waits for nor performs H4. H4 stops on a real
  exact-head Trust CI failure, missing external repository policy, absent exact
  grant/credential, attempt three without a passing candidate, or the partner's
  accept/reject decision; it does not loop indefinitely.
- Stale PR #21 is superseded history and should be closed in a separate,
  explicitly authorized external operation. Its closure neither blocks nor
  proves this route.
