# Architecture — operator-pilot vertical

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Boundary and data flow

The new top-level `pilot/` component is owned by the local single operator. It is not imported by `factory/`, `delivery/` or `trust-ci/`, and is disabled unless a closed live profile and explicit CLI switch are supplied.

`trusted profile + issue number -> read-only issue/base snapshot -> private exact clone -> one pinned Codex CLI -> trusted Git seal -> one sandboxed unittest command + deterministic semantics -> exact push grant -> non-force new ref -> exact PR grant -> draft PR -> read-only App/human observation`

The durable chain commits each output before the next transition. Provider and GitHub transports are injected ports; deterministic fakes prove local behavior. The live adapters own argv construction and receive no shell fragments. GitHub/Codex credentials remain opaque host capability, outside model/test environments and evidence.

## Components

- `contracts`: closed values, canonical JSON/digests and schema validation.
- `profile`: the one exact target/model/executable/path/test policy.
- `store`: private SQLite append-only records, prepared intents and idempotency keys.
- `issue_source`: bounded read-only `gh` projections and base observation.
- `workspace`: private clone, remote removal, exact checkout, trusted seal and cleanup.
- `codex_executor`: pinned executable/version/digest, one ephemeral noninteractive invocation in workspace-write sandbox.
- `validation`: credential-free bubblewrap test runner and independent deterministic semantic gate.
- `authority`: exact literal operation-resource validation against current delegated grants.
- `github`: non-force exact ref publisher, draft-PR publisher and observation-only reconciliation.
- `coordinator`/`cli`: five finite transitions; default unavailable; no background retry loop.

## Architecture ruling

Route `0ce2d62a018e` remains valid as the agent-selection record. The typed spec is red and the verifier must independently derive `risk_pre=yellow`, an architecture-expansion escalation and `risk_post=red`. This post-diff escalation is the designed mechanism; regenerating a route would add no authority. Required scope strings classify review obligations but are not operational grants.

`TD-PILOT-OPERATOR` is a separate local-preflight trust domain. It may have explicit allowlisted egress to external Codex and GitHub nodes and a private local state/workspace boundary. No new edge originates in `TD-FACTORY-CONTROL`; Trust CI remains an independent read-only observed authority.

## Recovery and risk

- Before Codex start, store `prepared`; after a start without a sealed output, recover to terminal `provider_outcome_ambiguous`.
- Before push/PR, store the canonical request and grant-use digest. An in-flight restart performs exact observation only.
- Ref conflict, base/issue drift, multiple matching PRs, or unavailable observation is terminal; never force or retry.
- A missing sandbox/profile/executable/credential/grant/check produces a typed stop, not fallback.
- Landing branch protection currently returns private-plan `403`, and deployed Trust CI policy currently allowlists only the control repository. A draft proposal therefore remains `merge_eligible=false` until external operators establish that independent gate.
