# M7.1 durable evidence lookup — scoped proposal

Base: `64378d28c7b78cace463d96470c1898294b8f196` (PR #32 merged). Branch: `feat/m7-durable-evidence-lookup`.
Status: design only; implementation and operational actions are pending.

## Problem and outcome

The historical evidence CLI is delivered. Existing delivery history is useful evidence, but absent task-profile, human-acceptance and intervention records cannot be filled by inference. The next dependency is a durable, inspectable M7 lookup bound to actual producer records.

M7 bundles/outcomes have no persistence service. The V1 bundle permanently has `blocked_pending_durable_lookup`; M8 permanently reports acceptance/currentness unavailable, and M9 relies on that boundary. Add a separate persisted lookup/preflight result without changing those versioned meanings.

## First delivery

Use the existing PostgreSQL infrastructure, an additive migration, separate closed contracts and a read-only preflight consumer. Recompute producer identities, distinguish missing/rejected/stale evidence, preserve immutable historical facts and reconstruct results after restart. No new framework, database engine or running service is proposed.

External observations must bind exact result head, checked base, deployed epoch, check/App identity and explicit human outcome. A signed Trust CI envelope does not itself carry every field: retain authenticated source provenance separately rather than inventing signed claims. Without a trusted source the result stays unavailable.

## Scope and authority

The route `18ea639b9d02` selected design analysis (`write_agent=null`) and names `scope_and_design_approval`. This package prepares that decision. After approval, route the agreed implementation with one write owner and preserve applicable gates. No V1 behavior change, M8 promotion/activation, production migration, live collector, deployment or external authority change is included.

The user's GitHub milestone question is addressed by a separate reviewable projection in this package. API inspection found zero milestones and zero issues. Creating GitHub objects requires named external-write delegation. Prior consent covered only the historical-evidence branch/PR.

## Privacy

Public documents use public repository facts and synthetic fixtures only. Private historical consumer names, task counts and operational details remain outside this proposal.
