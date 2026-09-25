# Rollback plan — Fix issue 227: inherited GIT_DIR or GIT_WORK_TREE can redirect repository identity and let a valid local grant authorize git push to a foreign pushurl. Add root-bound Git probes and explicit fail-closed denial. Never execute git push or access the network.

## Trigger conditions

- Root-bound probes select the wrong checkout, clean grant behavior regresses, or
  denial leaks selector values.

## Application rollback

Do not restore the vulnerable allow path. Disable delegated agent Git pushes and
forward-fix the selector handling on a new exact head.

## Data recovery / forward-fix

No data migration exists. Local grants bound to a changed tree naturally become
stale and must not be reused.

## Verification after rollback

Re-run the P0 foreign-checkout denial and root-bound fingerprint tests, then the
full route verifier and independent security review.
