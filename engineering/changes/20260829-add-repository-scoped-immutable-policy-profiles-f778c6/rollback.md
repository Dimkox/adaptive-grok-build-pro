# Rollback plan — Add repository-scoped immutable policy profiles to the Python trust-ci webhook API and worker, selecting commands and holdout by exact repository, binding jobs to the selected profile digest, rejecting unknown repositories, and preserving schema-version-1 behavior with automated tests

## Trigger conditions

- Profile lookup executes or attempts commands from another repository.
- Legacy digest/check compatibility changes unexpectedly.
- API and worker disagree on a job-bound profile.
- New profile checks cannot be published or validated before branch-protection switch.

## Application rollback

Drain/stop workers with the existing kill switch, restore the previous reviewed API/worker images and legacy server-mounted policy, then restart API/workers as one unit. Do not edit job rows or reinterpret their policy digests.

## Data recovery / forward-fix

No schema rollback is required. Jobs whose digest is unavailable remain non-success; enqueue fresh exact-SHA jobs after the restored policy is active. Preserve attestations and PostgreSQL state.

## Verification after rollback

Confirm `/health/ready` reports the restored legacy digest/check name, run a signed dry-run webhook against the original repository, observe the App-owned exact-SHA check, and only then alter branch protection if it had been switched.

If paired-root validation blocks startup, restore the reviewed binaries and legacy policy together; never bypass validation by remapping a profile to another daemon root.
