# Trust CI activation report (operator-safe)

Fill after live M0.2/M0.3. Empty fields stay `UNKNOWN`. Never paste PEM, JWT, webhook secret, admin token, or human approval private keys.

Listener facts from `claw` (`127.0.0.1:18080` → container 8080). Worker env App ID `4694114` and Installation ID `156003193` are set (gitignored). Nested DinD remains unused; worker runs via an untracked host-socket overlay. Live intake is GitHub App `pull_request` via Funnel `https://claw.taild9f611.ts.net/webhooks/github`. M0.2 webhook stage is closed; M0.3 binds protected `main` to that App-owned check. Human Ed25519 / attestation / mutation / policy retitle remain **not done**. Host `:8080` remains SearXNG. `main` is protected (`adaptive-trust-ci/verified@6737355947c2`, `app_id` 4694114).

SHA-change history: Check Run `97390635614` on `1fc9420` (local HMAC); `97406973020` on `ce03c87` (local HMAC); GitHub webhook `97524725228` on `9d56734d9050fb3cb2543565084bcb83ded5c73b`; later GitHub webhook `97527445754` on `56f5462e78c7ebc0ab7e69fbffd5c1371ff7af78`; current GitHub webhook `97529209576` on `ac01326a4a3fde1d0630e621da51ef67379da191` job `53870ce3-951c-4247-afe9-88969be5dc98`. See `engineering/changes/20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95/evidence/sha-invalidation.md`.

| Field | Value |
| --- | --- |
| Report date | 2026-08-24 |
| Dedicated CI host (hostname only) | `claw` |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |
| GitHub App webhook URL (inbound) | `https://claw.taild9f611.ts.net/webhooks/github` (GitHub `pull_request`/`synchronize` 200) |
| Product base SHA | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| GitHub App slug | `adaptive-trust-ci` |
| App ID | 4694114 |
| Installation ID | 156003193 |
| Policy digest (full hex) | `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5` |
| Required check name | `adaptive-trust-ci/verified@6737355947c2` |
| Disposable PR number | 5 (draft) |
| Disposable PR head SHA | `ac01326a4a3fde1d0630e621da51ef67379da191` (earlier proof SHAs `56f5462e78c7ebc0ab7e69fbffd5c1371ff7af78`, `9d56734d9050fb3cb2543565084bcb83ded5c73b`) |
| Check Run id | 97529209576 (earlier proofs `97527445754`, `97524725228`) |
| Check Run `external_id` (job id) | `53870ce3-951c-4247-afe9-88969be5dc98` (earlier proofs `5b378f31-ea7c-4333-9c09-d3ed758fdfbb`, `0e147461-6de8-415f-b712-d06b2034c735`) |
| Attestation verified offline | N/A (job needs_approval; GET 404) |
| API image `name@sha256` | `ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23` |
| Worker image `name@sha256` | `ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227` |
| Runner image `name@sha256` | `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2` |
| Holdout digest | `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8` |
| `main` protected | true |
| Protection `app_id` | 4694114 |
| Leftover Actions workflow 340420982 | disabled_manually |
| Kill switch drill | 2026-08-24 pass (on → GET /health/ready 503; off → 200; STOP unlinked) |
| Backup/restore/restart drill | 2026-08-24 pass (`backup-create` / `backup-verify` / restore-drill `--confirm-disposable` on throwaway tmpfs; `compose restart postgres` without `-v`; jobs 2=2; `/health/ready` 200) |
| Bootstrap-exception language superseded | true — see `decisions.md` 2026-08-24 M0.3 bind main (revokes 2026-08-23 M1-start / PR #2 / PR #4 because a live App-owned check exists) |
