# Rollback plan — Fix issue #167: select focused static SEO landing verification for landing-only changes while retaining full PR verification for runtime, contract, Trust CI, package, architecture, or workflow changes, with regression tests.

## Trigger conditions

Rollback or forward-fix if focused mode ever accepts a mixed/unknown path, executes more than the named landing contract, mishandles multiple landing directories, or changes the full PR path.

## Application rollback

Revert the issue #167 verifier, workflow allowlist, regression, and documentation changes as one change. This is source-only and has no runtime or deployment rollback.

## Data recovery / forward-fix

No data recovery is required. Prefer a forward fix to the classifier/tests, then rerun targeted tests and invalidate any stale local receipt. Do not alter deployed Trust CI policy or approvals.

## Verification after rollback

Confirm `--mode pr` remains available and full, focused mode is absent or fails closed, targeted tests pass, and the exact-SHA App-owned Trust CI check remains the merge authority.
