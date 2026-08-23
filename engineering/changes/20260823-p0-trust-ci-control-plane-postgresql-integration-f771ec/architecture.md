# Architecture — Trust CI remaining activation

## Current behavior

The `trust-ci/` service is implemented: PostgreSQL schema, HMAC webhooks, GitHub App JWT, Checks API, policy-epoch names, app-bound protection payload, isolated runner, holdout, attestations, API/worker split. It is not yet live. HEAD `04348db` local baseline is red. No GitHub App, webhook, or `main` protection exist.

## Proposed behavior

Keep the existing control-plane design. Repair baseline mismatches, execute the live PostgreSQL harness, pin immutable images, activate a dedicated GitHub App, deploy on this host, prove the App-owned check on PR #2, then bind branch protection.

## Components and boundaries

Trusted (outside PR checkout): deployed API/worker images, mounted `policy.json`, holdout bundle, PostgreSQL, worker-only CI Ed25519 key, worker-only GitHub App RSA key, API-only webhook secret, API-only human public trust store, app-bound branch protection.

Untrusted: repository content at the PR SHA, local receipts, delegated grants, prompts, hooks, agent output.

API has no App key and cannot publish a successful check. Worker has no webhook secret or human trust store. Runner has `--network none`, no secrets, no Docker socket.

## Data flow

GitHub PR webhook → API HMAC + allowlist + idempotent enqueue → PostgreSQL job/lease → worker claim (`FOR UPDATE SKIP LOCKED`) → exact-SHA checkout → holdout → no-network commands → source-mutation check → Ed25519 attestation → App Check Run `adaptive-trust-ci/verified@<policy-sha12>`.

## Decisions

- User-approved source is `GROK_BUILD_HANDOFF.md`; this change does not reopen design.
- Route `d2ba49e0570d` write owner is `general_implementer`. Reviews are `code_reviewer` and `test_reviewer` only if product files change.
- Example policy may keep an explicit runner-digest placeholder; deployed policy must use a real digest.
- Branch protection runs only after the App-owned check is observed on the exact SHA.
- This turn is a daemon compile, not HANDOFF §3 pin: two-file compose `build` with no push and no `up`. Freeze the reviewed docs/toolchain tree. Do not add Makefile/script/test product edits.
- Smoke env-file lives at `/tmp/adaptive-trust-ci-build.env`, not `trust-ci/.env` (protected path). API/worker/runner values are mutable local `:2.1.0` tags. Measure `python:3.12-slim-bookworm` after `docker pull`; do not invent hex.
- On Docker Engine 29 a non-empty `RepoDigests` that equals `.Id` is still not a registry pin. Inspect `.Id` plus JSON `RepoTags`/`RepoDigests`. Never copy that string into `policy.example.json` or `.env.example`.
- Example holdout digest stays test-locked to `trust-ci/holdout.example`. Production holdout waits: `/srv` and `/opt` bundles are absent.
- Do not commit leftover `engineering/changes/20260817-вычисти*`. Do not read `trust-ci/runtime/*.pem`. GitHub App, TLS, `compose up`, and `branch-protect` stay out of slice until separately named.
- User named registry `ghcr.io/dimkox` for docker-push (option 1). Pin path is retag already-built `adaptive-trust-ci-{api,worker,runner}:2.1.0` and `docker push` those three names. Do not run `supply-chain-release.sh` (cosign absent). Keep only inspect RepoDigests that start with `ghcr.io/dimkox`. Write `name@sha256:` only to untracked `/tmp` env. Tracked examples stay `REPLACE_WITH_*`. Fail-closed on 401/403 or hostless digests. Do not `compose up`.

## Risks and mitigations

- This host already binds `127.0.0.1:8080` (searxng). Deploy Trust CI on a free loopback port and HTTPS reverse proxy, not by stealing existing services.
- GitHub App creation requires a browser/manifest conversion; do not invent App credentials.
- Human approval private keys stay off this agent environment.
- Public webhook intake needs valid TLS; do not register HTTP-only GitHub webhooks.
