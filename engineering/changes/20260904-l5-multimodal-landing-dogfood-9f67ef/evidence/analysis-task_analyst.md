# Task analysis — L5 multimodal landing dogfood

Route: `9f67efd2575c`
Inspected source: `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`
Inspected tree: `878fd39838d43131b05dfa5e553be11260237342`

## Ruling

This tree contains useful control, validation, trust, artifact, and static-landing
building blocks, but it does not contain an executable path from a text/audio/image/
PDF/DOCX request to a generated landing or to
`https://therealaidarkfactory.online/`. It must not be described as operational L5.

The minimum coherent feature is one authenticated, one-input/one-output dogfood
vertical: one untrusted input is normalized once into one closed landing spec; a
writer produces at most three exact-SHA candidates in disposable workspaces; an
independent evaluator alone selects the candidate; Trust CI attests the selected PR
head; and an external materializer may activate the exact immutable artifact only
after the live site has a trusted baseline and the separately required authority.
The user supplies intent, but does not author or review generated source.

The supplied SERP evidence establishes that the existing domain is indexed, including
a homepage and a roadmap result. It does not bind those live bytes to this repository.
The live source, release manifest, document-root inventory, redirect configuration,
and rollback pointer are currently unavailable. Consequently the locally achievable
result is an exact, immutable candidate artifact plus a deployment plan; a truthful
`live` result is blocked until the production prerequisites below exist.

## Implemented components versus missing executable glue

| Stage | Implemented on the inspected tree | Missing for this route |
| --- | --- | --- |
| Static landing baseline | The framework-free showcase, SEO rules, and responsive browser contract exist under `side-projects/seo-landing-showcase/` and `.agents/skills/seo-landing/`. | The showcase is explicitly `noindex`, has no production canonical/sitemap, and is not proven to be the live site's source. It is a reference/regression fixture, not a deployable replacement. |
| Authenticated API conventions | Factory bearer authorization, repository scoping, idempotency/correlation headers, bounded errors, and a 1 MiB streamed body ceiling exist (`factory/src/adaptive_factory/api.py:38,57-86,348-395`). | No multimodal endpoint, media contract, MIME/magic validation, quarantine store, retention/purge flow, or landing job/result API exists. |
| Typed normalization | Canonical JSON/digest helpers and closed change/execution/semantic contracts exist. | There is no speech transcription, OCR, image interpretation, PDF/DOCX extraction, pinned normalization pipeline, `LandingSpecV1`, prompt/model evidence, or live normalization broker. `grok_spec generate` only emits an empty engineering template with `UNKNOWN` fields (`.grok-stack/adaptive_grok/spec.py:803-824`). |
| Durable orchestration | M4 provides immutable intake, leases, fences, budgets, retries, events, and reconciliation; M5 provides task packets/manifests and execution APIs (`factory/src/adaptive_factory/api.py:417-439,529-620`). | No landing coordinator maps normalized input to those contracts, no durable landing job projection exists, and no shipped worker consumes an execution claim. |
| Provider execution | Provider-neutral protocols and fixture translators exist. | Codex and Grok adapters translate already-produced bytes only and are explicitly execution-ineligible (`factory/src/adaptive_factory/adapters/codex.py:6-17`, `grok.py:6-17`). No pinned provider invocation, credential broker, or rootless launcher exists. Enabling execution through the shipped server fails without injected registry/artifact/snapshot dependencies (`factory/src/adaptive_factory/server.py:123-138,195-207`). |
| Workspace and source mutation | M5 defines workspace policies, snapshots, artifact requests, and host-isolation readiness facts. | The shipped workspace/Git implementations are fakes: network and `.git` access are denied, Git mutation/external operations are rejected, and snapshots are unavailable (`factory/src/adaptive_factory/workspace.py:297-400`). No real disposable clone, bounded HTML/CSS writer, commit, branch, or PR updater exists. |
| Bounded repair | M6 validates semantic evidence and can derive exact repair directives/child bindings for bounded cycles (`factory/src/adaptive_factory/service.py:326-374`, `semantic_repair.py:414-486`). | No coordinator invokes the evaluator, consumes its finding, creates the next executable child, or enforces one cumulative landing-attempt counter across execution/infrastructure retry paths. |
| Independent hidden evaluation | Trust CI checks an exact PR head in a read-only/no-network container, mounts its holdout outside the checkout, rejects source mutation, signs the result, and publishes an App-owned check (`trust-ci/src/adaptive_trust_ci/sandbox.py:18-103`, `runner.py:414-520`). | Trust CI starts only after a PR exists. Factory has no PR delivery path or callback/poller that turns a non-PASS result into a bounded repair directive. Its public job projection intentionally exposes command identity/status/digest rather than actionable hidden fixture bytes (`trust-ci/src/adaptive_trust_ci/api.py:201-228`). |
| Artifact and delivery | M5 has artifact-attestation shapes; M9 has closed signed-artifact/delivery/recovery value objects and an evidence chain. | Shipped attestation is unavailable in the fake workspace. M9 accepts only its sealed in-memory fake, whose environments are nonproduction; production is structurally unreachable (`delivery/src/adaptive_delivery/fake_environment.py:29-89`, `controller.py:43-62,257-272`). No landing archive builder, signer/verifier, release store, HTTPS materializer, or durable recovery adapter exists. |
| External delivery | The App-owned exact-SHA merge check exists, and prepare-only release tooling records the required boundary. | No component creates/updates the PR, merges, publishes a release, writes Namecheap hosting, switches a release pointer, or observes the resulting HTTPS bytes. Those are external actions and are not authorized by this analysis. |

M7/M8 human-review/cohort contracts are not an implementation shortcut for this
feature, and the name `L5 Landing Dogfood` must not be added to their closed
`L0`/`L1`/`L2` model. The current M9 fake should remain unchanged; a real
materializer belongs behind a new injected port.

## Bounded v1 product definition

- Exactly one request body, not multipart and not a caller-supplied URL/path.
- Exactly five accepted media families: strict UTF-8 text, bounded audio, PNG/JPEG/
  WebP image, non-encrypted PDF, and non-macro DOCX. Keep the first dogfood payload
  within the existing 1 MiB API ceiling rather than weakening the control API.
- Treat file content, metadata, OCR text, transcripts, hyperlinks, and embedded
  instructions as untrusted data. Reject MIME/signature disagreement, active or
  encrypted documents, expansion bombs, malformed containers, unsafe relationships,
  excessive dimensions/pages/duration, and cross-tenant replay.
- Normalize once into `LandingSpecV1`. It contains bounded semantic fields and local
  asset references; it cannot contain HTML, CSS, JavaScript, shell commands, tool or
  policy instructions, credentials, arbitrary origins, analytics, forms, or authority.
- Generate one static landing using HTML and CSS only. Image input is a design/content
  reference unless an independently sanitized, content-addressed local asset is
  explicitly admitted; it is never copied to output implicitly.
- Initial generation plus at most two repair generations gives the absolute ceiling of
  three writer invocations. Set infrastructure retries to zero and semantic repairs to
  two; also enforce `attempt_ordinal <= 3` in the L5 coordinator so two independent
  retry mechanisms cannot multiply calls.
- Attempt three without independent PASS is terminal failure with no artifact or
  deployment. Human intervention is not a successful L5 runtime path.
- The fixed site is `therealaidarkfactory.online`; no request may choose another
  repository, origin, credential, release namespace, or deployment path.

## Required vertical flow

```text
authenticated raw bytes
  -> private quarantined digest reference
  -> pinned extraction/transcription/vision pipeline
  -> closed LandingSpecV1 + normalization evidence
  -> M4 intake / M5 writer claim
  -> disposable exact-base workspace
  -> candidate SHA + trusted diff/snapshot
  -> independent hidden verdict
  -> repair child or selected SHA (maximum three candidates)
  -> internal PR head
  -> exact-head Trust CI signed PASS
  -> protected merge with selected-subtree identity check
  -> deterministic landing archive + manifest/provenance
  -> separately authorized compare-and-swap materialization
  -> TLS-verified observation
  -> live URL + signed evidence
```

The writer must receive only the closed spec and bounded repair findings. It must not
receive raw uploads, evaluator fixtures, provider/deployment credentials, `.git`
authority, network authority, or artifact-signing authority. Git derivation, PR
delivery, signing, and materialization are separate trusted adapters.

## Contract and implementation seams

The smallest source layout is additive:

- `factory/contracts/openapi/landing-dogfood.v1.json` for submit/status/cancel/result;
- closed schemas for `LandingInputV1`, `LandingSpecV1`, `NormalizationEvidenceV1`,
  `LandingAttemptV1`, evaluator verdict, and `LandingResultV1`;
- `factory/src/adaptive_factory/landing_contracts.py` for canonical values/digests;
- `landing_intake.py` for raw-body validation and a private `LandingBlobStore` port;
- `landing_normalization.py` for pinned extractor/ASR/vision/normalizer ports;
- `landing_coordinator.py` for M4/M5 projection and the single three-attempt loop;
- `landing_artifact.py` for deterministic HTML/CSS manifest construction;
- `delivery/src/adaptive_delivery/landing_materializer.py` for a sealed local fake and
  an operational adapter protocol, without widening the existing M9 fake;
- focused contract, hostile-input, replay, isolation, evaluator, artifact, browser,
  and rollback tests.

An asynchronous job spanning model execution and Trust CI must survive restarts.
Either its immutable records must be mapped losslessly onto existing M4-M6 storage,
or a new additive migration must be explicitly approved. An in-memory landing store
is sufficient for tests only and cannot support an operational/L5 claim.

Preserve `side-projects/seo-landing-showcase/` byte-for-byte as the reference fixture.
Generate the selected domain artifact under a separate add-only source/release path,
for example `side-projects/seo-landings/therealaidarkfactory.online/`. This resolves
the analysis conflict safely: the showcase remains a regression oracle, while the
domain-specific manifest makes ownership explicit. No stale feature branch should be
cherry-picked; the reusable source is already on `ad6d23c`.

## Finite acceptance proof

1. Each of the five valid media fixtures reaches the same canonical spec when it
   carries equivalent intent; hostile or ambiguous inputs fail closed without a
   provider/tool/policy override.
2. Raw bytes have short bounded retention, are tenant-separated and mode-private, and
   never occur in task packets, Git, durable logs, responses, metrics, or evidence.
3. Exact provider/model/native/prompt/role/tool/output-schema/decoder identities are
   recorded; any drift or fallback rejects the job.
4. The writer can change only the allowlisted landing files in a fresh exact-base
   workspace, without network, secrets, `.git`, symlink escape, or hidden-test access.
5. One seeded candidate exercises a repairable hidden failure and a later attempt
   passes; replay/concurrency cannot duplicate an ordinal, and a fourth invocation is
   impossible.
6. The evaluator identity and context are distinct from the writer, recomputes its
   verdict, and alone selects the candidate. The writer receives bounded reason codes,
   not hidden fixture content.
7. Public HTML/CSS checks and the existing 320/768/1280/1920 keyboard/focus/reduced-
   motion browser contract pass for the selected candidate.
8. Only a signed Trust CI PASS matching repository, PR, base/head SHA, policy epoch,
   spec coverage, and required approval scopes can cross the merge boundary.
9. Two artifact builds from the same selected merged tree are byte-identical. The
   manifest binds every owned path, mode and digest and is distinct from the published
   product `v2.0.13` ZIP.
10. Activation never overwrites an active directory. It stages by digest, rechecks the
    live inventory, atomically switches one release pointer, verifies the exact HTTPS
    release digest, and restores the previous pointer on any failed probe.
11. The result API returns the canonical live URL only after successful observation,
    together with checked head, merged SHA, artifact digest, Trust CI attestation,
    materialization receipt, and observation digests; it exposes no secrets.
12. A source/policy/holdout/base/head/spec/authority change invalidates downstream
    evidence. Failure, cancellation, or attempt exhaustion leaves the current live
    site unchanged.

## Blocking prerequisites and scope-gate decisions

1. **Live-source preservation is unresolved.** Before materialization, obtain an
   authorized read-only snapshot of the current homepage, roadmap URL/content,
   document root, redirects, headers, robots/sitemap, WAF/CDN behavior, and a sorted
   path/size/MIME/SHA-256 inventory. Public visibility and SERP evidence do not grant
   overwrite authority.
2. **Atomic deployment is unproven.** The observed Namecheap path has no established
   versioned-release/atomic-pointer primitive. In-place FTP or file-manager overwrite
   is not acceptable. Until compare-and-swap plus previous-release rollback is proven,
   the route can stop only at an immutable local artifact.
3. **Executable provider/isolation profiles are absent.** Exact ASR/OCR/document/
   vision/normalizer and writer binaries, models, prompts, images, digests, egress and
   secret scopes must be supplied outside Git and pass conformance before enablement.
4. **PR/Trust-CI repair glue is absent.** A trusted delivery adapter and authenticated
   Trust CI result bridge are required before the hidden evaluator can drive attempts
   two or three. Trust CI policy/holdout code must not be weakened or copied into the
   writer workspace.
5. **Signing and materialization authority are absent.** Repository code, local
   receipts, and generated output cannot mint artifact or production authority.
   Provider, GitHub, signing, and hosting credentials must remain in mutually separate
   runtime boundaries.
6. **Named gate remains open.** Route `9f67efd2575c` requires
   `scope_and_design_approval` before implementation. The decision must freeze the
   v1 limits, storage model, output ownership path, live-baseline procedure, exact
   external resources, and rollback primitive. It does not itself authorize push,
   merge, signing, Namecheap access, DNS/TLS change, or deployment.

For the Shapiro-L5 claim, distinguish a one-time platform/scope authorization from a
per-job human fallback. The latter would disqualify the run as an autonomous proof.
Until the external prerequisites and a permitted no-human-per-job authority model are
explicitly established, report this work as a bounded L5 dogfood candidate, not an
operational L5 system or a live deployment.

No tests, provider calls, Git/network writes, hosting access, or deployment actions
were performed for this analysis.
