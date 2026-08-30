# Production promotion

## Invariant

Development validation, pull-request delivery and merge are automatic and require no human signature or chat approval. Exactly one human signature exists in the workflow: a short-lived `promotion:production` envelope created at final production go/no-go for one exact merged commit, immutable artifact digest, target environment, active policy epoch and protected-branch attestation.

Repository code, agents, API and workers never read, generate, request, submit or simulate the human private key or signature. `scripts/grok_approve.py` and legacy PR approval envelopes are not production authority.

## Automated prerequisites

Before asking the human to start the ceremony, automation must have recorded all of the following on one immutable release candidate:

- the automated-only policy epoch is deployed with `approval_rules: []` and its exact App-owned check is required by branch protection;
- the integration PR passed that check on its exact head and was merged through protected automation;
- GitHub App corroboration identifies the actual protected-branch merged commit;
- exact-SHA validation and the external holdout passed for that merged commit;
- the immutable artifact bytes and SHA-256 are present in a passed protected-branch attestation;
- migration, restart/restore, replay/concurrency, role, negative E2E, rollback and independent review evidence pass on the final fingerprint;
- promotion acceptance and consumption are ready, the database active policy matches the service policy, and the production kill switch is off.

If the deployed policy still returns `needs_approval`, stop: the automated-only control-plane cutover is incomplete. Do not request a PR signature. Repository code cannot repair deployed policy or branch protection.

The external cutover operator must use `branch-protect --previous-context ... --previous-app-id ...`. Capture the initial GET, exact `old+new` PUT/read-back, and exact `new` PUT/read-back. On any failed write or verification, the adapter restores and verifies `old+new`; do not continue while the observed context/App-ID set differs. The disposable policy-transition drill exercises this same adapter with a fake transport and makes no external request.

## Sole human production ceremony

The operator presents the exact repository, merged commit SHA, artifact SHA-256, target environment, full policy epoch, source attestation ID, issue/expiry times and reason. The human verifies that tuple and makes one go/no-go decision.

On a human-controlled workstation only:

1. Create exactly one `PromotionEnvelopeV1` with `adaptive-trust-ci promotion-create` and an external private-key file whose mode is `0600`. The TTL for production is at most 900 seconds.
2. Independently verify that same file with `adaptive-trust-ci promotion-verify`, an explicit public trust store, and the exact expected tuple.
3. Submit that existing file once with `adaptive-trust-ci promotion-submit`, a unique idempotency key and correlation ID. Never regenerate or refresh it after a mismatch.
4. The authenticated deployer repeats the exact tuple and consumes once immediately before its first production side effect.
5. Deploy only the attested bytes. Through the dedicated deployer bearer boundary, append exactly one terminal `deployment.completed`, `deployment.failed` or `deployment.reconciled` event to `/promotions/{promotion_id}/consume/{operation_id}/terminal`.

The human signs once; offline verification, submission and atomic consumption do not add signatures. No legacy PR approval is part of this ceremony.

## Abort conditions

Abort with zero production writes on any mutable/missing provenance, digest mismatch, wrong repository/environment/policy, expired or future envelope, unknown/revoked/wrong-scope key, signature failure, replay, consumed authority, kill switch, rate limit, or database/policy/trust/provenance outage. Never recover by changing the tuple, accepting an old envelope, deleting nonce/consumption history or bypassing exact-SHA verification.

## Crash and reconciliation

A crash before consume leaves no production authority consumed and no production side effect is allowed. A crash after consume is intentionally fail-closed: do not unconsume or automatically request another envelope. Reconcile the external deployment system by the unique operation ID, append the terminal event, and escalate inconsistent state.

Before rollout, run `trust-ci/scripts/postgres-backup-restore-drill.sh` with the pinned disposable images and `trust-ci/scripts/policy-transition-drill.sh`. The recovery drill verifies the backup manifest and SHA-256, restores into an isolated database, checks migration/state integrity and runtime-role access, and proves that consumption and its terminal outcome remain single-use.

Also run `trust-ci/scripts/clean-runner-simulation.sh`. It must pass with no checkout `.venv` and a Docker sentinel that always fails. The authoritative repository sandbox records `execution_capability=repository-sandbox` and excludes host orchestration; the trusted host receipt records `execution_capability=trusted-host` and owns the pinned database/recovery bundle. Never expose the host Docker socket to repository commands.

## Rollback

Activate the production kill switch first. Restore the previous reviewed application image or forward-fix with migration 005+; never edit/down-migrate migration 004 or delete promotions, nonces, consumptions or audit events. After database restore, reconcile every consumed operation ID against external deployment history before re-enabling production.

If Trust CI policy or branch protection must be rolled back, prove the replacement App-owned epoch check on a disposable PR, then run the same add-before-remove adapter with current and replacement contexts reversed. That control-plane recovery preserves at least one App-owned gate, never creates production authority and never introduces a PR signature.
