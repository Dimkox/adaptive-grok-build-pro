# Requirements — P0 Trust CI control plane activation

## Acceptance criteria

- [ ] Given HEAD `feat/trust-ci-control-plane`, when the handoff baseline commands run, then root tests, Trust CI tests, compileall and `grok_verify --mode pr` pass on the recorded SHA.
- [ ] Given `TRUST_CI_TEST_DATABASE_URL` against disposable PostgreSQL, when the Trust CI suite runs, then previously skipped live tests execute and pass.
- [ ] Given two workers, lease expiry, heartbeat, attempt exhaustion, nonce replay, attestation reconnect and PostgreSQL restart, when the live harness runs, then each scenario passes.
- [ ] Given built API/worker/runner/holdout artifacts, when policy and compose env are written, then every image reference is `name@sha256:<64 hex>` and no mutable tag is used for deploy.
- [ ] Given the GitHub App, when it is installed on `Dimkox/adaptive-grok-build-pro`, then permissions are Checks read/write, Contents read, Pull requests read; the App key is worker-only; the webhook secret is API-only.
- [ ] Given a pull-request webhook, when PR #2 is synchronized, then PostgreSQL stores the exact SHA job, the worker claims one lease, holdout runs outside checkout, source mutation still fails the job, a signed attestation is stored, and the App-owned policy-epoch check appears on that SHA.
- [ ] Given a successful App-owned check, when branch protection is applied, then `main` requires PRs, strict up-to-date, the exact policy-epoch check bound to the App ID, admin enforcement, conversation resolution, linear history, and disabled force-push/deletion.
- [ ] Given the repository tree, when inspected, then `.github/workflows/` does not exist.

## Failure and edge cases

- Invalid webhook HMAC → HTTP 401.
- Missing approval on `trust-ci/**` → `needs_approval`, never success.
- Replay nonce → `ReplayError`.
- New commit or policy digest → old approval and old check cannot satisfy the new SHA/epoch.
- Command exit 0 after mutating tracked source → job failed.

## Non-functional requirements

- Security: fail-closed; no GitHub credentials in runner; no human private key in the agent environment.
- Reliability: jobs and attestations survive API/worker/PostgreSQL restart; leases reclaim once and are attempt-limited.
- Observability: health endpoints, job events, signed attestations, Check Run IDs.
