# Architecture — L5 multimodal landing dogfood

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This document cannot widen typed scope or authority.

## Decision

Add a repository-local landing pipeline over the delivered M5 workspace/provider boundaries and M6 semantic-evaluation concepts. It has a fixed command-provider port, a sealed deterministic fixture, an unavailable default profile, a trusted deterministic renderer, an independent evaluator, a three-attempt ceiling, exact-SHA site packaging, and a disabled publisher. It adds no migration, service, framework, provider SDK, network path, or production capability.

The tracked showcase at `side-projects/seo-landing-showcase/` is immutable reference material. The separate private target is `github.com/Dimkox/ai-dark-factory-landing` at SHA `176efcaab931c2482781ff163c621b10aa05dee9`, tree `f2bdcecc6dbe9ecc82007610d398ca12bd75e07f`; generated `index.html` and `content.css` exist only in fresh disposable target workspaces and, after selection, in a content-addressed artifact. The local target clone is read-only, no stale branch is imported, and indexed URL topology, locale/legal pages, verification files, robots, sitemap, canonical, and hreflang facts stay byte-identical to the source.

## Components

| Component | Responsibility | Prohibited authority |
| --- | --- | --- |
| Landing contracts | Closed records, canonical JSON and domain-separated digests | I/O, provider choice, state mutation |
| Intake/quarantine | Bounded type/shape checks, tenant binding, private transient bytes | Caller paths/URLs, durable raw content |
| Command-provider port | Fixed executable/argv, canonical stdin/JSONL stdout, limits | Shell, fallback, arbitrary env/network |
| Sealed fixture / unavailable profile | Deterministic local proof / default closed denial | Operational model claim, credentials |
| Trusted renderer | Escape a closed spec into target-root `index.html` and `content.css` | Model HTML, script, remote dependency |
| Workspace broker | Fresh exact-SHA checkout, allowlisted writes, Git-derived result identity, cleanup | Shared mutable worktree, ref mutation |
| Independent evaluator | Read-only fixed rubric and closed `pass|repair|needs_human` result | Writer identity, hidden-data disclosure, selection authority |
| Artifact builder | Sorted canonical manifest, ZIP and sidecar | Product ZIP mutation, mutable latest identity |
| Publisher port | Describe later materialization boundary | Any repository-composed transport or live result |

## Data flow

```text
authenticated raw body
  -> bounded private quarantine + LandingInputV1
  -> trusted profile resolution
  -> fixed command-provider port
  -> closed StaticLandingSpecV1 + provider evidence
  -> disposable exact target SHA/tree workspace
  -> deterministic renderer
  -> read-only evaluator
       repair -> fresh workspace (total attempts <= 3)
       pass   -> exact candidate SHA/tree
       other  -> needs_human
  -> deterministic site ZIP + .sha256
  -> artifact_ready
  -X-> unavailable production publisher
```

Raw data and provider-native output are transient. Durable/local result records contain only bounded closed projections, identities, counters, reason codes, and digests. Untrusted input never becomes an executable, argument, path, policy, origin, capability, or authority.

## Contracts and state

The additive `factory/contracts/openapi/landing-dogfood.v1.json` exposes submit, status, cancel, and result operations. Six additive JSON schemas cover input, static spec, provider evidence, attempt, evaluation, and artifact. Existing OpenAPI and M0-M9 schemas remain byte-identical.

Local states are `accepted`, `normalizing`, `generating`, `evaluating`, `artifact_ready`, `provider_unavailable`, `rejected`, `cancelled`, and `needs_human`. The only loop is `evaluating -> generating` while the next ordinal is at most three. `live`, `https_observed`, and `indexed_observed` are not representable by the repository default composition.

## Trust and isolation

- Input bytes are tenant/repository/job-bound, mode `0600`, outside Git, and purged after terminal processing.
- Provider commands are selected from trusted immutable profiles and launched without a shell, inherited secrets, proxy variables, Git authority, or repository network destinations.
- Each candidate uses a host-owned `0700` temporary root under `umask 0077`; exact base SHA/tree is verified before work, and child processes/workspace are cleaned on every outcome.
- The writer receives only the closed spec and bounded prior repair projection. The evaluator has a different identity/context and read-only candidate access.
- Candidate identity and artifact membership are derived by trusted Git/filesystem code, never asserted by provider output.
- Local evidence cannot substitute for the App-owned exact-PR-head Trust CI check, signed artifact authority, or production approval.

## Determinism

Canonical structured digests use UTF-8, NFC strings, sorted keys, declared ordered arrays, no duplicate keys, and no non-finite numbers. The renderer is a pure function of spec, renderer version, and verified repair codes. ZIP entries are sorted, timestamps fixed, modes normalized, undeclared metadata excluded, and the sidecar hashes final ZIP bytes.

## Production boundary

Production is blocked until an authoritative current-site snapshot and rollback manifest, execution-eligible provider profile and data-transfer authority, deployed hidden evaluator/Trust CI evidence, signed site artifact, factual M8/M9 operational evidence, exact hosting/TLS configuration, and explicit external action grants exist. The publisher implementation in this scope always denies before transport. User-supplied SERP evidence establishes observed indexing; inability of automation to see origin bytes is reported separately and never reclassified as non-indexing.

## Architecture compatibility

Migrations `001`-`018`, existing control/execution/semantic/shadow/autonomy/delivery contracts, the published `2.0.13` product package, and the showcase remain frozen. New architecture nodes and dependencies are additive. `L5` is the feature name and does not alter M8 autonomy levels `L0`-`L2`.

## Recovery

Before artifact creation, cancellation or failure destroys transient input/workspace state and leaves the repository/showcase untouched. After artifact creation, disabling the local feature and deleting only the content-addressed candidate artifact is sufficient. A future production rollback may restore only an exact captured predecessor under separate authority; it is not implemented here.
