# Tasks

- [ ] Fill remaining change-package fields; transition implementing.
- [ ] `git add --` explicit in-scope paths (85a17e reviews/state + this package). Commit. Do not add leftovers.
- [ ] `python3 scripts/grok_verify.py --mode pr`
- [ ] Mint `git-push-branch` for `milestone/m0-live-trust-authority` on that fingerprint. `git push -u origin milestone/m0-live-trust-authority`
- [ ] Re-fetch PR #5 `head.sha`. HMAC synchronize from **inside api container**. Print status/job_id/created/job status only.
- [ ] Prove old SHA still has Check Run `97390635614`; new SHA has a different App-owned Check Run. Write `evidence/sha-invalidation.md`. Do not commit/push that file this slice if it would move PR head again before HMAC; if it is written after HMAC, leave it unpushed.
- [ ] Write `evidence/implementation.md`. Stop. No merge, no `main`, no webhook registration.
