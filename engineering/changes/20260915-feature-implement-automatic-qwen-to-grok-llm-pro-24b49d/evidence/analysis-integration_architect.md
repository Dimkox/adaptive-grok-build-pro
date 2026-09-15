# Integration analysis — durable Qwen/Grok CLI caller

Route `24b49d0529c8`; design only. Named `scope_and_design_approval` remains pending.
No product edits, model calls, credential reads or service operations were performed.

## Recommendation

Use one durable CLI caller over the existing Unix hosts; no third service or nested backend failover.
Implement classifier #87 and durable attempt receipts before enabling automatic fallback.
Existing v1 submit/get/result contracts must remain byte/shape compatible.

## Findings and required bindings

- v1 submission finishes processing before HTTP 202 (`api.py:521`, `landing_service.py:326`). A lost response can hide completed/billed work.
- v1 job/result omit reasons, profile and usage (`landing_service.py:79`). State `needs_human` alone cannot select fallback safely.
- Backend rows retain reason and evidence digest only; failed provider evidence/usage cannot be reconstructed (`landing_sqlite_store.py:35`, `landing_service.py:399`).
- Tenant is authenticated `actor.actor_id`, not a caller-supplied tenant header (`api.py:502`, `landing_service.py:294`). Require the same logical actor/repository on both hosts, or an explicit immutable actor mapping; never infer identity from token filenames or socket names.
- Child input digests will differ: `LandingInputV1` includes job ID, tenant, quarantine identity, received time and expiry (`landing_contracts.py:249`). Do not require Qwen/Grok input-digest equality or relabel the winning artifact.
- Persist a separate parent request digest over logical actor, repository/base SHA/tree, media type, byte length/content SHA256, request key and policy/config digest. Persist each backend's actual child input digest under its deterministic child key.
- Child reconciliation must compare actor/repository, content hash/length/media, exact source, backend profile and child ID; a matching job ID or HTTP 200 alone is insufficient.
- Backend service identity is currently unavailable in the job view. A swapped/misconfigured socket could process the wrong profile before discovery; add authenticated profile/capability discovery before POST.
- Different profiles support different media. Reject an ineligible fallback before transfer; Qwen Omni audio cannot be sent to Grok Vision.

## Minimal additive contracts/endpoints

1. Closed local `LandingFailoverRequestV1` and `LandingFailoverRecordV1`: parent digest, actor/repository, ordered pinned backend identities, policy digest, bounded spool reference/expiry, child intents/receipts, selected result and unknown accounting exposure.
2. Authenticated `GET /v2/landing-backend`: schema/profile/provider/model identity, supported media, limits, receipt protocol version and authenticated actor binding. Pin its facts in caller config; incompatible/legacy live hosts stop before POST rather than downgrade silently.
3. Authenticated `GET /v2/landing-jobs/{job_id}/attempt`, with the existing repository header: immutable child/source/profile binding, safe failure origin/category, phase/finality, dispatch/usage certainty, known usage or explicit unknowns, receipt digest, artifact/evidence identities and monotonic revision.
4. Keep `POST /v1/landing-inputs` and its headers unchanged. Parent-to-child association can remain in the durable caller record and deterministic child ID; do not overload X-Correlation-ID as idempotency or authority.
5. Add a versioned backend receipt table/column with explicit migration and strict schema validation. Commit provider outcome/known usage before proceeding to artifact work; advance receipt phases consistently with job transitions. Old rows must decode as historical receipt unavailable, never as zero-cost eligible failure.

## Dispatch and recovery rules

- Caller owns one private, owner-validated SQLite journal outside source/backend roots, with process lock, transactional claims and unique parent/backend child identities. Persist/flush dispatch intent before network I/O; concurrent invocations cannot race Qwen and Grok.
- Primary stopped before Unix connection establishment: record definitely-not-submitted and select Grok. A health check failure alone is not proof of POST outcome.
- Once a POST might have been sent, reconcile only the same child ID. Timeout, disconnect, interrupted receipt or transient 404 never authorizes another POST or Grok. Terminal unknown remains needs_human.
- Fallback requires an authoritative current-job receipt: terminal provider-phase failure from the #87 allowlist AND explicit artifact_absent, committed consistently with job finalization. A normalization-only failure receipt cannot authorize fallback while local processing might continue.
- Caller authorization, source/tenant/profile mismatch, policy/media rejection, renderer/evaluator/storage failure and existing artifact prohibit fallback.
- A definite terminal upstream failure may have unknown billing; preserve that exposure alongside Grok's usage. Do not synthesize complete totals or recompute pricing.
- Caller retains one bounded private input spool through reconciliation/fallback, then deletes under explicit retention rules. Backend input is purged after processing (`landing_service.py:336`) and cannot serve as fallback input storage.
- Winner is the backend's unchanged artifact/evidence reference, with backend locator; v1 result has no artifact download path. CLI success must not imply files were copied locally or published.
- Rollback preserves both ledgers and unresolved intents; old binaries may reject migrated strict schemas, so document reader compatibility or offline backup restoration rather than assuming downgrade works.

## Focused design acceptance tests

- Real Unix transport: primary killed before connect selects Grok exactly once; killed after request acceptance never causes replay or unproven fallback.
- Crash at intent/send/provider-receipt/artifact/parent-result boundaries; recover a completed winner without a second POST.
- Cross-actor/repository/job collisions, changed bytes/base/profile/config on reused parent key, swapped sockets and unsupported receipt versions fail closed.
- Distinct timestamped child digests map to one parent content identity without modifying either backend evidence.
- Eligible classified failure versus local/policy/authorization failures; known failed usage survives, missing usage remains unknown, no fallback after artifact creation.
- Legacy v1 responses and retained provider evidence v1/v2 remain readable; old rows, schema migration/restart and rollback compatibility are explicit.
- Duplicate/concurrent CLI requests, spool expiry/cancel, total deadline exhaustion and incompatible audio cannot multiply attempts or leak input.
