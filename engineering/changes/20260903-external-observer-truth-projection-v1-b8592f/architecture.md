# Architecture — External Observer truth projection v1

## Current behavior

Repository-local current-state documents and receipts carry mutable SHA/PR/release claims, while remote truth is checked ad hoc. No single component proves snapshot coherence, exact Check Run App ownership, merge ancestry or release lag, so stale claims can look current.

## Proposed component and boundaries

Add one separate operator-owned nonprivileged read-only `External Observer` service/domain. It is not inside the adaptive-delivery controller and is not Factory, Trust CI, a deployment controller or a competing framework.

Owned future paths: `.grok-stack/adaptive_grok/external_observer.py`, `scripts/grok_observer.py`, placeholder-only `engineering/external-observer/external-observer.example.json`, two closed schemas, fake tests and ignored `.grok-stack/runtime/external-observer/**`. Actual repo/branch/PR/check/App selection is operator-owned deploy config. Its only external edge is fixed allowlisted public HTTPS GET to `api.github.com`; local edges read bounded typed claims/config and write only normalized ignored observer state/output.

```text
PROJECT_STATE + typed evidence manifest + local receipts (claims)
                    |
                    v
       External Observer local-preflight ----GET only----> GitHub public REST
                    |
                    v
       PUBLIC_STATUS.v1 JSON -> deterministic text

No edge to Factory, M5 execution, Trust CI mutation, approvals, signing, deployment or production.
```

## Data and consistency flow

1. Validate closed config and bounded local claims; compute their canonical digests.
2. Acquire the observer lock before network/state work.
3. Read main and the exact configured PR, then exact-head checks, newest qualifying release/tag chain and required compare relations.
4. Reread main and PR; any identity movement rejects coherent freshness.
5. Compute independent stage projections and stable findings, validate `PUBLIC_STATUS.v1`, atomically persist normalized public state, and render text only from that validated object.

Exact equality establishes claim identity; a compare fixture matching the real REST shape (`status`, counts, `base_commit`, `merge_base_commit`, bounded `commits`) establishes ancestry or `release_behind` against the requested base/head identities. The exact PR endpoint is delivery authority for the configured proposal; list endpoints cannot establish absence/delivery. Historical milestone records remain claimed evidence with freshness metadata.

## Planned contracts

- `engineering/contracts/schemas/external-observer-config.v1.schema.json`: closed subject, identity and bounds.
- `engineering/contracts/schemas/public-status.v1.schema.json`: closed projection, stages, remote identities, freshness, stable findings and digest.
- Human text is a pure rendering of validated JSON, not a second contract or source of truth.

No event, queue, database or OpenAPI endpoint is introduced. A future optional signed public attestation endpoint requires separate design/security review; absent that, output is `attestation_unobservable`.

## Security, reliability and operations

No Authorization/cookie/proxy/userinfo, redirects, arbitrary URLs, retries, external methods or raw-body persistence. Strict bounded parsing treats all external/local strings as untrusted. One deadline/lock/CAS domain prevents mixed snapshots and lost projection state; prior valid state becomes stale on failure, while corruption fails closed.

The optional service is source-only/inert until separately approved and runs under a dedicated nonprivileged operator account with read-only repository access plus an owned runtime directory. No GitHub Actions or automatic enable/install path is allowed.

## Decisions and risks

Docs precede code and SHA facts precede evidence only after the implementation commit freezes. Remaining risks are GitHub unauthenticated rate limits, absence of a public signed attestation endpoint, and the tight program deadline; mitigations are stale/unknown truth, bounded failure codes and explicit non-completion rather than optimistic inference.
