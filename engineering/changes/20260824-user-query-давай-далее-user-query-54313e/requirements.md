# Requirements — M0.3 bind main

## Acceptance criteria

- [x] Given leftover Actions workflow `trusted-ci` id `340420982`, when GET catalog, then `state=disabled_manually`.
- [x] Given `GET /repos/Dimkox/adaptive-grok-build-pro/branches/main/protection`, then required check is `adaptive-trust-ci/verified@6737355947c2` with `app_id` 4694114, `strict` true, `enforce_admins` true, `allow_force_pushes` false, `allow_deletions` false.
- [x] Given a user token POST of Checks API same-name Check Run, then HTTP 403 `You must authenticate via a GitHub App`.
- [x] Given a user (`Dimkox`, id 4751099) commit status `context=adaptive-trust-ci/verified@6737355947c2` `state=success` on `ac01326`, when GET PR #5, then `mergeable_state=blocked` and App Check Run `97529209576` stays `action_required` / `app.id=4694114`.
- [ ] Docs: supersede README L11 bootstrap-exception as current-state; add a 2026-08-24 `decisions.md` revoke entry (keep 2026-08-23 history); fill activation-report cells; tick plan M0.3 boxes except merge.
- [ ] Characterization tests pin protected `main` + `app_id` 4694114 + disabled workflow wording; keep M0.2 historical “Do not protect `main`” string.

## Failure and edge cases

- GitGuardian `app.id=46505` success on a **different** name is not actor-mismatch proof.
- Do not PATCH App Check Run `97529209576` to success.
- Do not merge PR #5 while `conclusion=action_required`.
- Do not `funnel reset`, grant Administration, or mint human approval keys.

## Non-functional requirements

- Security: no PEM/JWT/webhook secret/admin token/human private key in git or chat.
- Reliability: Funnel + socat stay up.
- Observability: activation report lists IDs, not secrets.
