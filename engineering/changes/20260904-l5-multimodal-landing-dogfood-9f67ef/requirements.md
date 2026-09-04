# Requirements — L5 multimodal landing dogfood

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Functional requirements

1. **REQ-001 — Closed intake.** Accept exactly one raw body of allowlisted text, audio, image, PDF, or DOCX data. Reject caller URLs, filesystem paths, multipart filenames, remote includes, archives other than structurally validated DOCX, MIME/signature mismatch, encrypted/active content, and limit violations.
2. **REQ-002 — Fixed provider boundary.** Resolve one command-provider profile from trusted configuration. The executable and argv template are immutable configuration, stdin/stdout use bounded canonical JSON/JSONL, shell execution is forbidden, and the caller cannot select a provider or model.
3. **REQ-003 — Offline implementations.** Ship one sealed deterministic conformance fixture and one default unavailable profile. The unavailable profile must return `provider_unavailable` without reading input bytes, a credential, or the network, and without fallback.
4. **REQ-004 — Closed specification.** Normalize into `StaticLandingSpecV1`, limited to fixed site/origin, plain text, closed section kinds, local content-addressed assets, SEO metadata, source-backed claims, and deterministic style tokens. HTML, CSS, JavaScript, commands, prompts, tools, analytics, forms, credentials, arbitrary origins, and authority claims are forbidden model output.
5. **REQ-005 — Add-only rendering.** Render escaped framework-free HTML/CSS only under `side-projects/seo-landings/therealaidarkfactory-online/` in a fresh disposable exact-SHA workspace. The existing showcase and all other repository paths are read-only reference inputs.
6. **REQ-006 — Bounded independent evaluation.** Evaluate the sealed candidate with a distinct read-only identity and fixed rubric. Permit one initial attempt plus at most two repairs; the writer never receives hidden fixture bytes and cannot self-select a winner.
7. **REQ-007 — Exact candidate identity.** The trusted workspace boundary derives candidate SHA/tree, complete file inventory, modes, and digests. Branch labels and model assertions are not identity.
8. **REQ-008 — Deterministic artifact.** Package only the selected inventory in sorted order with fixed timestamps and canonical modes. Emit an immutable ZIP and `.sha256` sidecar bound to the same exact candidate and provenance record.
9. **REQ-009 — Disabled production.** Expose a publisher protocol but compose only an unavailable implementation. It must reject before any transport call and never return a live URL.
10. **REQ-010 — Additive compatibility.** Do not modify the existing showcase, product ZIP/sidecar, migrations `001`-`018`, or prior M0-M9 contracts. Import zero commits from stale branches.

## Acceptance criteria

- [ ] **AC-001:** Valid sealed fixtures for all five media kinds produce the same canonical spec when their semantic content is equivalent; invalid shape, type, size, tenant, repository, idempotency, or content fails closed.
- [ ] **AC-002:** The fixed sealed command fixture produces deterministic evidence; absent, mismatched, caller-selected, or default profiles produce `provider_unavailable` with zero command/network calls.
- [ ] **AC-003:** Rendering and evaluation produce an append-only chain of one to three exact-SHA candidates under the add-only domain path; no fourth invocation or write outside that path is possible.
- [ ] **AC-004:** Repeated packaging of one sealed candidate yields identical ZIP bytes and sidecar content, and every archive member matches the manifest path/mode/SHA-256.
- [ ] **AC-005:** API/result and publisher tests prove that no fixture/local artifact can become `live`, `https_observed`, or `indexed_observed`.
- [ ] **AC-006:** Frozen predecessor and showcase byte inventories remain identical and architecture/contract registration is additive.

## Bounded input policy

| Kind | Accepted shapes | Maximum |
| --- | --- | --- |
| `text` | strict UTF-8 `text/plain` | 1 MiB and 200,000 Unicode scalar values |
| `audio` | WAV, MP3, or Ogg signature | 25 MiB and 15 declared minutes |
| `image` | PNG, JPEG, or WebP signature | 10 MiB and 40 megapixels |
| `pdf` | non-encrypted PDF | 20 MiB and 100 pages |
| `docx` | non-macro OOXML DOCX without external relationships | 10 MiB compressed, 50 MiB expanded, 2,000 ZIP entries |

Provider output is at most 256 KiB; canonical spec is at most 128 KiB; artifact member count, path length, individual bytes, and total bytes use explicit finite constants. Values above are ceilings, not targets.

## Failure behavior

- Missing or ineligible profile, executable identity mismatch, unrecognized protocol version, non-terminal/duplicate terminal output, or malformed provider output yields `provider_unavailable` or `needs_human`; no fallback occurs.
- Digest, tenant, repository, exact-SHA, workspace, evaluator, or prior-attempt mismatch yields `needs_human` and no package.
- Active content, prompt/tool/authority-shaped output, unsafe URL, unsupported claim, or unproven asset rights yields `rejected` or `needs_human`; it is never silently removed and treated as approved content.
- Timeout, cancellation, child-process leakage, workspace cleanup failure, or artifact replacement race is explicit and prevents a success result.
- A non-pass result on attempt three is terminal `needs_human`.
- Any production publisher request in the repository default composition is denied before transport, with zero external effect.

## Non-functional requirements

- **Security:** no shell, inherited credentials, unrestricted environment, raw input logging, arbitrary network, symlinks, traversal, special files, executable site members, or cross-tenant access.
- **Reliability:** canonical digests, immutable attempt chain, exact SHA/tree, bounded time/bytes/processes, cleanup on every path, idempotent replay, and fail-closed ambiguity.
- **Performance:** deterministic static rendering and packaging; no frontend runtime framework or third-party first-load dependency; browser checks at 320, 768, 1280, and 1920 px.
- **Accessibility:** semantic landmarks, one H1, keyboard-visible focus, adequate contrast, alt text policy, zoom-safe layout, and reduced-motion behavior.
- **Observability:** bounded structured IDs, digests, counts, timings, disposition, denial reason, cleanup result, and zero-effect assertion; no raw input, native model stream, reasoning, credential, or hidden fixture content.

## Operational blockers retained

An operational provider/snapshot/deployment phase remains blocked on all of: explicit authorization to transfer selected input; a pinned execution-eligible provider profile; authoritative current-site source and rollback snapshot; deployed hidden evaluator and exact-head Trust CI evidence; signed artifact authority; factual M8 activation/currentness; real M9 environment/recovery evidence; exact hosting/document-root/TLS configuration; and separately delegated production actions. Their absence is a required fail-closed state, not an implementation placeholder.
