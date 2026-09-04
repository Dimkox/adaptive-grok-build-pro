# Architecture — M9 staged delivery on exact M8 f53275d

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Exact M8 provides a pure earned-autonomy recommendation layer bound to actual M7 producer records. Durable acceptance/currentness and activation remain unavailable, and no delivery runtime exists.

## Proposed behavior

Add a separate pure-Python M9 package. It consumes recomputed actual-M8 evidence, evaluates one bounded staged step, applies only dry-run effects through an exact in-memory adapter, records an immutable chain, and selects narrowing recovery. It introduces no operational integration.

## Components and boundaries

- `contracts.py`: closed signed-artifact, exposure, promotion, observation, decision, recovery, and evidence records.
- `m8_boundary.py`: thin imports and reconstruction over `adaptive_factory.autonomy`; it owns only the M9 handoff envelope and fail-closed gate projection.
- `evaluator.py`: pure deterministic one-step decision function.
- `recovery.py`: pure least-authority recovery selection.
- `fake_environment.py`: sealed, locked, in-memory dry-run effect sink with no external capability.
- `controller.py`: validates chain continuity and adapter identity, serializes evaluate/apply/append, rechecks authority expiry, and caps state at 128 records.
- No database, queue, HTTP API, provider client, credential, subprocess, filesystem mutation, or operational environment adapter is added.

## Data flow

1. Real M8 records are reconstructed from the handoff payload; their nested values and digests are recomputed and fail closed.
2. Signed artifact and promotion records bind the exact repository, policy/holdout/runner, authority resource, environment, exposure plan, and validity window.
3. Bounded observations plus an empty trusted local chain enter deterministic evaluation; at most one pre-authorized non-production step is selected.
4. The controller holds one lock across evaluation, optional narrowing recovery, fake effect application, and immutable evidence append.
5. Production or the last canary yields `needs_human`; stale or contradictory facts deny without an external effect.

## API and event contracts

This phase adds an internal typed Python contract surface only. It publishes no HTTP operation or event and changes no existing contract meaning.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: closed contracts, least authority, deterministic evidence, dry-run isolation, human production authority, and exact-head binding.
- Applicable canonical example IDs/versions: M9 version-1 records over actual integrated M8 version-1 producer objects.
- Open or overdue debt IDs: none created; real signed evidence, trusted persistence, operational adapter, and acceptance remain explicitly deferred.
- Expected governance handoff or receipt impact: exact-head full verification and five route-selected reviews remain later finalization work.

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Canonical M9 source is imported as file snapshots, but the temporary duplicate M8 model is replaced by a thin bridge to actual M8 classes.
- Only an exact `FakeEnvironmentAdapter` instance is accepted; subclasses, monkeypatching, replacement, and production targets fail closed.
- A local chain may start only empty. Import of prior evidence needs a future trusted witness and cannot be self-asserted.
- Final canary and production remain human-only even when every threshold passes.

## Risks and mitigations

- Producer-authority duplication: eliminated by importing and reparsing actual M8 types and rejecting caller-derived authority fields.
- Concurrent duplicate effect: one lock spans decision, at-most-once fake apply, and evidence append.
- Recovery escalation: fixed action shapes only halt, decrement one authorized step, or restore the exact bound previous artifact.
- Source mistaken for deployment capability: no operational adapter or I/O exists, fake effects are typed and in-memory, and documentation makes no delivery claim.
