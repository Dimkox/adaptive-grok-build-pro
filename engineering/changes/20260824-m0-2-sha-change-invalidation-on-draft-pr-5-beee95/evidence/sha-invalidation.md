# M0.2 SHA-change invalidation evidence

Operator-safe ids only. No secrets, JWT, PEM, or HMAC signature.

## Push

- Branch: `milestone/m0-live-trust-authority`
- Pre-push HEAD: `1fc942065a124ce75659bd082519d8ebc37774e8`
- Pushed commit: `ce03c87b3d9b8767105c01270869e33b50af56df` (`ops: record M0.2 SHA-change slice evidence before live proof`)
- `git push origin milestone/m0-live-trust-authority` (no force, not `main`)
- Draft PR #5 `head.sha` after push: `ce03c87b3d9b8767105c01270869e33b50af56df` (≠ `1fc9420`)
- Base remains `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` / `main`

## Loopback HMAC

- Event: `pull_request` / `synchronize`
- HTTP 200
- `job_id`: `54e2c6f4-ed18-45dd-abfb-2074fb8ee96a`
- `created`: true
- job `status`: queued (then completed on GitHub as `action_required`)

## Check Runs

| SHA | Check Run id | name | App | external_id | conclusion |
| --- | --- | --- | --- | --- | --- |
| `1fc942065a124ce75659bd082519d8ebc37774e8` | `97390635614` | `adaptive-trust-ci/verified@6737355947c2` | `4694114` | `1b63d10b-90c1-498a-97b8-7b5e0ea76aec` | `action_required` |
| `ce03c87b3d9b8767105c01270869e33b50af56df` | `97406973020` | `adaptive-trust-ci/verified@6737355947c2` | `4694114` | `54e2c6f4-ed18-45dd-abfb-2074fb8ee96a` | `action_required` |

Old Check Run id is unchanged and still listed only on the old SHA. New Check Run id ≠ old; `external_id` equals the new `job_id`.

`action_required` / needs_approval on the new SHA is expected (publication succeeded; no forged approval).

`GET http://127.0.0.1:18080/health/ready` → 200.

This file is intentionally uncommitted so it does not move PR head.
