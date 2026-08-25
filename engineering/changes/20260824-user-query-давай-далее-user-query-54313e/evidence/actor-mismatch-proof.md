# M0.3 live proofs (2026-08-24)

No secrets. Did not merge PR #5. Did not execute force-push or delete of `main`.

## GET `branches/main/protection`

- `required_status_checks.strict`: true
- `checks`: `[{ "context": "adaptive-trust-ci/verified@6737355947c2", "app_id": 4694114 }]`
- `enforce_admins.enabled`: true
- `allow_force_pushes.enabled`: false
- `allow_deletions.enabled`: false
- `required_linear_history.enabled`: true

## Leftover Actions workflow `340420982`

- name: `trusted-ci`
- path: `.github/workflows/trusted-ci.yml`
- state: `disabled_manually`

## Actor mismatch

1. User-token `POST /check-runs` same name → HTTP **403** `You must authenticate via a GitHub App.`
2. User-token `POST /statuses/ac01326a4a3fde1d0630e621da51ef67379da191` `context=adaptive-trust-ci/verified@6737355947c2` `state=success` → status id **52802341946**, creator `Dimkox` / `4751099` / `User`.
3. Combined commit statuses: `state=success` (the spoof).
4. App Check Run **97529209576** still `conclusion=action_required`, `app.id=4694114`, slug `adaptive-trust-ci`.
5. GitGuardian **97529197793** `app.id=46505` different name — not this proof.
6. PR #5: draft, `mergeable=true`, `mergeable_state=blocked`.

Same check **text** from a non-4694114 actor does not satisfy protection.
