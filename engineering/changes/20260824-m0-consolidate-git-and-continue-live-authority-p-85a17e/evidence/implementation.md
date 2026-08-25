# Implementation — M0 consolidate git and continue live authority

Change `20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e`. Route `85a17ed2e935`. No push.

## Changed files

- `decisions.md` — unify-git / no-push ruling
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` — M0.0 boxes; kill-switch host-local pass; M0.2 webhook still open
- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` — live-gap freeze snapshot annotation
- `engineering/runbooks/trust-ci-activation-report.md` — Check Run ids kept; kill-switch 2026-08-24 pass; attestation N/A 404
- `trust-ci/tests/test_m0_invariants.py` — report exists; no PEM markers; Check Run id not UNKNOWN; local HMAC / not done
- this change package and `engineering/changes/20260824-the-user-sent-a-message-while-you-were-working-u-3e6166/`

## Commands (no secrets)

- Attestation: `docker compose --project-name adaptive-trust-ci exec -T api python` GET `/attestations/1b63d10b-90c1-498a-97b8-7b5e0ea76aec` **HTTP 404**
- Kill-switch: host STOP at `trust-ci/runtime/control` (API uid cannot write STOP). On → `GET http://127.0.0.1:18080/health/ready` **503**. Off → **200**. CLI `kill-switch status` **off**. No `compose down -v`.
- `python3 -m unittest trust-ci.tests.test_m0_invariants`
- `python3 scripts/grok_verify.py --mode pr`

## Residual risk

- Worker overlay still mounts host docker.sock (claw-only exception). Public HTTPS webhook absent. SHA-change not done (no push). Policy/holdout retitle and human Ed25519 requeue blocked. Leftover change packages stay unstaged.

## Rollback

- Revert the docs/test commit on `milestone/m0-live-trust-authority`. Live compose and Check Run `97390635614` on SHA `1fc9420` are unchanged by this slice. Kill-switch is off; do not leave STOP in place.
