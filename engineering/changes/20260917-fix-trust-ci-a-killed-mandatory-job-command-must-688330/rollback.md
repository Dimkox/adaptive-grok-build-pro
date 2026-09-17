# Rollback plan — interrupted Trust CI commands (#103)

## Trigger conditions

- A killed or timed-out command must be treated as an ordinary verification verdict again (i.e. the maintainer
  rejects the new vocabulary), or
- the classification proves wrong in a way that misleads an operator — for example an in-container OOM
  recorded as `aborted-by-signal` where the maintainer needs it to read `verification-failed`, or
- `result.abort` or the new check title breaks a downstream reader that parsed the previous strings.

## Application rollback

`forward_fix` with at most one step: revert the single commit. Nothing else has to move — there is no
migration, no schema object, no config key, no feature flag, no new module and no new dependency, so a plain
`git revert` restores `failure_code='verification-failed'` for every non-passing run and stops writing
`result.abort`. As with rollout, the deployed worker only follows the revert when its image is rebuilt or
relaunched under separate authority.

## Data recovery / forward-fix

- Rows written by the fixed code carry `status='failed'` and a `failure_code` outside the old set. Readers
  that only test `status` or `status == 'passed'` are unaffected; a reader that requires
  `failure_code == 'verification-failed'` to consider a job failed would have to be the one reverted, and the
  corrective action is the revert above, not SQL.
- Deliberately no `UPDATE`/`DELETE` against `trust_ci_jobs` — rewriting the trust record is the destructive
  operation this change exists to avoid. If a specific job's classification is disputed, re-gate its exact
  head with a fresh job and let the newer row speak.
- The `result.abort` member is additive inside `result jsonb`: an old binary ignores it, and no column,
  constraint or index was introduced that a rollback would leave orphaned.

## Verification after rollback

1. `git diff --check <base>..HEAD` clean and `git status --porcelain` shows no residue under `trust-ci/`.
2. `make trust-ci-test` on the reverted tree: the pre-existing suite is green and only the #103 tests added in
   the reverted commit are gone (they were added by that commit, so no test is left asserting the removed
   behavior).
3. `python3 scripts/grok_verify.py --mode pr` green, and the App-owned `adaptive-trust-ci/verified@<policy-sha12>`
   check re-run on the new exact head.
4. Confirm no live job row is left mid-flight: terminal rows keep their recorded `failure_code`; the rollback
   changes only what future finishes write.
