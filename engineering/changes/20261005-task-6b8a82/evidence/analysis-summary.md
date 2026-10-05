# Four selected read-only analyses: coordinator synthesis

Source HEAD/base2a8e3839a469b3e05da167e9d8a807bf18e6adbf; route6b8a823793c4. All four analyses completed and returned reports out-of-band. This concise synthesis records their material conclusions, not verification/review PASS or operational readiness. No candidate product edit, full suite, credential read, deployed mutation or additional agents was performed.

## Repository explorer

WorkerSettings currently requires a numeric installation ID (settings.py112/137); Worker.build38-50 creates one GitHubAppAuth and reuses one no-argument token provider for every job. github_app.py45-91 caches one token and requests reduced permissions without repository_ids. Bind checkout and Check Run publication to the same validated installation/repository and key caches by that scope; tests should cover two installations/repositories, concurrent caches, expiry and invalidation.

webhooks.py38-63 ignores installation lifecycle and lacks stable installation/account/repository identity in jobs/models/SQL. Add durable, versioned admission bindings and lifecycle reconciliation; signed events alone may create pending intents, but credential-owning worker must confirm current GitHub access before activation. Suspension/removal must prevent enqueue, checkout and successful publication, including queued/replayed jobs.

Exact catalog admission is intentional (policy.py344-413; api.py103-106), not replaceable with wildcard repository access. A public installation requires an approved supported profile/version and effective repository-specific policy/holdout digest. api.py170-216 operator bearer currently reads globally by job ID: retain operator-only REST details/metrics initially and expose sanitized Check Runs via GitHub repository access, or implement repository-authorized tenant reads. Trusted approval keys are globally actor/scope-bound, not tenant-bound: no public customer key enrollment without additional exact repository authorization.

## Architect

Minimum public architecture reuses API/PostgreSQL/worker/sandbox; no broker, database or framework addition is needed. Add installation admission, immutable trusted public profile templates and exact generation-bound per-repository policies alongside unchanged legacy catalog semantics. One honestly described supported default profile can avoid a dashboard/login subsystem; unsupported content/layout must receive action-required/non-success, never blanket verified. Self-service does not imply arbitrary languages, networked dependency installs, custom jobs or customer secrets.

Add additive migrations and packaged SQL parity for installation state, stable repository IDs, binding/profile generation, webhook deduplication/intents, queue reservations and quotas. Enforce per-installation and global pending/running budgets atomically in PostgreSQL, fair claims and recovery/retry accounting. Bound raw request, checkout disk, retained evidence and actual log capture: current sandbox.py143-176 captures temporary output without a storage bound, while max_output_bytes limits only returned tails. Profile selection must not come from untrusted candidate commands/paths; changes require a fresh binding/epoch/job.

## Primary documentation researcher

GET /repos/{owner}/{repo}/installation requires App JWT, not a user/installation token; POST /app/installations/{id}/access_tokens should explicitly restrict repository_ids and permissions. Omitting restrictions broadens the token to the installation grant. Cache valid opaque tokens within expiration under App/host/installation/repository/permissions/generation identities; never recover from revocation by requesting broader access.

Public registration is required for other accounts; Marketplace is optional. Landing-page presence does not prove visibility/installability. Direct onboarding URL: https://github.com/apps/adaptive-trust-ci/installations/new . Setup URL installation_id can be spoofed: dashboard administration would require authenticated installer/installation association, not trusting the URL parameter. Every App receives installation and installation_repositories events; an all-to-selected transition can have an empty repositories_removed array, so reconcile current access. Suspend/delete/permission changes require authorization invalidation.

Primary references: https://docs.github.com/en/rest/apps/apps#get-a-repository-installation-for-the-authenticated-app ; https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app ; https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/about-the-setup-url ; https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation ; https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app .

## Integration architect

Source capability/examples do not deploy images, apply migrations, enable actual installations or change server authority. Compatible API/worker changes roll out with public admission closed and legacy fixed-installation behavior intact. Preserve existing factory App4694114 and exact required contextadaptive-trust-ci/verified@06ecf1c875bc; switching legacy/catalog mode or common policy fields may rotate the epoch and cannot promise unchanged protection.

After source delivery and separately authorized operation/security approval, canary one consenting foreign repository with independent profile/holdout binding, disposable exact-SHA PR, signed attestation verification, stale-SHA denial, duplicate/lifecycle tests and cross-tenant read denial. Only the foreign repository owner may authorize its protection after observing its App-owned check. Public admission/claim stop must preserve factory intake; the existing STOP is global. Rollback closes public admission, drains affected jobs and restores compatible images/profile artifacts without deleting PostgreSQL evidence or removing factory protection. New tenant failures must not expand authority.

## Current boundary

Public common-service approach is awaiting owner response; architectural written design and plan remain unapproved, route.write_agent is null. Implementation/deployment are not started. These findings define the remaining work and do not turn the already-public source into an available public service.
