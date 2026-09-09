# Task analysis — finite M5 scope and acceptance ruling

## Ruling

**APPROVE repository-local implementation** for route `6c578a9933b3` on exact M4
`67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` (tree
`399c65e7c65626f3d5236cae1bce009c5d3a9714`). Reuse the final M5 semantics through
`3940267ac5754ad07a047894102015d33eb759b1` (tree
`4646582a7c5ff6f08ee7e8462687da400459b08d`) as source material, not as ancestry,
verification, review, or delivery authority. Exact M4 wins every overlap; a whole-tree merge or sequential
cherry-pick is outside scope.

The user-approved gate covers source changes in this repository and the four new, unpublished migration files
`014`-`017`. It permits isolated disposable PostgreSQL testing. It does not authorize applying migrations to a
shared or persistent environment, provider invocation, network or external writes, credentials, systemd
installation or activation, push, pull request, merge, tag, release, deployment, or production operation.

## Bounded outcome

Deliver one disabled-by-default local execution control plane that preserves M4 and adds:

- immutable, separately domain-digested task packets and run manifests;
- closed execution schemas and additive provider-neutral v1/v2 API contracts;
- bounded canonical JSON/JSONL processing and exact-version offline Codex/Grok fixture adapters, with no
  subprocess, network call, or provider fallback;
- capability-shaped note, artifact, usage, terminal, workspace, and snapshot/attestation boundaries;
- authenticated repository-scoped execution mutations bound to the durable task, run, owner, role, lease,
  fence, allocation, deadline, budget, packet, manifest, and workspace identities;
- canonical persistence and atomic server-owned terminal finalization through migrations `014`-`017`;
- bounded factual restart/orphan recovery, exact-handle idempotent cleanup, and fixed-cardinality metrics.

Migrations `014`-`017` are one forward schema unit. `016` may remove only provisional constraints introduced by
the unpublished M5 schema after their canonical replacements exist in `015`; it must not rewrite or remove M4
schema, evidence, or migrations `001`-`013`.

## Required invariants

1. M4 migrations `001`-`013`, the 17-operation control contract, legacy claim identity, state transitions,
   history, authorization, fencing, capacity, retry, kill-switch, accounting, deadline, and budget behavior are
   preserved.
2. Repository identity is the tenancy boundary. Request data and provider output never grant repository,
   provider, role, policy, stage, workspace, snapshot, attestation, or terminal authority.
3. Packets and manifests are insert-once; stages, proposals, attestations, results, and recovery outcomes are
   immutable or append-only. Exact replay is idempotent and conflicting replay fails closed.
4. Terminalization commits at most one result under a live M4 authority tuple. A stale or mismatched tuple,
   unavailable trusted snapshot, or invalid attestation commits no partial effect.
5. Recovery may record only factual `orphaned`/`cancelled` state, release the exact M4 allocation, and schedule
   exact-handle cleanup. It cannot fabricate a provider proposal, attestation, successful result, or semantic
   verdict.
6. Product documentation uses formal engineering terminology and describes only capabilities proven by the
   current tree. Exploratory labels, promotional shorthand, and conversational scope language are excluded.

## Finite local acceptance criteria

The following criteria are complete; extending them requires an explicit scope change.

1. **M4 non-regression:** migrations `001`-`013` and the current control OpenAPI remain byte-identical, all 17
   control operations retain their contracts, and the legacy claim continues to return the M4 intent digest.
2. **Schema safety:** fresh and exact schema-13 disposable PostgreSQL 17 databases migrate transactionally through
   `014`-`017`; checksum/order, role topology, canonicalization gates, timeout, and injected-failure checks prove
   no partial schema or evidence mutation. PostgreSQL below 17 fails before `017` mutates state.
3. **Execution identity:** one live M4 grant plus trusted selection creates exactly one canonical packet and
   manifest bound to all authority, source, policy, provider, workspace, acceptance, and limit identities;
   changed input changes the digest and conflicting replay is rejected.
4. **Offline contract boundary:** closed schemas, bounded parser, and exact-version fixture adapters reject
   malformed, oversized, unknown, identity/sequence-mismatched, post-terminal, hidden-reasoning, or ineligible
   input. No product path launches a provider, subprocess, network request, or fallback.
5. **Authorization and isolation:** every mutation requires authenticated `task:execute`, repository permission,
   durable role and owner equality, and the live task/run/fence/allocation tuple. Cross-repository, cross-task,
   cross-run, cross-workspace, stale-fence, and reader-write attempts commit nothing.
6. **API and terminal flow:** execution-disabled startup exposes no M5 routes and leaves M4 usable. Complete
   injected local composition exposes the six logical v1/v2 operations matching their separate closed contracts;
   proposal, trusted snapshot/attestation, result, and M4 disposition finalize atomically and replay to one
   outcome.
7. **Restart recovery:** disposable PostgreSQL 17 evidence proves bounded indexed discovery, concurrent fencing,
   preservation of live work, factual stale-work terminalization, higher-fence exact-handle cleanup, durable
   replay across two restarts, and zero synthetic proposal/result evidence.
8. **Exact-tree evidence:** focused unit/contract/PostgreSQL checks, M4 regressions, final PR-mode verification,
   and every route-selected review pass against one clean final fingerprint. Local evidence is not merge,
   deployment, or external Trust CI authority.

## Risk and review stop rule

Risk remains **high** because the slice joins durable state, authorization, tenant isolation, untrusted provider
output, and a versioned API. A finding blocks local acceptance only when supported by a concrete reproduction or
direct invariant violation in one of these classes:

1. **Core-flow break:** M4 regresses, or the required claim-to-terminal/retry/recovery path cannot complete or
   cannot satisfy its closed contract.
2. **Authority or isolation bypass:** an unauthorized actor, repository, role, owner, stale fence, provider input,
   workspace handle, or incomplete startup composition can gain or exercise execution authority; secrets,
   private reasoning, network, or external capabilities cross the declared boundary.
3. **Data loss or corruption:** migration or runtime behavior loses, rewrites, cross-binds, duplicates, partially
   commits, or fabricates authoritative packet, manifest, proposal, attestation, result, accounting, history, or
   recovery evidence.

Style preferences, optional topology, additional provider versions, broader observability, performance tuning,
retention automation, fleet/HA behavior, and defense-in-depth that does not demonstrate one of the three blocking
classes are recorded once in a bounded follow-up backlog. They do not expand this milestone or trigger repeated
implementation/review cycles.

## Explicit exclusions and forward recovery

Live provider execution, real workspace or Git mutation, credential issuance, egress enablement, host/container
qualification, service installation/activation, M6 semantic adjudication, and all external delivery actions are
excluded. Before any persistent application, rollback is removal of the unmerged M5 source while retaining M4.
If migrations `014`-`017` are ever separately authorized and applied, recovery is to quiesce new claims, preserve
all execution evidence, disable M5 routes, reconcile outstanding work, and forward-fix with `018+`; never
down-migrate or rewrite `001`-`017`.
