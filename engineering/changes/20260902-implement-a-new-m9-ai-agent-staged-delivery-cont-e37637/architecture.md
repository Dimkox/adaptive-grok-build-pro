# Architecture — M9 Staged Delivery and Recovery

> Typed authority: [`change-spec.yaml`](change-spec.yaml). The complete field contract is the [approved design](../../../docs/superpowers/specs/2026-09-02-m9-staged-delivery-recovery-design.md).

## Current behavior

M9 now has a source-only successor correction pinned to provisional M8 producer `2cee9b93c161b6c76f4fee877e6d19eacee5a271`. It still starts from provisional M4 source `9fe779ab9f90719201acfd01160d3452658ff075` rather than M8 ancestry, so the temporary boundary is digest-compatible transport, not accepted/current M8 authority. No accepted M5→M8 chain, durable M8 currentness, signed delivery input, nonproduction environment or recovery proof exists.

The executable architecture owns current provisional `delivery` source/tests under `NODE-STAGED-DELIVERY-SOURCE`, a no-network local-preflight component whose only edge is filesystem verification by `NODE-LOCAL-VERIFIER`. This is repository inventory and separation evidence only; it creates no acceptance, durable currentness, runtime or activation authority.

## Proposed behavior

Tasks 1–4 M9 source is a pure local deterministic library. It accepts closed immutable records whose authority was verified elsewhere, evaluates one complete observation set, and advances a dry-run state machine only through `preview → staging → bounded_canary → production`. `production` is not executable: it always yields `needs_human`.

## Components and boundaries

- `contracts.py`: closed frozen V1 records, canonical validation and digesting; no signature implementation.
- `m8_boundary.py`: temporary typed tuple/cohort/profile/recommendation transport. It recomputes M8 domain-separated tuple/cohort/profile/recommendation digests, task→bundle→outcome links and profile aggregates, but deliberately does not duplicate the complete M7/M8 producer implementation.
- `evaluator.py`: pure completeness/freshness/consistency/threshold evaluation for five fixed metric families.
- `recovery.py`: pure selection of `halt`, `decrease_exposure` or `restore_previous`; authority can only narrow.
- `controller.py`: lock-serialized dry-run evaluate/apply/append transitions, internal evidence-chain validation and fail-closed non-empty import.
- `fake_environment.py`: exact bounded in-memory adapter for tests; its private immutable effect tuple is updated only by the reviewed original implementation and it has no network, provider, process or production method.
- JSON Schemas: machine-readable exact record contracts created with source, then registered in the architecture model.

There is no service, database, queue, HTTP API, webhook, outbox, runtime daemon, credential broker or external adapter.

The old two opaque M8 digests are removed from the unaccepted V1 promotion. `M8DeliveryHandoffV1` binds repository, task/change class, M7 cohort key, provider mapping, agent, validator, provider, model, prompt, policy, runner, holdout, authority, L2 ceiling, complete cohort body, recomputed profile and recommendation. Promotion resource authority then binds that complete handoff together with the signed artifact and recovery resources.

## Data flow

```text
externally verified opaque references + complete aggregate observations
  -> closed contract validation and exact-binding comparison
  -> deterministic metric decision
  -> recovery authority subset check
  -> dry-run in-memory transition
  -> bounded redacted append-only DeliveryEvidenceV1
  -> production boundary returns needs_human
```

## Trust boundary

M9 never creates or verifies cryptographic authority. An opaque authority reference carries only envelope digest, external verifier ID, verification/expiry timestamps, scope and exact resource digest. Signature bytes, certificates, private/public keys, credentials and untrusted envelope bodies are absent. Presence is not enough: every reference must be unexpired at `evaluation_time`, match the expected closed scope, and bind the exact canonical resource digest. Before recording, the controller also rejects expired promotion/current-artifact authority and, for restore, expired prior-artifact authority; `recorded_at` remains caller-supplied and a trusted Task 5 clock is required for activation.

The temporary M8 handoff has code-owned status `blocked_pending_durable_m8_lookup`, `durable_currentness_available=False` and `EXTERNAL_ACTION_AUTHORIZED=False`; there is no caller override. A typed synthetic handoff may exercise Tasks 1–4 source conformance and the exact fake adapter only. It cannot enter any operational path because none exists; Task 5 must use server-derived durable acceptance/currentness, and factual M8 restack must delete this adapter in favor of direct producer imports.

## State and failure semantics

Normal dry-run states are `pending`, `preview`, `staging`, `bounded_canary`, `needs_human`, `halted` and `restored`. Stage order cannot skip or reverse except through a recovery terminal. Every observation binds promotion, artifact, environment, exposure and policy digests. Missing, stale, duplicate, contradictory, nonfinite or threshold-breaching data yields a stable deny reason; input order cannot change the decision.

Automatic recovery is pre-authorized in `DeliveryPromotionV1`. It can halt, choose an earlier exposure step in the same stage, or restore the exact `previous_signed_artifact`. Every recovery evidence record requires at least one non-recovery denial reason, forbids `thresholds_passed`, and carries exactly one matching recovery code. It cannot advance, increase exposure, introduce an artifact, modify resource/environment/policy bindings, or reach production.

The in-process controller has no restart contract in Tasks 1–4. Every non-empty prior chain fails closed because record digests alone do not witness the observations, decision or recovery bodies. Task 5 must introduce a trusted checkpoint or complete independently witnessed inputs before import/restart can be enabled. Private name-mangled slots, immutable tuples and class-surface checks close ordinary mutation paths, but are not claimed as an OS sandbox or protection against arbitrary interpreter compromise.

## Observability and retention

At most 128 observations are indexed from a declared bounded sequence before evaluation; generators and non-sequences are rejected without consumption. At most 128 evidence records and 128 fake effects exist in their respective in-process tuples. Audit stores closed IDs, SHA-256 digests, RFC3339 UTC timestamps, exposure basis points, numeric aggregates and reason codes. Metrics use fixed labels: stage, decision and reason. No task body, prompt, reasoning, source, PII, secret, credential, authority body or environment response body is accepted or emitted.

## Governance context

Canonical governance and Trust CI remain separate authority. No current active governance rule is claimed. Architecture, security and release approval scopes remain required before later implementation can become ready. External signed inputs and human production approval are never replaceable by repository receipts.

## Decisions

- Choose a pure library plus fake adapter, not a deployment service, because the current scope must prove semantics without external capability.
- Choose one complete observation snapshot per decision, not streaming updates, so missing/stale/contradictory handling is deterministic and replayable.
- Keep the authority envelope opaque, not a local signing/verifying abstraction, so repository code cannot simulate external approval.
- Recompute the profile from cohort tasks/outcomes at the boundary instead of trusting a typed profile body; a caller-rehashed aggregate is still caller data.
- Encode exposure in integer basis points and timestamps in UTC seconds to avoid float ordering and timezone ambiguity.

## Risks and mitigations

- False authority from examples: synthetic typed cohort/artifact/environment identities exercise only local conformance; their boundary reports durable currentness unavailable and the ledger remains blocked.
- Accidental forward recovery: recovery actions are a closed enum and validated against the previous exposure index and prior artifact binding.
- Stale metrics: each metric has captured time, maximum age and evaluation deadline; any violation denies.
- Information leakage: contracts reject free-form messages and bodies; evidence is bounded and redacted by construction.
- Calendar pressure: the deadline never waives predecessor, external signature, environment, recovery, verification, review or production gates.
