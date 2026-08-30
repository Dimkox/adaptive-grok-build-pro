# Security review rerun

- Route: `75aa6daa89b1`
- Reviewed fingerprint: `dcdee2548ec1f47e4620ea1b895421c58b3ad8b6a704464380bf405e4c97a8ec`
- Base: `origin/main` (`1c06299894279a88b881defa3f19b004fa742223`)
- Reviewer: route-selected `security_reviewer` (independent, read-only except this report)
- Previous report: `evidence/security-review.md` (retained unchanged)
- Verdict: **PASS**

## Previous findings

### CLOSED — deployer-only terminal deployment audit and crash reconciliation

- Migration 004 now defines a constrained `SECURITY DEFINER` function, `trust_ci_record_deployment_terminal`, bound to an existing exact `(promotion_id, operation_id)` consumption.
- The function derives actor, key, repository, merged SHA, artifact digest, environment and policy epoch from stored promotion state; callers cannot supply or rewrite those security bindings.
- A partial unique index allows exactly one of `deployment.completed`, `deployment.failed` or `deployment.reconciled` for the consumed operation. Invalid event type, reason/details, absent consumption and concurrent/conflicting terminal writes reject.
- Function execution is revoked from `PUBLIC` and granted only to `trust_ci_deployer`; no generic table insert/update/delete/truncate authority was added.
- The API route `/promotions/{promotion_id}/consume/{operation_id}/terminal` requires the existing constant-time deployer bearer boundary, strict framing, bounded body, canonical UUIDs and the shared consume rate limit.
- Memory, E2E, real-PostgreSQL concurrency, restart/restore and runbook paths now cover the terminal event.

### CLOSED — malformed-request durable-write amplification

- `promotion_limiter.allow()` now runs before header validation, body streaming and JSON/envelope decoding.
- A rejected admission returns `429 rate_limited` with `persist=False`, so traffic beyond the bound does not execute a PostgreSQL rejection-audit transaction.
- The focused regression proves two malformed requests with a limit of one produce one bounded rejection row followed by a non-persisted 429.
- Production still requires the documented reverse-proxy/TLS admission layer; the in-process control now prevents the previously identified parser/audit bypass.

## Security controls revalidated

- `PromotionEnvelopeV1` is immutable and strict; Ed25519 covers every canonical payload field and exact server-owned repository, merged commit, artifact, environment, policy epoch and protected-attestation binding.
- Unknown, revoked, inactive, wrong-actor and wrong-scope keys remain indistinguishable externally; only `promotion:production` can authorize the production target.
- Acceptance atomically enforces current database policy, protected-branch provenance, promotion ID, nonce, payload digest and idempotency uniqueness.
- Consumption is deployer-authenticated, exact-tuple, time/current-policy checked and single-use across replicas; authorization and audit state commit atomically before any external effect.
- The supply-chain verifier is now wired by `Worker.build` from a read-only mounted public key. It verifies the manifest signature, exact merged SHA, policy epoch, immutable image digest and artifact index; the runner rehashes the bundle after validation before signing protected evidence.
- GitHub merge facts originate from HMAC-authenticated deliveries, are independently corroborated by the GitHub App against the protected ref, exact commit and required App-owned check, and never trust a mutable branch tip.
- Runtime PostgreSQL roles remain least-privilege and separated among API, worker, migrator, deployer and backup; `PUBLIC` function execution and schema creation are revoked.
- The checked-in policy has `approval_rules: []`. Development validation, PR and merge need no human signature; the only human signature is the short-lived final `promotion:production` envelope. No human private key was read, requested, generated, submitted or simulated in this review.

## Verification evidence

Command:

`PYTHONPATH=tests .venv/bin/python -m unittest -v test_promotions test_promotion_consumption test_promotion_e2e test_merge_provenance test_key_rotation test_database_roles test_supply_chain test_api test_observability test_policy_transition`

Result: **142 tests passed**.

Additional checks:

- deployment/package migration 004 byte mirror: pass;
- Python compileall for `trust-ci/src` and `trust-ci/tests`: pass;
- `git diff --check`: pass;
- private-key/access-key marker scan of changed product/evidence tree: no material found.

## Findings

None.

## Residual risks and production no-go conditions

- An exact retry of a terminal append is intentionally a conflict rather than an idempotent retrieval. A lost terminal response therefore requires the documented reconciliation/escalation path; it must never trigger a second production effect or a different terminal outcome.
- Trust-store rotation remains externally operated. Use atomic immutable trust-store generations so a revocation cannot race an already-verified in-flight request; this is deployment hardening, not an authorization bypass observed in the reviewed implementation.
- Repository evidence cannot prove the deployed policy epoch, branch-protection App ID/context, reverse-proxy controls, mounted public keys or production database roles. Production remains no-go until those external controls and the exact merged artifact pass their rollout drills.
