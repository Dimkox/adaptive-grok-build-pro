# Implementation — M0.2 SHA-change slice

Change `20260824-m0-2-sha-change-invalidation-on-draft-pr-5-beee95` / route `beee95e0b3c6`.

## Done

1. Transitioned change `approved` → `implementing`.
2. Explicit `git add --` of 85a17e `code-review.md`, `test-review.md`, `state.json`, and this `beee95` package. Leftovers `9d97f8` / `37bf04` / `33e0c2` not staged. Commit `ce03c87`. No `decisions.md` / activation-report edit.
3. `python3 -m unittest trust-ci.tests.test_m0_invariants` OK (8 tests). `python3 scripts/grok_verify.py --mode pr` PASS.
4. Delegated grant `git-push-branch` resource `milestone/m0-live-trust-authority` (TTL 30). Push `1fc9420..ce03c87`.
5. Loopback HMAC from api container (secret never printed): HTTP 200, `job_id=54e2c6f4-ed18-45dd-abfb-2074fb8ee96a`, `created=true`.
6. Proved Check Run `97390635614` remains on `1fc9420`; new Check Run `97406973020` on `ce03c87` with matching `external_id`.
7. `health/ready` 200. No compose down, no PATCH checks, no `main` protection, no merge, no GitHub webhook registration.

## Not this slice

M0.2 complete would still require later policy-epoch pass + human Ed25519 scopes. `action_required` is success of publication only.

This file is uncommitted on purpose (infinite-SHA ruling).
