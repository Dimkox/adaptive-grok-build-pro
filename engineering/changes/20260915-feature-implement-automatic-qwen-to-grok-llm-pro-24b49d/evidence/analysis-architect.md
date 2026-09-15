# Architecture analysis — Qwen primary / Grok fallback

Route: `24b49d0529c8`. Source baseline: `7b147366a1f9b7e4b59f17e10283cc8ad67ba0c8`. This is design evidence only; the named `scope_and_design_approval` gate remains unresolved. No provider call, credential read, runtime change, or product edit was performed.

## Recommendation

Implement a durable CLI caller over the existing Qwen and Grok Unix services, with a small common orchestration module and an additive backend attempt-status contract. This is the smallest operational entrypoint that can survive primary-service unavailability without putting both provider credentials in one host. If the required entrypoint must itself be a continuously running API, use the same durable orchestration in a separate Unix router instead; this adds API/authentication/concurrency and service-installation scope.

Automatic fallback applies when the primary was definitely not submitted or its durable outcome is an explicitly eligible provider failure. A process/connection loss after dispatch is an unknown outcome: reconcile by read-only status first, then stop if it remains unknown. An unconditional switch after every crash cannot also promise no repeated billed work or duplicate artifacts.

## Three alternatives

| Design | What it covers | Compatibility and cost | Ruling |
| --- | --- | --- | --- |
| Composite provider inside one `LandingApplicationService` | Qwen upstream failure while that host is alive; one downstream artifact build | Needs two secrets in one trust boundary and changes single-profile/evidence handling; cannot answer when the primary host process is down | Insufficient alone for the requested scope |
| Durable CLI caller over existing Unix hosts | Provider failure and primary process down before dispatch; restart/status reconciliation | New local command/config/private state and additive backend attempt records; direct host v1 callers remain available | Recommended minimum |
| Durable shared Unix router | Same failure handling, exposed through a persistent common endpoint | Adds server authentication, tenant propagation, request concurrency, lifecycle, and installation; still needs identical ambiguity rules and backend attempt evidence | Choose only if a shared API endpoint is required now |

No design should implement both an internal provider fallback and an external fallback independently: nested retry policies would make attempt ceilings and billing unclear.

## Current boundaries established from code

- Host configuration selects exactly one profile (`factory/src/adaptive_factory/landing_host_config.py:27`). Each host constructs exactly one provider composition (`landing_server.py:78`). Existing Qwen/Grok keys can remain isolated in those hosts.
- `LandingApplicationService` is bound to one profile digest and rejects another provider's evidence (`landing_service.py:260`, `:392`). The artifact must carry the winning evidence's exact profile (`:469`). An internal wrapper cannot relabel Grok evidence as Qwen.
- `LandingProviderEvidenceV2` has one provider/model/profile and integer usage fields; it has no attempt list or unknown-usage representation (`factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json:6`). Keep retained v1/v2 evidence readable and truthful; create a separate orchestration/attempt contract rather than overloading those fields.
- v1 submission processes normalization and artifact construction before returning HTTP 202 (`api.py:521`, `landing_service.py:326`). A lost submit response is not proof that work was never done.
- Backend idempotency is scoped to one host database, tenant, repository, and job (`landing_sqlite_store.py:178`). The same key on two hosts is not cross-host exclusion.
- Restart recovery explicitly records `provider_outcome_ambiguous` for interrupted normalization and never replays it (`landing_sqlite_store.py:373`). Retain this rule.
- v1 job/result views expose state and digests, without reason codes, provider identity, or usage (`landing_service.py:79`). The current database persists one evidence digest/reason (`landing_sqlite_store.py:35`); this cannot support a truthful two-attempt ledger alone.
- Qwen Omni accepts audio, DOCX, image, PDF, and text; Grok Vision accepts DOCX, image, PDF, and text (`landing_http.py:50`). Fallback must respect the common supported media. Audio cannot silently switch or be transcoded by this change.

## Minimal durable caller design

1. A new command accepts an explicit request key, the already-supported target/source identity, and bounded input. It uses a closed operator configuration pinning Qwen then Grok socket/profile identities and a versioned fallback policy. It uses scoped Unix-service actor tokens, never provider API keys.
2. Persist the logical request, immutable input digest, target identity, actor/repository binding, policy digest, and a private bounded input spool before any submission. Reusing the request key with different bytes/configuration is a conflict. Keep the spool through fallback/reconciliation; apply bounded retention and deletion after terminal completion. Backend services currently purge their own input after processing, so they cannot serve as the caller's retry spool.
3. Maintain at most one Qwen attempt and one Grok attempt per logical request. Derive stable child job keys and persist the selected backend, attempt identity, request digest, and dispatch intent before sending. Enforce a single local writer/claim and a total elapsed-time ceiling. Do not parallelize or hedge providers.
4. A fresh Unix connect failure that proves no request bytes were sent can be recorded as `not_submitted`, allowing Grok. A health check alone does not prove submission safety. After dispatch starts, write/read timeout, disconnection, process death, or caller crash become `outcome_unknown` until the same child job is reconciled through read-only status. A transient 404 is not sufficient proof of no pending submission.
5. A durable backend terminal record with an eligible provider-failure category allows the one Grok attempt, provided the input/profile and remaining limits permit it. Never fallback after normalization has succeeded and local rendering, evaluation, retention, or publication has failed. Never fallback after a selected artifact exists.
6. Persist the chosen backend, its unmodified artifact/evidence identities, and both attempt records before reporting the final result. Replaying a terminal caller request returns this result without another POST. The caller selects/references the existing backend artifact; it neither rebuilds nor publishes it.
7. `status`/`resume` primarily reconcile durable records. They do not clear backend locks, remove failed rows, create fresh job IDs to evade idempotency, or interpret unknown provider usage as zero.

The CLI must be installed/documented as the normal generation entrypoint. Direct calls to the old Qwen socket cannot acquire fallback automatically merely because this command exists. Router-service adoption would similarly require callers to use its socket.

## Failure taxonomy and accounting prerequisite (#87)

The parent supplied verified issue #87 scope: a closed safe vocabulary distinguishing authentication, provider unavailable, stream incomplete, invalid response, and draft decode, with no raw response bodies. Source confirms that non-200 responses currently collapse to `executor_http` (`landing_live_executors.py:266`), and the normalizer collapses provider/contract errors to `http_outcome_unusable` (`landing_http.py:262`). Failed evidence is then constructed with zero units (`:287`), including cases where the provider may have returned billed output.

Implement and persist a bounded per-attempt receipt before enabling fallback. It must distinguish failure origin, dispatch certainty, finality, phase, exact provider/profile, safe failure category, and usage certainty. Preserve known usage even if draft decoding fails; represent missing usage as unknown, not zero. Do not retain secrets or arbitrary provider error bodies. Separate upstream authentication failure from caller authentication/authorization rejection.

Policy should explicitly allow only selected terminal provider failures and known no-submit unavailability. Source/tenant/authentication-boundary mismatch, unsupported media, content-policy refusal/moderation, invalid source, artifact/evaluation/storage failures, and interrupted/ambiguous outcomes must not trigger a broad fallback. Incomplete streams require a durable terminal record proving no artifact path continued; their usage may remain unknown. Unknown usage must stay visible even when an eligible, definitely terminated provider failure permits the separately budgeted Grok attempt.

Two distinct, bounded attempts can both incur legitimate charges. The enforceable guarantee is no automatic repeat of the same submitted attempt and no double counting; exactly-once external billing across providers cannot be guaranteed after an ambiguous failure. Record known totals plus any unknown exposure instead of advertising a complete zero/total cost.

Backend attempt persistence requires an additive versioned storage/API change, with migration/recovery review. Do not add fields silently to the closed v1 job/result schemas or silently alter the existing single-provider evidence contract. A new attempt-status endpoint can support both the CLI and a future router. Preserve the current direct-host response shapes and `live_url=null`.

## Acceptance and approval decisions

- Prove offline: primary success calls only Qwen; connect refusal before submission calls Grok once; eligible durable Qwen failure calls Grok once; both fail terminally; duplicate/concurrent caller requests cannot multiply calls.
- Crash at each dispatch/receipt/result boundary; resume must read the same backend identity, recover a completed artifact, and refuse automatic replay/fallback when outcome remains ambiguous. Exercise a child Unix host killed before dispatch and after request acceptance.
- Prove no fallback for source/authorization/policy/media rejection, renderer/evaluator/retention failure, or any already-created artifact. Cover unsupported audio explicitly.
- Verify truthful failed-attempt usage, unknown usage, preserved winner evidence, stable idempotency conflicts, total attempt/time ceilings, token/secret redaction, and retained v1/v2 compatibility.
- Scope approval should choose CLI versus persistent Unix endpoint; acknowledge automatic fallback before dispatch versus observation-only handling after ambiguous dispatch; and confirm audio remains outside Grok fallback capability. No general repository-coding runtime, M4/M5 worker, release publication, deployment, or production authority is implied.

Rollout after normal source delivery is additive: migrate backend receipt storage, install the chosen caller, and route new requests through it under separately authorized operational configuration. Rollback directs new requests to the existing explicit provider entrypoints while preserving caller/attempt state for reconciliation; never replay pending requests during rollback.
