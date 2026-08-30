# Security review

- Route: `75aa6daa89b1`
- Base: `origin/main` (`1c06299894279a88b881defa3f19b004fa742223`)
- Scope: final working-tree diff for production promotion authorization, provenance, PostgreSQL roles, replay/idempotency, audit, and the production-only human gate
- Reviewer: route-selected `security_reviewer` (independent, read-only except this report)
- Verdict: **FAIL**

## Findings

### MEDIUM — the deployer cannot append the required terminal deployment audit event

- Files/lines: `trust-ci/sql/004_production_promotions.sql:134-160`, `trust-ci/sql/004_production_promotions.sql:782-795`, `trust-ci/sql/004_production_promotions.sql:945-947`; no corresponding method or endpoint exists in `trust-ci/src/adaptive_trust_ci/store.py` or `trust-ci/src/adaptive_trust_ci/api.py`.
- Evidence: the event contract and metrics recognize `deployment.completed`, `deployment.failed`, and `deployment.reconciled`, and the runbook requires the authenticated deployer to append one. Migration 004 grants the deployer only consume, consume-reconciliation lookup, and event-list functions. The deployer has no table insert privilege and there is no constrained `SECURITY DEFINER` terminal-transition function, store method, or authenticated API route. Consequently every consumption remains `consumed_without_terminal`, and crash reconciliation cannot produce the append-only evidence required by AC-006.
- Security impact: post-consume production outcome is permanently unauditable. Operators cannot distinguish completed, failed, and reconciled side effects in the authoritative ledger, weakening incident response and making the documented safe recovery path impossible.
- Required repair: add an append-only, deployer-only terminal transition bound to the existing `(promotion_id, operation_id)` consumption, constrain event type/outcome/reason/details, reject conflicting or duplicate terminal outcomes, expose it through the authenticated deployer boundary, and add negative/concurrency/PostgreSQL tests. Do not grant generic table writes.

### MEDIUM — malformed unauthenticated requests bypass the in-process rate limit but still force durable audit writes

- Files/lines: `trust-ci/src/adaptive_trust_ci/api.py:254-271`, `trust-ci/src/adaptive_trust_ci/api.py:353-365`, `trust-ci/src/adaptive_trust_ci/api.py:504-518`.
- Evidence: `promotion_limiter.allow()` executes only after header validation, full body read, and strict envelope decoding. Every earlier `malformed_envelope`/`unsupported_contract` rejection reaches the common exception handler and invokes `record_promotion_rejection`. `/promotions` intentionally has no bearer credential, so an untrusted caller can submit unlimited malformed requests that never enter the limiter yet create one PostgreSQL transaction and append-only row per request.
- Security impact: unauthenticated write amplification and unbounded audit-table growth can exhaust database capacity or degrade the authorization service. The checked-in service binds to localhost, but the production contract explicitly expects exposure through a reverse proxy; no repository-enforced upstream rate-limit configuration is present.
- Required repair: enforce a bounded admission control before request parsing and before any per-request durable write, while retaining secret-free aggregate rejection telemetry. If individual malformed-request audit is mandatory, make upstream rate limiting an explicit verified deployment prerequisite and ensure rate-limited traffic cannot itself create unbounded audit writes.

## Controls verified

- Promotion signatures cover a strict canonical payload and exact repository, merged commit, artifact digest, environment, policy epoch, and protected-attestation identifier.
- Unknown, inactive, revoked, wrong-actor, and wrong-scope keys fail with the same public signature error; production authorization requires `promotion:production`.
- Nonce, promotion identity, payload digest, idempotency key, promotion consumption, and operation ID are durably unique; acceptance and consume events share their authorization transactions.
- Consume rechecks current policy, expiry, exact provenance tuple, and immutable supply-chain bytes before the first external side effect; outages and the kill switch deny.
- PostgreSQL runtime roles are separated; `PUBLIC` execution is revoked, deployer has no generic table mutation, and no runtime role receives delete/truncate authority.
- Merge provenance starts from an HMAC-authenticated webhook, is independently corroborated through the GitHub App, validates the required exact App-owned check, and fetches the exact merged object rather than a mutable ref.
- The example validation policy has `approval_rules: []`; the sole human signature is scoped to the final `production` promotion. No human private key was read, requested, generated, submitted, or simulated during this review.

## Verification evidence

`PYTHONPATH=tests .venv/bin/python -m unittest -v test_promotions test_promotion_consumption test_promotion_e2e test_merge_provenance test_key_rotation test_database_roles test_supply_chain`

Result: 70 tests passed. The suite validates the existing negative authorization controls but does not cover either finding above.

## Residual risks

- Trust-store replacement is not fingerprinted across signature verification and database acceptance. A key revoked by a concurrent mounted-file replacement can still win a narrow already-verified request race; production rollout should use atomic immutable trust-store generations, and a future hardening change should bind acceptance to a stable trust-store epoch.
- Repository policy cannot prove the deployed policy, branch protection, GitHub App identity, reverse-proxy controls, or external human trust store. Production remains no-go until those externally owned controls are verified against the exact deployed policy epoch.
