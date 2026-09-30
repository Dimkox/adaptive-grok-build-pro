# Requirements — Добавить новую локальную функцию VibeVM U6: детерминированный package graph resolver, lock cache offline replay, bounded unpack projection, boot checks, atomic generations, scoped caches, export fallback и тесты

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC83–86: resolution rejects cycles/conflicts/ambiguous overrides and altered, revoked or unauthorized cached identities before use; admitted snapshots replay offline or name the missing package.
- [ ] AC87–88: the managed boot block is idempotent and preserves owner text; volatile observation data does not change semantic identity while backend/config/local inputs do.
- [ ] AC89–90: archive projection is data-only and bounded; traversal, links, hooks and malformed bindings fail closed, and a mapping never becomes executed evidence.
- [ ] AC91–93: one complete generation is active after crash/conflict, rollback admits only qualified non-revoked history, cache boundaries isolate tenants, and native export survives adapter absence without mutating in-flight identity.

## Failure and edge cases

- Missing cache object, digest mismatch, conflicting version constraints, concurrent expected-generation mismatch, invalid archive member and unavailable rollback target.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no network, hook execution, symlink following, absolute/traversal paths or cross-scope cache reads.
- Reliability: immutable objects plus staged generation directory and atomic pointer replacement.
- Performance: configurable hard bounds on files, bytes and depth.
- Observability: stable error codes and generation metadata/status.
