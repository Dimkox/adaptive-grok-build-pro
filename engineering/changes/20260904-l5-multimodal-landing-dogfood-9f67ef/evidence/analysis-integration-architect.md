# Integration and production-boundary analysis

**Route:** `9f67efd2575c`
**Analysis basis:** local branch `feature/l5-multimodal-landing-factory`, source HEAD `ad6d23cc30c11e5ea51c388213f5ebdfe306fb56`, tree `878fd39838d43131b05dfa5e553be11260237342`
**Role:** read-only integration/security analysis; this report grants no merge, publication, or production authority.

## Decision

Implement L5 as a closed, content-addressed pipeline that produces a locally verifiable static-site artifact. Reuse the existing M0-M9 contracts, exact-SHA verification patterns, recovery semantics, and external Trust CI boundary; do not create a parallel release authority.

The Namecheap materializer must be a disabled, preconfigured HTTPS adapter. Because the exact current site source/snapshot, remote document root, supported HTTPS management interface, and host-owned credential reference are not present, production materialization is **BLOCKED**. The implementation may provide contracts, a fake adapter, and fail-closed orchestration, but must neither infer hosting details nor claim a live/indexed site.

## Bounded architecture

1. A versioned authenticated API accepts bounded text, audio, image, PDF, or DOCX payloads and records tenant, request, correlation, media digest, declared/detected type, and policy version. Input bytes remain untrusted data and never become system or tool instructions.
2. Pinned decoders and a pinned model/prompt/tool policy normalize input into a closed `StaticLandingSpecV1`. Reject active content, remote includes, filesystem paths, executable instructions, unknown fields, and any spec outside the existing landing/SEO showcase.
3. A host controller creates at most three independent attempts in host-owned disposable Git workspaces. Generation has no network or publisher credentials.
4. An independently configured hidden evaluator receives immutable candidate manifests, not mutable workspaces. It selects one candidate deterministically under its pinned rubric; the generator cannot read evaluator fixtures, secrets, or scores before finalization.
5. An exact-head verifier validates the selected tree and emits an attestation bound to source SHA/tree, input/spec/model/prompt/tool/evaluator/verifier identities, and candidate digest.
6. A deterministic packager emits an immutable ZIP and checksum sidecar into a content-addressed namespace. The existing product ZIP `packages/adaptive-grok-build-pro-v2.0.13.zip` is a separate release artifact and must never be overwritten or repurposed for the site.
7. PR delivery remains governed by the GitHub App-owned Trust CI check on the exact PR head. A separate host-owned publisher may stage, activate, or roll back the exact site artifact only when every production precondition and separate scoped authority is present.

## Host-owned disposable Git workspace

The workspace root is supplied by trusted host configuration, owned by the runner identity, mode `0700`, outside the repository and outside any user-controlled upload directory. Create each attempt with `umask 0077` and `mkdtemp`; reject an existing path, symlink, mount escape, unexpected owner/mode, or shared mutable clone.

Materialize from the authoritative repository using an explicit 40-hex source SHA already resolved by the controller. Fetch only the required object/ref under host policy, then use a detached checkout. Before generation, require:

- `HEAD` equals the requested SHA and the computed Git tree equals the request;
- no symbolic branch, extra worktree changes, submodule indirection, alternates, replace refs, or unsafe hooks/config;
- no use of stale milestone branches as authority; branch names are display metadata only;
- read-only mounted inputs and limits on bytes, files, paths, CPU, memory, processes, and wall time;
- no inherited Git, proxy, cloud, model, or publisher credentials; no outbound network; stdout/stderr are bounded and redacted.

Each attempt gets a fresh process group/sandbox and output root. On success or failure, terminate descendants, wait for exit, unmount/release handles, capture the manifest, and remove the workspace. Cleanup failure makes the attempt failed and quarantines the path for host cleanup; it must not be reused.

## Exact-head verification and hidden evaluation

`CandidateManifestV1` should include request/tenant IDs, attempt ordinal, source SHA/tree, normalized-spec digest, generated-tree digest, complete path/mode/hash inventory, generator image/model/prompt/tool-policy digests, start/end timestamps, and limit outcomes. Only regular static files under the declared output root are allowed; reject symlinks, hard-link ambiguity, traversal, special files, executable bits, case-colliding paths, undeclared files, JavaScript, remote dependencies, and secrets.

The evaluator accepts one to three sealed manifests plus read-only candidate trees, a pinned hidden corpus/rubric digest, and fixed limits. It returns scores, disqualifications, chosen manifest digest, and deterministic tie-break data. Missing candidates are acceptable only when their failures are recorded; zero eligible candidates, an unresolved tie, rubric mismatch, mutation during evaluation, or evaluator timeout fails the request closed.

The verifier runs after selection against the same sealed candidate. Its attestation must bind at least:

- repository identity, exact source SHA and tree;
- request, input bundle, normalized spec, selected candidate, and complete output-tree digests;
- model, prompt, decoder, generator, evaluator, policy, holdout, and runner-image identities;
- commands/check results, timestamp/expiry, and attestation schema/signing identity.

Static checks must cover closed-spec conformance, HTML/CSS validity, no active/remote content, accessibility essentials, responsive rendering, size budgets, canonical URL, robots/sitemap consistency, and deterministic rebuild where supported. The attestation is evidence for the L5 artifact; it is not the App-owned merge check and cannot mint human production approval.

## Immutable ZIP and sidecar

Package only the selected manifest inventory with canonical UTF-8 paths, sorted order, fixed timestamps, normalized non-executable modes, and no symlinks or undeclared metadata. Write to a private temporary file, fsync, compute SHA-256, and atomically rename into a content-addressed location. Create the `.sha256` sidecar from the final bytes and publish it atomically as a pair; pre-existing content at the same digest must match byte-for-byte or fail.

`SiteArtifactV1` must bind the ZIP and sidecar digests to the candidate/verifier attestation, source SHA/tree, provenance/SBOM, intended canonical host, creation time, schema, and optional exact predecessor artifact. Neither mutable `latest` names nor a branch name may be used as identity. Replays for the same inputs must return the existing immutable record rather than rebuild or replace it.

## PR and delivery authority separation

The following boundaries are independent and cumulative:

- Local generation, evaluation, verification, and review produce evidence only.
- Repository push requires an exact delegated local grant for the named branch and current SHA/tree; no report or route supplies it.
- Merge eligibility requires the deployed GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact PR head plus any externally required signed approvals. Repository code, local receipts, and local grants cannot substitute for it.
- A merged source SHA only makes an artifact eligible for consideration. It does not authorize staging, activation, DNS, hosting, release, or rollback.
- Production staging, activation, and rollback each require an explicit action/resource grant bound to repository, route/change, merged SHA/tree, artifact digest, target account/domain/document root, expected baseline digest, operation, and TTL. A wildcard is forbidden. Any separately required human-signed production/security approval remains external and cannot be created or read by the agent.

Trust CI signing keys, GitHub App credentials, human approval keys, and the publisher credential must reside in distinct host-owned trust domains. The publisher receives only a short-lived credential handle through a protected descriptor/agent interface; it must not read repository `.env` files, private-key stores, or inherited environment secrets.

## Disabled HTTPS publisher contract

Do not assume FTP, SFTP, cPanel, API shape, account name, DNS provider, or document root from the registrar/hosting brand. Host-owned configuration must explicitly provide a supported HTTPS transport adapter, exact management endpoint/origin, account and site identity, remote document root, TLS trust policy, credential handle, staging/activation capability, health URL, and retention policy. Configuration is immutable for one operation and its digest is included in evidence.

Network policy is deny-by-default:

- no inbound public listener; control is a local protected Unix socket or loopback-only endpoint;
- publisher egress is TCP `443` only to the exact configured HTTPS management host and, for post-activation observation, `therealaidarkfactory.online:443` plus the host resolver required by platform policy;
- deny FTP `21`, SSH/SFTP `22`, arbitrary DNS destinations, redirects to a different origin, plaintext downgrade, proxy inheritance, and certificate/hostname verification bypass;
- enforce TLS 1.2 or newer, bounded request/response sizes and timeouts, and redact authorization material from logs.

Before the first remote mutation, acquire a complete, restorable, host-side baseline snapshot and manifest of the current site. Bind its digest to the request and re-check the remote precondition immediately before activation. If a trustworthy snapshot cannot be acquired, cannot be restored in a dry/fake adapter exercise, or the remote state has changed, stop without writing.

Stage the new artifact under a unique content-addressed remote name, upload only manifest-declared files, and verify remote hashes before activation. Prefer an atomic server-side release pointer/directory switch. If the configured HTTPS interface cannot provide atomic activation, it must expose an explicitly tested equivalent in which versioned assets are uploaded first and the entry manifest/index is switched last; otherwise the adapter is unsupported and fails closed.

## Idempotency, retry, and rollback

Use a durable host-owned operation ledger, not repository state. The idempotency key is the digest of operation type, repository, route/change, merged SHA/tree, artifact digest, target environment/account/domain/document root, publisher-config digest, and baseline digest. States are `prepared`, `staged`, `verified`, `activated`, `rolled_back`, or `failed`. The same key and request digest returns the recorded result; key reuse with different bytes is denied.

Retry only read-only discovery and content-addressed upload operations that are provably idempotent: at most three attempts, exponential backoff with jitter, and a total deadline. Do not retry authentication/authorization failures, TLS failures, policy/precondition/hash/schema errors, or permanent HTTP 4xx responses. Never blindly retry activation after an ambiguous response. Reconcile remote state read-only by artifact/release ID; if exact state cannot be proven, halt for human recovery without deleting or overwriting anything.

Activation records the exact predecessor before switching, then performs bounded HTTPS health and content checks. On a failed health gate, a separately authorized rollback restores the exact predecessor release/snapshot once, verifies its manifest and public response, and records new immutable evidence. Rollback may only narrow/restore; it cannot generate a replacement, change DNS, or select an unapproved artifact. Failed rollback freezes further mutation and preserves both versions and all evidence.

## Publication and indexing evidence

Success has distinct states: `artifact_verified`, `staged`, `activated`, `https_observed`, `indexable`, and `indexed_observed`. The canonical URL is `https://therealaidarkfactory.online/`; HTTPS observation must reject redirect escape and must bind response evidence to the activated release/manifest. Validate canonical metadata, robots directives, sitemap availability, response content type, and crawlable links. Search-engine indexing is asynchronous and must never be inferred from successful deployment; return `indexed_observed` only with separately collected, timestamped search/provider evidence.

The API may return the live URL only after `activated` and `https_observed`; until then it returns the immutable artifact/evidence identity and a non-live state. Signed evidence contains no credentials or raw uploaded customer data.

## Fail-closed acceptance matrix

| Condition | Required behavior |
|---|---|
| Exact current site source/snapshot absent | Permit contract/fake-adapter work only; deny all remote mutation. |
| Authoritative exact SHA/tree cannot be resolved, is stale, or mutates | Abort generation/verification; never fall back to a branch tip. |
| Workspace owner/mode/path/isolation check fails | Reject the attempt; quarantine and do not reuse the workspace. |
| Input, decoder, model, prompt, evaluator, or policy identity is unpinned | Reject before generation or attestation. |
| More than three generation attempts requested | Reject the request; retries do not create extra candidates. |
| Candidate/evaluator/verifier/artifact digest mismatch | Quarantine output; no packaging, PR evidence, or publication. |
| Exact Trust CI check missing/stale/wrong App or policy epoch | Not merge-eligible and not production-eligible. |
| Namecheap HTTPS endpoint, document root, baseline, TLS policy, or credential handle missing | Publisher remains disabled; no discovery by mutation. |
| Scoped staging/activation grant or required external human approval absent/expired | Deny that operation; a route or local receipt is insufficient. |
| Remote baseline differs immediately before activation | Stop; require a new snapshot, artifact decision, and authority binding. |
| TLS, redirect-origin, remote hash, or health check fails | Stop; do not retry policy failures; roll back only under exact rollback authority. |
| Activation outcome is ambiguous | Perform read-only reconciliation; if unresolved, freeze mutations and escalate. |
| Site is deployed but no indexing evidence exists | Report `indexable`, never `indexed_observed`. |

## Minimum implementation and evidence seams

The first vertical slice should add versioned closed contracts, deterministic workspace/manifest/artifact orchestration, fake model/evaluator/verifier adapters, a fake CAS/publisher with crash/replay simulation, and a disabled production HTTPS adapter that validates complete host configuration and authority before any transport call. It must reuse M9 signed-artifact, promotion, exposure, observation, and exact-predecessor recovery concepts rather than weakening or duplicating them.

Focused tests must prove exact-SHA/tree pinning, stale-branch rejection, secure workspace ownership/cleanup, three-attempt ceiling, hidden-evaluator isolation, deterministic selection/package bytes, ZIP traversal/symlink rejection, sidecar binding, replay idempotency, ambiguous-activation reconciliation, baseline compare-and-swap, egress/redirect denial, grant expiry/resource mismatch, predecessor-only rollback, and that no transport call occurs while production prerequisites are missing.

No production go/no-go is possible from the current repository state. The explicit unblock inputs are: an authoritative snapshot/source and restorable baseline for the existing site; a verified Namecheap-supported HTTPS publishing interface and exact host-owned configuration; an eligible exact merged SHA/artifact; successful fake/staging recovery evidence; and separately granted production actions with all external Trust CI/human gates satisfied.
