# Requirements — M0 live Trust Authority

## Live gap (2026-08-24, no secrets)

- `main.protected = false` (protection API 404)
- repo webhooks = 0
- check-runs on `48cb973` = 0
- PR #4 merged with GitGuardian only; no `adaptive-trust-ci/verified@*`
- no Trust CI containers; leftover images `adaptive-trust-ci-*:2.1.0` not running
- App installation ID unverified (`gh` 401/403)
- leftover GitHub Actions registry workflow `trusted-ci` id **340420982** still **active** (file absent from git)
- `trust-ci/runtime/github-app-private-key.pem` filename present; not opened

## Acceptance (roadmap M0, verbatim)

- main protected = true
- required check = current `adaptive-trust-ci/verified@<policy-sha12>`
- required check app_id = adaptive-trust-ci App ID
- exact-SHA disposable PR = success
- signed attestation = independently verified
- protected-path approval flow = proven
- backup + restore + restart drill = pass
- kill switch = pass
- no GitHub Actions = true (including disable 340420982)

## Non-goals this route

- Runtime compose-up, webhook, branch-protect, PEM read
- M1 re-implementation, M2–M9, `factory/`, GitHub Actions, VERSION bump
- Using this laptop as the Trust CI host
