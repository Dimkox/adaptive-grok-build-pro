# M0.2 SHA-change invalidation on draft PR 5

Change ID: `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95`
Route: `beee95e0b3c6`
Write owner: `general_implementer`

## Problem

User «да ле е» (далее) after the named next slice: push local `ca1e88a` (plus leftover 85a17e reviews) onto already-open draft PR #5, then loopback HMAC so a **new** App-owned Check Run binds to the new SHA. Check Run `97390635614` must stay on `1fc9420`.

## Outcome

Draft PR #5 head is a descendant of `ca1e88a`. GitHub shows Check Run `97390635614` only on `1fc9420`. The new head has a **different** Check Run id, name `adaptive-trust-ci/verified@6737355947c2`, App `4694114`, `external_id` = new `job_id`. Not M0.2 complete.

## Scope

### In scope

- Commit 85a17e reviews/state + this change package (explicit paths)
- `git-push-branch` `milestone/m0-live-trust-authority` only
- Loopback HMAC `pull_request`/`synchronize` for GitHub head after push
- Prove old vs new Check Runs; record ids in `evidence/sha-invalidation.md`

### Out of scope

- Public webhook, `gh pr edit`, merge, mark ready, protect `main`
- Policy/holdout retitle, human Ed25519, PEM, GitHub Actions
- Updating activation-report/plan/`decisions.md` with new ids **and pushing that** (infinite SHA). Product docs stay on `1fc9420` this slice.
- Leftover `9d97f8` / `37bf04` / `33e0c2`
- Tracked `trust-ci/compose.yaml`

## Controller rulings

1. «далее» after the offered push+HMAC slice **is** `git-push-branch` on this milestone only. Not merge, not `main`.
2. Infinite-SHA: **(a)** — new ids only in this package evidence; do not push a docs commit that contains them.
3. Analysis wave: route listed 4; user asked for 10; hook **blocked** names outside `allowed_agents`. Extra allowed readers (`code_reviewer`, `test_reviewer`, grants `docs_researcher`) were added. 10 is a ceiling, not a quota; do not pad with unmatched specialists.
