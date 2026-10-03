# Release plan — Implement read-only authenticated Trust CI current-authority snapshot endpoint and bounded store queries with current public approval validation and short validity bound.

## Deployment

Source delivery only. No installation, runtime activation, deployed-policy/holdout update, production write or release publication is performed. The isolated PR requires the App-owned exact-head Trust CI check and applicable externally signed approval scopes.

Future separately authorized installation must mount the current policy, its exact holdout tree, the public approval trust store, and a CI attestation public PEM. Configure `TRUST_CI_ATTESTATION_PUBLIC_KEY_PATH` to an absolute regular non-symlink public file (including non-symlink parents), at most 16 KiB; alternatively the application factory may receive a current public-only provider. Missing, unreadable or invalid public evidence returns 409. There is no fallback to approval keys or a CI private signing key. Existing compose/settings/worker/examples are intentionally untouched; this prerequisite is not a claim that the endpoint is installed or available on the deployed service.

## Feature flags / staged rollout

The endpoint is additive and uses the existing read bearer token. Public evidence sources are loaded independently of cached startup policy/trust injection. Validate synthetic canary reads before any separately delegated installation. The kill switch disables authority snapshots.

## Metrics and alerts

Existing metrics and health behavior remain unchanged. The consumer-visible signals are authenticated 200 for a complete exact-job observation, 401 for missing/incorrect read token and 409 for unavailable/stale/invalid/over-bound authority. No high-cardinality endpoint metrics or secret-bearing error logs are introduced.

## Go/no-go criteria

Require focused tests, full PR verification, independent code/test/security/release review, current fingerprint-bound local receipts, then external App-owned exact-head Trust CI plus signed approval scopes. A snapshot is observation only and cannot replace branch protection, a Check Run, or a human security approval. Consumers must re-read after `valid_until` or an authority change. Validity is at most 60 seconds and every selected approval expiry/key not-after/revocation cutoff. The current policy schema has no timestamp-validity field; current policy binding and holdout digest are instead rechecked before return.
