# repo_explorer — facts only

Route `5b9bcb7d60d7`. Change `20260824-user-query-далее-user-query-5b9bcb`.  
No push, no merge, no PEM, no `.env`, no webhook secret.

## Git (local vs origin)

| Ref | SHA | Subject |
| --- | --- | --- |
| `HEAD` (`milestone/m0-live-trust-authority`) | `92ddbd9f69c5c560f257fd61fa9c902f43f67e50` | `ops: record M0.2 backup restore restart drill on claw` |
| `origin/milestone/m0-live-trust-authority` | `ce03c87b3d9b8767105c01270869e33b50af56df` | `ops: record M0.2 SHA-change slice evidence before live proof` |
| PR #5 `head.sha` (GitHub) | `ce03c87b3d9b8767105c01270869e33b50af56df` | same as origin |
| PR #5 `base.sha` (`main`) | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` | matches `active-route.base_commit` |

- Branch tracking: **ahead 1** of origin. Unpushed: `92ddbd9`.
- Working tree: dirty (tracked `decisions.md`, plan, activation report, `mistakes.md`, `trust-ci/tests/test_m0_invariants.py`, plus untracked change packages including this one).
- Remote: `https://github.com/Dimkox/adaptive-grok-build-pro.git`.

## PR #5

- URL: https://github.com/Dimkox/adaptive-grok-build-pro/pull/5
- Title: `M0.0: live Trust Authority on host claw (no runtime)`
- State: **open**, **draft** (`draft: true`), `merged: false`, `mergeable_state: unstable`
- Head ref: `milestone/m0-live-trust-authority`
- Commits on GitHub: 6, latest `ce03c87`. Local `92ddbd9` is **not** on the PR until a push.
- Body still claims worker not running and webhook not registered (stale vs later operator facts).

### Check runs on current GitHub head (`ce03c87`)

From `pull_request_read` `get_check_runs`:

| id | name | conclusion |
| --- | --- | --- |
| `97406973020` | `adaptive-trust-ci/verified@6737355947c2` | `action_required` |
| `97406292854` | GitGuardian Security Checks | `success` |

SHA-change history (docs, not this API page): Check Run `97390635614` remains on `1fc942065a124ce75659bd082519d8ebc37774e8`.

## Tailscale Funnel (live, this host)

`sudo -n tailscale funnel status` exit 0. Funnel **on**.

- Public origin: `https://claw.taild9f611.ts.net`
- Path: `/webhooks/github` → proxy `http://10.200.200.1:18080/webhooks/github`
- JSON: TCP 443 HTTPS true; `AllowFunnel` true for that host:443.

No `funnel reset`.

## GET `/app` events

Recorded operator fact (`decisions.md`, 2026-08-24): after App hook URL set to Funnel and GitHub `ping` redelivery HTTP 200, **GET `/app` still lists `events: []`**. `pull_request` is not subscribed via REST. Repository webhook list remains empty by policy (do not add one).

This explorer did **not** mint an App JWT or call `GET /app` / `GET /app/hook/config` (PEM unread). User `gh` tokens historically return 401 JWT decode on `/app`.

## Impact

- GitHub still evaluates PR #5 at `ce03c87`. Local `92ddbd9` + dirty tree are not Trust CI’s current PR SHA.
- Funnel path is live; App event list empty means GitHub will not POST `pull_request` until permissions/events change on the App registration (outside this repo, JWT required).
- M0.2 SHA invalidation already proven on `1fc9420` vs `ce03c87`; next SHA-bound check needs an explicit push of a new head.

## Residual

- Live GET `/app` payload not re-fetched this turn.
- Check Run `97390635614` not in the PR-head check-runs list (expected: bound to older SHA).
- Uncommitted files not on origin.
