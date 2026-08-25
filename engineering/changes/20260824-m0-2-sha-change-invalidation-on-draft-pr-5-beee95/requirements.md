# Requirements — SHA-change invalidation

## Acceptance

- [ ] Explicit commit includes 85a17e `code-review.md`, `test-review.md`, `state.json`, and this `beee95` package. Never `git add -A`. Never add `9d97f8` / `37bf04` / `33e0c2` / env / PEM / overlay host file.
- [ ] `git push` of `milestone/m0-live-trust-authority` only, after a fingerprint-bound `git-push-branch` grant on that branch name.
- [ ] PR #5 `head.sha` equals the pushed commit and is not `1fc942065a124ce75659bd082519d8ebc37774e8`.
- [ ] HMAC POST `http://127.0.0.1:18080/webhooks/github` returns 200 with `created: true` (or honest `created: false` only if that exact new SHA was already posted) and a **new** `job_id`.
- [ ] `gh api .../commits/1fc942065a124ce75659bd082519d8ebc37774e8/check-runs` still lists Check Run `97390635614`, App `4694114`, `external_id=1b63d10b-90c1-498a-97b8-7b5e0ea76aec`.
- [ ] `gh api .../commits/<NEW-HEAD>/check-runs` lists a **different** Check Run id, name `adaptive-trust-ci/verified@6737355947c2`, App `4694114`, `external_id` = new `job_id`.
- [ ] No PEM, webhook secret, JWT, or signature in git/chat. `/health/ready` stays 200. `main` unprotected. PR #5 stays draft.
- [ ] `python3 scripts/grok_verify.py --mode pr` after the pre-push commit.

## Non-goals

Forge success, user-token check create, Actions, webhook registration, `branch-protect`, second push of activation-report ids.
