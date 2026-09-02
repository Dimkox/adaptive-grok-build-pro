# Architecture — M9 Staged Delivery and Recovery

> Typed authority: [`change-spec.yaml`](change-spec.yaml). The complete field contract is the [approved design](../../../docs/superpowers/specs/2026-09-02-m9-staged-delivery-recovery-design.md).

## Current behavior

M9 Task 1 now provides pure local closed contracts and canonical digests. This branch starts from provisional M4 source `9fe779ab9f90719201acfd01160d3452658ff075`; it does not contain an accepted M5→M8 predecessor chain, accepted M8 profile/cohort, signed delivery input, nonproduction environment or recovery proof.

## Proposed behavior

Tasks 1–4 M9 source is a pure local deterministic library. It accepts closed immutable records whose authority was verified elsewhere, evaluates one complete observation set, and advances a dry-run state machine only through `preview → staging → bounded_canary → production`. `production` is not executable: it always yields `needs_human`.

## Components and boundaries

- `contracts.py`: closed frozen V1 records, canonical validation and digesting; no signature implementation.
- `evaluator.py`: pure completeness/freshness/consistency/threshold evaluation for five fixed metric families.
- `recovery.py`: pure selection of `halt`, `decrease_exposure` or `restore_previous`; authority can only narrow.
- `controller.py`: append-only dry-run transitions and evidence-chain validation.
- `fake_environment.py`: bounded in-memory adapter for tests; it records requested dry-run effects and has no network, provider, process or production method.
- JSON Schemas: machine-readable exact record contracts created with source, then registered in the architecture model.

There is no service, database, queue, HTTP API, webhook, outbox, runtime daemon, credential broker or external adapter.

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

M9 never creates or verifies cryptographic authority. An opaque authority reference carries only envelope digest, external verifier ID, verification/expiry timestamps, scope and exact resource digest. Signature bytes, certificates, private/public keys, credentials and untrusted envelope bodies are absent. Presence is not enough: every reference must be unexpired at `evaluation_time`, match the expected closed scope, and bind the exact canonical resource digest.

## State and failure semantics

Normal dry-run states are `pending`, `preview`, `staging`, `bounded_canary`, `needs_human`, `halted` and `restored`. Stage order cannot skip or reverse except through a recovery terminal. Every observation binds promotion, artifact, environment, exposure and policy digests. Missing, stale, duplicate, contradictory, nonfinite or threshold-breaching data yields a stable deny reason; input order cannot change the decision.

Automatic recovery is pre-authorized in `DeliveryPromotionV1`. It can halt, choose an earlier exposure step in the same stage, or restore the exact `previous_signed_artifact`. It cannot advance, increase exposure, introduce an artifact, modify resource/environment/policy bindings, or reach production.

## Observability and retention

At most 128 evidence records exist in one dry-run chain. Audit stores closed IDs, SHA-256 digests, RFC3339 UTC timestamps, exposure basis points, numeric aggregates and reason codes. Metrics use fixed labels: stage, decision and reason. No task body, prompt, reasoning, source, PII, secret, credential, authority body or environment response body is accepted or emitted.

## Governance context

Canonical governance and Trust CI remain separate authority. No current active governance rule is claimed. Architecture, security and release approval scopes remain required before later implementation can become ready. External signed inputs and human production approval are never replaceable by repository receipts.

## Decisions

- Choose a pure library plus fake adapter, not a deployment service, because the current scope must prove semantics without external capability.
- Choose one complete observation snapshot per decision, not streaming updates, so missing/stale/contradictory handling is deterministic and replayable.
- Keep the authority envelope opaque, not a local signing/verifying abstraction, so repository code cannot simulate external approval.
- Encode exposure in integer basis points and timestamps in UTC seconds to avoid float ordering and timezone ambiguity.

## Risks and mitigations

- False authority from examples: no artifact, signature, cohort or environment fixture is created in this checkpoint; the ledger remains blocked.
- Accidental forward recovery: recovery actions are a closed enum and validated against the previous exposure index and prior artifact binding.
- Stale metrics: each metric has captured time, maximum age and evaluation deadline; any violation denies.
- Information leakage: contracts reject free-form messages and bodies; evidence is bounded and redacted by construction.
- Calendar pressure: the deadline never waives predecessor, external signature, environment, recovery, verification, review or production gates.
