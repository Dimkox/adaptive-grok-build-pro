# Final security review

- Route: `75aa6daa89b1`
- Reviewed fingerprint: `c00baee9fdd3ebad087dcb29539bb36ea24a205b18cce8d8d6706bdbdcf8a5ba`
- Base: `origin/main` (`1c06299894279a88b881defa3f19b004fa742223`)
- Reviewer: route-selected `security_reviewer` (independent, read-only except this report)
- Prior reports retained: `security-review.md`, `security-review-rerun.md`
- Verdict: **PASS**

## Findings

None.

## Prior findings revalidated

- The unauthenticated promotion admission limiter executes before header/body/JSON parsing. Requests beyond the bound return non-persisted `429`, so malformed traffic cannot bypass admission and amplify durable audit writes.
- Terminal deployment evidence remains deployer-authenticated, append-only, bound to an exact existing consumption, and restricted to one constrained completed/failed/reconciled result. `PUBLIC` has no execution privilege and the deployer has no generic table mutation authority.
- Acceptance, replay rejection, consume-once, terminal uniqueness, active-policy checks, exact provenance joins, artifact verification and audit transitions remain atomic or fail closed.

## Round 3 security review

### Durable merge-fact retry and requeue

- Retry is lease-owner, claim-ID and attempt bound. PostgreSQL and memory implementations clear ownership, apply bounded exponential backoff, cap attempts at 20 and prevent hot-loop claims through `next_attempt_at`.
- Independently corroborated provenance mismatches are classified permanent and transition directly to `dead`; they cannot be reset by reconciliation.
- Reconciliation can requeue only an already-known fact whose terminal error is explicitly `attempts-exhausted` or `retry-exhausted`. It cannot requeue completed, live, unknown or permanent-denial facts.
- Requeue execution is revoked from `PUBLIC` and granted only to the worker role. Resetting an exhausted attempt does not create promotion authority: GitHub App corroboration, exact-SHA validation, signed supply-chain verification and protected evidence must all pass again.
- Durable watermarks advance only after a bounded complete GitHub result and successful fact persistence/corroboration; incomplete pagination does not silently skip merges.

### GitHub policy-epoch cutover and rollback

- The cutover reads and verifies the exact old `(context, app_id)`, installs exact `old+new`, reads it back, then installs exact `new` and reads it back. There is no write that removes all required checks.
- Any failure attempts a verified rollback to `old+new`. A rollback-verification failure is surfaced as a hard error rather than claimed successful.
- Required status checks remain strict and App-ID bound; branch protection enforces administrators, pull requests, conversation resolution and linear history, while force pushes and deletion remain disabled.
- The long-lived GitHub App retains reduced permissions; branch-protection mutation requires a separate temporary administration token and is explicitly an external operator action. Repository tests use a fake transport and do not mutate GitHub.
- The disposable cutover drill proves that `needs_approval` cannot satisfy the new check and only exact automated success permits merge.

## Full trust-boundary validation

- Promotion authorization is a strict canonical Ed25519 envelope bound to the exact repository, merged commit SHA, immutable artifact SHA-256, production environment, full policy epoch and protected-branch attestation ID.
- Unknown, inactive, revoked, wrong-actor and wrong-scope keys share one public failure; only `promotion:production` is accepted for production.
- Merge provenance starts with an HMAC-authenticated delivery, is independently corroborated through GitHub App APIs and the protected branch rule, and checks out the exact merged commit instead of a mutable ref.
- The worker verifies the signed supply-chain manifest with a read-only mounted public key, rechecks policy/image/artifact digests and rehashes the bundle after exact-SHA validation before signing protected evidence.
- PostgreSQL roles remain separated among API, worker, migrator, deployer and backup. Runtime roles receive constrained functions, not broad DML; no delete/truncate authority or schema creation leaks to them.
- API/worker/runner/consumer components do not hold the human promotion private key or production deployment credentials. Promotion consumption records authorization/audit state before the separate external effect.
- The checked-in automated policy has `approval_rules: []`. Legacy PR approval compatibility paths cannot become required under this epoch. Development validation, PR delivery and merge have no human signature or chat gate; the one human signature is the short-lived final `promotion:production` envelope immediately before production consumption/deploy.
- No human private key was read, requested, generated, submitted or simulated during this review.

## Verification evidence

`PYTHONPATH=tests .venv/bin/python -m unittest discover -v -s tests -p 'test_*.py'`

Result: **326 tests passed, 32 PostgreSQL integration tests skipped because no test database URL was configured in this reviewer process**.

Additional evidence:

- `bash trust-ci/scripts/policy-transition-drill.sh`: PASS;
- deployment/package migration 004 byte mirror: PASS;
- Python compileall for `trust-ci/src` and `trust-ci/tests`: PASS;
- `git diff --check`: PASS.

The skipped real-PostgreSQL suite remains a mandatory release input and must be taken from fingerprint-bound verification evidence; this review does not replace it.

## Residual risks and production no-go conditions

- Exhausted non-provenance failures may be requeued by reconciliation. Persistent infrastructure or signed-bundle faults therefore require alerting and operator repair; they remain fail closed and cannot create evidence or production authority.
- Cutover rollback to `old+new` can intentionally block merges if one epoch is unavailable. This is the safe failure mode; operators must repair an epoch rather than remove checks or submit a legacy human approval.
- Repository evidence cannot prove the deployed policy/holdout, live branch-protection App identity, mounted keys, PostgreSQL roles, reverse proxy, or exact merged artifact. Production remains no-go until the external Trust CI check and rollout/restore/cutover drills pass for the exact deployed epoch and commit.
- Trust-store rotation must use an atomic immutable generation to minimize an in-flight revocation race. This is deployment hardening; no authorization bypass was found in the reviewed diff.
