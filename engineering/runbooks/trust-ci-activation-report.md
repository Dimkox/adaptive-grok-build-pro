# Trust CI activation report (operator-safe)

Fill after live M0.2/M0.3. Empty fields stay `UNKNOWN`. Never paste PEM, JWT, webhook secret, admin token, or human approval private keys.

Listener facts below are operator-safe M0.1 evidence from `claw` (`127.0.0.1:18080` → container 8080). Worker env App ID `4694114` and Installation ID `156003193` are set (gitignored). Compose-up of `docker-engine` + `runner-loader` + `worker` was issued; `docker-engine` is restarting unhealthy (`rootlesskit: fork/exec /proc/self/exe: operation not permitted`), so `runner-loader` and `worker` stayed `Created`. Webhook stays blocked (no public HTTPS). Host `:8080` remains SearXNG.

| Field | Value |
| --- | --- |
| Report date | 2026-08-24 |
| Dedicated CI host (hostname only) | `claw` |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |
| Product base SHA | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| GitHub App slug | `adaptive-trust-ci` |
| App ID | 4694114 |
| Installation ID | 156003193 |
| Policy digest (full hex) | `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5` |
| Required check name | `adaptive-trust-ci/verified@6737355947c2` |
| Disposable PR number | UNKNOWN |
| Disposable PR head SHA | UNKNOWN |
| Check Run id | UNKNOWN |
| Check Run `external_id` (job id) | UNKNOWN |
| Attestation verified offline | UNKNOWN |
| API image `name@sha256` | `ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23` |
| Worker image `name@sha256` | `ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227` |
| Runner image `name@sha256` | `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2` |
| Holdout digest | `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8` |
| `main` protected | false |
| Protection `app_id` | UNKNOWN |
| Leftover Actions workflow 340420982 | UNKNOWN (must be disabled by M0.3) |
| Kill switch drill | UNKNOWN |
| Backup/restore/restart drill | UNKNOWN |
| Bootstrap-exception language superseded | UNKNOWN |
