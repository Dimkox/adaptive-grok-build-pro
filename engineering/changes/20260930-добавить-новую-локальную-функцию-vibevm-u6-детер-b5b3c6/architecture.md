# Architecture — Добавить новую локальную функцию VibeVM U6: детерминированный package graph resolver, lock cache offline replay, bounded unpack projection, boot checks, atomic generations, scoped caches, export fallback и тесты

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Native context contracts exist, but there is no local package graph/cache/generation implementation for U6.

## Proposed behavior

`VibeVMStore` is an optional filesystem adapter. It validates a closed manifest, resolves exact dependency identities, admits immutable archive bytes into a tenant/repository namespace, materializes a bounded data-only projection, and publishes a complete generation through an atomic pointer. It exports canonical native JSON and does not participate in routing, evaluation or authority.

## Components and boundaries

- `vibevm_runtime.py`: resolver, cache, projection, boot block, generation and export boundary.
- `vibevm-generation.v1.schema.json`: frozen output contract.
- No network client, registry, subprocess, hook runner, database or new service.

## Data flow

Caller-supplied manifest + admitted archive bytes -> exact resolver/lock -> integrity/access recheck -> staging projection -> boot/bindings/native export -> atomic generation pointer.

## API and event contracts

Local Python API only. No HTTP/event compatibility impact. Errors use stable `VibeVMError.code` values and never expose partial success.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Package identity is `(name, exact version, digest, origin)`; a digest is integrity, never access authority.
- Cache scope includes tenant and repository and cannot be selected from an arbitrary path.
- Publication preserves immutable history; rollback updates only the active pointer after qualification/revocation checks.

## Risks and mitigations

- Archive abuse: reject non-regular files and enforce path/count/size/depth bounds before publication.
- Crash/concurrency: materialize into a private staging directory and use compare-and-swap generation identity plus atomic replace.
- Vendor lock-in: every generation contains a canonical native export independent of adapter availability.
