# AI/security architecture analysis — L5 Landing Dogfood

Route: `9f67efd2575c`
Inspected HEAD: `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`
Inspected tree: `878fd39838d43131b05dfa5e553be11260237342`
Scope: read-only AI/provider/security analysis. No provider call, broad test,
deployment, network operation, secret access, or product edit was performed.

## Ruling

The smallest safe vertical is an additive landing pipeline that reuses M5's
provider-independent execution contracts and disposable workspace, M6's
independent semantic verdict/repair boundary, M0 exact-SHA Trust CI, and M9's
signed-artifact/delivery records. It needs no new framework, service, queue,
database, provider SDK, or migration.

Repository source must contain only two normalization implementations:

1. a sealed deterministic fixture broker for contract tests; and
2. an `UnavailableLandingNormalizer` that returns the closed
   `provider_unavailable` disposition without reading a credential or making a
   network call.

This is not merely a placeholder limitation. Both current native adapters are
offline conformance adapters: Codex and Grok declare
`execution_eligible=False`, and Grok is not fixture-conformant. An operational
normalizer may later be injected at the composition root only with a complete
pinned profile and separately authorized data transfer. Until then, neither a
live AI run nor generated production content may be claimed.

The domain is known to be indexed from supplied/public observations, but its
current origin bytes, route inventory, and rollback manifest are absent from the
accessible source snapshot. Consequently L5 may generate and attest an isolated
candidate, but cannot claim that it preserves the indexed site, materialize it,
or return a verified live URL. The fail-closed result is
`awaiting_current_site_snapshot`, not a fabricated production success.

## Existing boundaries to compose, not replace

- `ExecutionSelectionV1`, `ProviderProfileV1`, `AuthorityBindingV1`,
  `TaskPacketV1`, and `AdapterRegistry` already bind provider/adapter bytes,
  prompt/tool/output-schema digests, exact SHAs, and capabilities.
- `CapabilityPolicyV1` already rejects network destinations. The landing writer
  should use it with only its isolated candidate `index.html` and `styles.css`
  paths writable; the normalization model and evaluator have no application or
  Git write authority at all.
- `WorkspaceResultV1` and `ArtifactAttestationV1` already make the trusted
  workspace broker, rather than model output, authoritative for result bytes.
- `ValidatorIdentityV1` already rejects the original writer and a reused writer
  context. `SemanticVerdictV1` and the deterministic M6 adjudicator already
  provide closed `pass | repair | needs_human` results and escalate
  contradiction, unsupported pass, security-boundary, and authority findings.
- M6 permits repair cycles `1..3` globally. L5 deliberately applies the narrower
  **three total candidate attempts** rule: initial attempt 1 and at most two
  repair attempts. It does not change the M6 contract or use M6 cycle 3.
- `SignedArtifactRefV1` and M9's sealed in-memory environment remain the delivery
  seam. They do not grant provider, signing, hosting, DNS, TLS, or production
  authority.

## Minimal closed contracts

All objects are version 1, reject unknown/missing fields and duplicate JSON keys,
use immutable ordered collections, and carry a domain-separated canonical digest.

### `LandingInputV1`

Required fields: `schema_version`, `job_id`, `tenant_id`, `repository_id`, fixed
`site_id`, `media_kind`, exact `media_type`, `byte_length`, `content_sha256`,
`quarantine_ref_digest`, `received_at`, `expires_at`, and `input_digest`.

`media_kind` is exactly `text | audio | image | pdf | docx`. The API accepts one
raw body, never a remote URL, caller filesystem path, multipart filename, archive,
or caller-selected storage location. Every lookup and deletion is bound again to
`tenant_id + repository_id + job_id + input_digest`; an opaque blob handle alone
is never authority.

### `PinnedLandingModelV1`

Compose the existing exact `ExecutionSelectionV1` and add only provenance that it
does not currently express: `model_revision`, `model_digest`,
`normalizer_contract_digest`, `decoder_id`, `decoder_version`, `decoder_digest`,
and `sampling_parameters_digest`. It also binds the existing adapter/native,
prompt-template, role-definition, tool-policy, and output-schema digests.

There is exactly one configured profile digest per job. The caller cannot select
or override any field. A missing revision/digest, registry mismatch, unavailable
profile, capability mismatch, or provider fallback request yields
`provider_unavailable`/`needs_human` before source bytes are disclosed. Low
temperature or a seed may be pinned when supported, but reproducibility is
represented by recorded output digests; the contract must not pretend model
generation itself is deterministic.

### `StaticLandingSpecV1`

This is the sole accepted model output. It contains only:

- fixed `site_id`, fixed HTTPS origin, locale and text direction;
- bounded SEO title/description and a closed robots/canonical policy;
- an ordered, bounded list of section records whose `kind` is from a local enum;
- bounded plain-text headings, paragraphs, list items, CTA label and local path;
- local content-addressed asset references with media type, alt text,
  `sha256`, and rights/provenance reference;
- source-backed claim references; and
- `spec_digest`.

It cannot contain HTML, CSS, JavaScript, templates, commands, prompts, tools,
event handlers, forms, analytics, arbitrary origins, `javascript:`/`data:` URLs,
deployment instructions, credentials, or authority claims. Unsupported factual
marketing claims and assets without a provenance/right reference are omitted or
produce `needs_human`; they are never invented. A trusted deterministic renderer,
not the model, context-encodes the closed values into static HTML/CSS.

### `LandingNormalizationEvidenceV1`

Bind `input_digest`, `profile_digest`, `spec_digest`, exact provider-call ID,
request/response digests, usage counters, price-table digest, start/end times,
and a closed disposition. The provider-call ID is an opaque bounded identifier,
not a URL or credential. Raw prompts, native event streams, reasoning, OCR text,
transcripts, source bytes, and provider responses are forbidden durable fields.

Normalization is one call for one immutable input digest. Parse/schema or policy
failure is terminal `rejected`; it is not retried with a looser prompt or another
model.

### `LandingAttemptV1`

Bind ordinal `1..3`, the same `input_digest`, `spec_digest`, `profile_digest`,
exact base/head SHA, M5 task/run/fence/packet/workspace-result digests, writer ID,
fresh `context_digest`, prior-attempt digest, evaluator-envelope digest, outcome,
usage, and times. The append-only ordinal plus prior digest is authoritative; no
mutable "best result" pointer and no provider-selected winner exists.

### `EvaluatorHintEnvelopeV1` and verified projection

The hidden evaluator returns a signed envelope bounded to 16 KiB with:
`schema_version`, fixed issuer/verifier/key IDs, fixed algorithm, repository and
tenant IDs, exact candidate head SHA, attempt ordinal/digest, spec/profile/policy/
holdout digests, `pass | repair | needs_human`, sorted closed reason codes (at
most 32), sorted requirement/finding digests (at most 32 each), issue/expiry
times, payload digest, and signature.

The trusted verifier obtains public keys from the existing external trust store,
checks signature, validity window, exact subject and policy bindings, and emits a
small `VerifiedEvaluatorHintsV1` projection. The writer sees only allowlisted
reason codes, requirement references, finding digests, and the signed-envelope
digest—never hidden fixture bytes, natural-language instructions, URLs, code, or
signature material. Signed data is still data: it cannot change system policy,
select tools/models, widen paths/network, or grant authority. Invalid, stale,
oversize, contradictory, or mismatched hints yield `needs_human` with zero write.
Only the full App-owned exact-SHA Trust CI attestation can select a delivery
candidate; a hint or local receipt cannot substitute for it.

## Bounded media and retention policy

These limits are deliberately small enough for the MVP and separate binary
intake from the existing 1 MiB JSON/event protocols.

| Kind | Accepted types | Hard input/shape limit |
| --- | --- | --- |
| text | UTF-8 `text/plain` | 1 MiB and 200,000 Unicode scalar values |
| audio | WAV, MP3, Ogg | 25 MiB and 15 minutes |
| image | PNG, JPEG, WebP | 10 MiB and 40 megapixels |
| PDF | `application/pdf` | 20 MiB and 100 pages; encrypted PDFs rejected |
| DOCX | non-macro OOXML DOCX | 10 MiB compressed, 50 MiB expanded, 2,000 ZIP entries |

Declared media type, magic bytes, and bounded structure must agree before a
normalizer is invoked. Active/macro content, external relationships, embedded
packages, symlinks, path traversal, archive recursion, and decompression-limit
violations are rejected. The normalized model response is at most 256 KiB; the
canonical spec is at most 128 KiB; extracted text/facts are at most 1 MiB.

Raw accepted bytes live tenant-namespaced with mode `0600`, outside Git and the
writer workspace, for at most 24 hours. They are purged immediately after a
terminal normalization outcome or cancellation. Partial/rejected uploads are not
retained. OCR/transcripts, normalized extracts, request bodies, and native model
responses are transient only and are destroyed when the call ends. Durable state
contains the closed public-candidate spec, counters, provenance, and digests—not
the raw input. Existing evidence-retention policy governs those records; L5 must
not silently introduce an independent long-term content store.

## Deterministic identity rules

- `content_sha256` is SHA-256 over the exact received bytes before decoding.
- Structured digests reuse repository canonical JSON: UTF-8, NFC strings, sorted
  object keys, no duplicate keys/non-finite numbers, and explicitly ordered or
  sorted-unique arrays as declared by the schema. Each digest is prefixed with a
  contract domain and version plus a NUL byte.
- Text extraction normalizes CRLF/CR to LF and NFC; PDF/DOCX elements use stable
  document order; media facts use schema-defined order. Extraction/decoder bytes
  and versions are part of the pinned profile.
- Each model request and response is hashed exactly. Attempt output digests prove
  what occurred; equal inputs do not imply equal model output.
- Evaluator signatures cover the canonical envelope payload digest. Artifact and
  deployment evidence continue to use their existing exact-SHA/digest bindings.

## Executable flow and prompt-injection containment

1. The authenticated API authorizes tenant and repository, streams the body into
   the bounded quarantine broker, verifies type/shape, hashes bytes, and closes
   `LandingInputV1`. Binary bytes never enter JSON/events or a Git workspace.
2. The control plane resolves the exact pinned model profile from trusted runtime
   configuration. The default unavailable broker stops here without a live
   provider; the sealed fixture broker can exercise the remaining local flow.
3. An operational normalization port, when separately supplied, gets a read-only
   one-job source handle and deadline. It has no tools, workspace, repository,
   network-destination list, secrets in context, or application write capability;
   its only output is bounded JSON for `StaticLandingSpecV1`.
4. Every text fragment, OCR result, transcript, image/PDF/DOCX metadata, embedded
   instruction, link, and evaluator value is labelled untrusted source data.
   System/tool policy is fixed outside that data. Injection containment relies on
   absence of tools/authority plus strict output validation—not on asking the
   model to ignore instructions. Unknown fields, unsafe URLs, active content, or
   policy-shaped output are rejected wholesale.
5. A trusted renderer gives the closed spec to an M5 writer packet in a fresh
   disposable exact-base workspace with network empty and only the two candidate
   files writable. The checked-in showcase and live site are not overwritten.
6. A separate read-only evaluator identity assesses the exact resulting SHA. A
   repair verdict may create the next ordinal only after signature/binding checks.
   Each attempt has a context digest distinct from every previous writer and
   evaluator context and contains only the immutable spec plus the immediately
   preceding verified hint projection—no accumulated chat or hidden evidence.
7. Attempt 1 may pass or request repair; attempts 2 and 3 use fresh contexts. Any
   contradiction, security/authority issue, repeated finding, non-repairable
   result, stale binding, or a non-pass at attempt 3 becomes `needs_human`. An
   ordinal 4 invocation is unrepresentable and must not reach a provider.
8. Only a selected exact SHA may proceed through existing Trust CI and immutable
   artifact construction. Production materialization remains unreachable until a
   current-site snapshot/manifest, matching previous signed artifact, operational
   provider/environment, exercised recovery, exact external authority, and HTTPS
   observation all exist.

## Minimal P0 verification slice

The implementation owner should add focused contract tests, not an exploratory
edge-case campaign:

- one valid offline fixture per five media kinds plus type/magic and hard-limit
  rejection;
- deterministic digest round-trip and strict unknown/duplicate-field rejection;
- a hostile source that asks for tools, secrets, external URLs and policy changes
  remains inert and cannot escape `StaticLandingSpecV1`;
- absent/mismatched provider profile performs no call and returns the closed
  unavailable state with no fallback;
- cross-tenant blob/job access and raw/native content persistence are denied;
- invalid/stale evaluator signature is denied, evaluator is not the writer, and
  only the bounded verified projection reaches repair;
- attempts are exactly ordinals 1–3 with unique contexts; a fourth call and
  non-pass after attempt 3 produce `needs_human`;
- generated output is confined to the disposable allowlist, with no network or
  application write authority; and
- missing current-site snapshot prevents materialization/live-result claims.

## True blockers and non-goals

No AI design uncertainty blocks the local vertical. The true unavailable inputs
are an execution-eligible pinned provider/normalizer, authorization to send the
selected tenant data to it, the current production-site snapshot and rollback
manifest, real evaluator/Trust CI signed evidence for the candidate, a signed
artifact, operational materializer/recovery proof, and explicit production
authority. These are runtime/operational prerequisites, not reasons to fabricate
adapters, secrets, indexed routes, or live evidence in repository source.

This report does not approve the route's named `scope_and_design_approval` gate
and does not authorize push, PR, merge, tag, release, signing, provider access,
deployment, DNS/TLS mutation, or any external write.
