# L5 Multimodal Landing Dogfood — Design

## Status and authority

Approved control-repository design for route `9f67efd2575c` and change `20260904-l5-multimodal-landing-dogfood-9f67ef`. The authoritative dogfood target is the separate private repository `github.com/Dimkox/ai-dark-factory-landing` at exact base SHA `176efcaab931c2482781ff163c621b10aa05dee9`, tree `f2bdcecc6dbe9ecc82007610d398ca12bd75e07f`; the current local clone is read-only input. Approval authorizes repository-local implementation only, not provider calls, data transfer, target mutation, push, PR, merge, signing, release, hosting, or production.

## Goal

Dogfood the delivered Adaptive Grok factory boundaries with one executable offline vertical: accept bounded text/audio/image/PDF/DOCX, normalize through a fixed provider-neutral command port, deterministically render and independently evaluate no more than three candidates, then emit an exact-SHA deterministic static-site ZIP and checksum sidecar. The vertical proves local orchestration, not operational Shapiro L5 autonomy.

## Fixed decisions

1. `side-projects/seo-landing-showcase/` remains byte-for-byte unchanged.
2. Candidate writes occur only to root `index.html` and `content.css` in a fresh detached workspace materialized from the exact target SHA/tree. The checked target clone and every other target path remain byte-identical, including the complete indexed URL topology, locale and legal pages, verification files, robots policy, sitemap, and canonical/hreflang source facts.
3. No stale feature branch is replayed or cherry-picked; import count is zero.
4. Command-provider executable and argv are selected only from trusted fixed configuration. Repository source ships one sealed deterministic fixture and one default unavailable profile.
   Provider output has no indexing authority: the only accepted policy token is `preserve_source`, and the trusted renderer must derive the actual robots, canonical, and hreflang values from the exact target baseline.
5. A trusted renderer, not model output, produces escaped static HTML/CSS. An independent evaluator returns closed reason codes and cannot write or disclose hidden fixtures.
6. The total generation ceiling is three: one initial candidate and at most two repair candidates, each with fresh context/workspace.
7. The site ZIP and `.sha256` sidecar are deterministic and bound to exact source/candidate SHA/tree and the full provenance chain.
8. The repository publisher is disabled and fails before transport. No live URL, indexing, or production claim is reachable.
9. M0-M9 contracts, migrations `001`-`018`, version `2.0.13`, and published artifacts remain unchanged.

## System boundary

```text
raw bounded body
  -> LandingInputV1 + private transient blob
  -> trusted profile resolver
  -> fixed command-provider port
  -> StaticLandingSpecV1 + LandingProviderEvidenceV1
  -> disposable exact target SHA/tree workspace
  -> deterministic renderer
  -> independent evaluator
  -> pass | repair (next ordinal <= 3) | needs_human
  -> exact candidate SHA/tree
  -> deterministic SiteArtifactV1 ZIP + sidecar
  -> artifact_ready
  -X-> UnavailableLandingPublisher
```

The existing M5 capability/workspace and M6 independent-validation concepts are composed, not redefined. L5 is a feature label; it does not add values to M8's `L0|L1|L2` model or bypass M9's human production boundary.

## Closed records

- `LandingInputV1`: tenant/repository/job/site, media kind/type, exact byte length/SHA-256, private blob reference digest, receive/expiry times, input digest.
- `StaticLandingSpecV1`: fixed site/origin, locale/direction, bounded SEO metadata, ordered closed sections, plain text, local asset references with digest/rights reference, source-backed claim references, spec digest.
- `LandingProviderEvidenceV1`: fixed profile/executable/protocol/adapter/model/prompt/tool/schema/decoder identities, request/response digests, bounded usage/times, disposition, evidence digest; never raw input/output/reasoning.
- `LandingAttemptV1`: ordinal `1..3`, input/spec/profile, exact base/head, workspace/result/renderer/evaluator/prior-attempt digests, times and outcome.
- `LandingEvaluationV1`: distinct evaluator identity/context, exact candidate subject, fixed policy/rubric, closed `pass|repair|needs_human`, sorted reason/requirement/finding digests.
- `SiteArtifactV1`: exact source/candidate SHA/tree, manifest and ZIP/sidecar digests, complete upstream provenance, canonical host intent, artifact digest, local-only disposition.

All records reject unknown fields, duplicate JSON keys, non-finite values, invalid Unicode, unbounded collections, identity mismatch, and digest mismatch. Canonical digests are domain-separated over UTF-8/NFC canonical JSON.

## Media and privacy policy

The fixed limits are text 1 MiB/200,000 scalars; audio 25 MiB/15 minutes; image 10 MiB/40 megapixels; PDF 20 MiB/100 pages and unencrypted; DOCX 10 MiB compressed/50 MiB expanded/2,000 entries with no macros, traversal, embedded packages, or external relationships. Declared MIME and bounded structural signature must agree.

Raw bytes are tenant-namespaced, mode `0600`, outside Git and candidate workspaces, and purged after terminal local processing. Provider output is at most 256 KiB and the canonical spec at most 128 KiB. Logs/evidence retain only bounded identifiers, counts, dispositions, and digests.

## Command-provider protocol

The trusted launcher invokes a fixed absolute executable with a fixed tuple of arguments, `shell=False`, a scrubbed allowlist environment, no repository/network/publisher credentials, bounded stdin/stdout/stderr, process-group timeout, and exactly one terminal canonical JSONL event. Untrusted data is carried only inside canonical stdin. Unknown protocol/capability, sequence error, duplicate/missing terminal event, output overflow, timeout, or identity mismatch fails closed.

The sealed fixture maps content digests to checked fixture responses and is explicitly non-authoritative. `UnavailableLandingProvider` is the default and returns `provider_unavailable` before reading the blob or launching anything. An operational provider/profile may be injected only by a future separately authorized composition.

## Rendering, evaluation, and attempt bound

The renderer is a pure function of the closed spec, renderer version, and optional verified repair reason codes. It owns escaping and emits framework-free local HTML/CSS only; spec fields cannot contain markup, scripts, commands, forms, analytics, remote dependencies, arbitrary URLs, or policy/authority instructions.

Each attempt uses a new host-owned mode-`0700` directory under `umask 0077`, a detached verified target base SHA/tree, no shared Git metadata, no outbound network, no inherited credentials, and a write allowlist restricted to target-root `index.html` and `content.css`. The broker derives the resulting SHA/tree and cleans all descendants/state on every exit.

The evaluator uses a different identity and fresh read-only context. The writer receives only verified closed repair codes, never hidden fixtures or free-form instructions. Attempt three without pass, repeated/contradictory/security findings, stale bindings, cleanup failure, or any fourth-attempt request yields `needs_human` without artifact creation.

## Artifact and production boundary

The packager accepts one sealed passing candidate. It rejects traversal, symlinks, special/executable files, case collisions, undeclared members, mutable input, and mismatch. It writes sorted canonical members with fixed timestamps/modes, hashes final bytes, and atomically creates a content-addressed ZIP/sidecar pair. It never touches `packages/adaptive-grok-build-pro-v2.0.13.zip`.

`UnavailableLandingPublisher` is the only repository-composed publisher. Production remains blocked until the current site source/snapshot and rollback manifest, authorized provider/data transfer, real hidden evaluator and exact-head Trust CI result, signed artifact, factual M8/M9 operational evidence, exact hosting/TLS configuration, reversible activation proof, and explicit resource-bound authority are supplied. User SERP evidence and automated origin visibility are recorded as separate facts; successful artifact creation implies neither deployment nor indexing.

## Failure and recovery

Every failure is typed and leaves the current repository/showcase/live site untouched. Cancellation purges transient input and workspace. A changed source, spec, provider, renderer, evaluator, or policy invalidates dependent evidence and requires a new exact-SHA run. Local rollback disables composition and reverts only additive L5 commits/artifacts; no migration or live rollback is needed.

## Acceptance

Focused tests must prove five-media intake, hostile-content inertness, fixed command identity, unavailable zero-call behavior, deterministic fixture/spec/render, tenant isolation, exact-SHA workspaces, path confinement/cleanup, evaluator separation, attempt ordinals `1..3`, deterministic ZIP/sidecar, predecessor/showcase preservation, and unreachable publication/live claims. After the source tree freezes, run one PR verifier and only then the route-selected independent reviewers.
