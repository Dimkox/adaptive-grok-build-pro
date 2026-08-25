# Architecture — M0 consolidate git and continue live authority proof

Authority: `evidence/analysis-architect.md` plus controller ruling in `brief.md`.

## Current behavior

Live claw already has postgres+api+worker. Tracked `trust-ci/compose.yaml` still documents isolated DinD. Untracked overlay mounts host docker.sock on worker/loader only. First App-owned Check Run exists on PR #5 SHA `1fc9420` via loopback HMAC, conclusion `action_required`. Git HEAD does not record that.

## Proposed behavior

No product runtime change. Docs and one live kill-switch drill. Tracked compose unchanged.

## Components and boundaries

| Plane | This slice |
| --- | --- |
| API | Kill-switch file on `./runtime/control` (`/run/adaptive-trust-ci/STOP`). Probe `/attestations/{id}` 404. |
| Worker | Untouched. Overlay residual stays claw-only exception. |
| Runner | Untouched (`network=none`, no sock). |
| Git | Local commit on the milestone branch. No push. |

Policy/holdout/images/Postgres catalog/keys stay outside the PR trust domain.

## Data flow

Kill-switch on writes STOP → API returns 503 on webhook/approvals/claims → off unlinks STOP → ready 200.

## Decisions

- Do not push. SHA-change waits.
- Do not edit tracked compose.
- Do not generate/read human approval keys.
- Leftover v2.0.12 / PR #4 / 2.0.10 change packages stay unstaged.

## Risks and mitigations

- Kill-switch left on 503s the live API → always off before commit; stop the slice if off fails.
- Protected-path grant consumed by first mutation (`mistakes.md` 2026-08-23) → batch `decisions.md` + `test_m0_invariants.py` or re-mint.
- Accidental `git add -A` → explicit path list only.
