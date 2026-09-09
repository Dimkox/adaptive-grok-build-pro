# Rollback plan — Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

## Trigger conditions

Any regression that masks a live/unknown survivor, fails to preserve an original error after proven zombie cleanup, or weakens TERM/KILL/reap containment.

## Application rollback

One reviewed forward-fix/revert of the narrow classifier and its regression tests; do not revert to ignoring group presence.

## Data recovery / forward-fix

No migration, data recovery, external write, or deployment is involved.

## Verification after rollback

Run zombie-only, live/unknown, descendant-cleanup, and focused Trust-CI workspace tests under the same read-only runner constraints.
