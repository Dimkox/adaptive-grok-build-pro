# Rollback plan — Fix cancelled disposable PostgreSQL harness cleanup, orphan recovery, and timeout reporting (#128)

## Trigger conditions

Roll back the code changes if bounded process-group termination kills commands outside the verifier's owned session, if KeyboardInterrupt leaves an owned process group running, if listing overflow is mistaken for an ordinary Docker failure, if nested Trust CLI worker selection becomes coupled to the outer test worker or inherited pinned tools shadow Trust suite imports, if exact container/volume checks regress, or if timeout results become unreportable. The change creates no durable PostgreSQL schema or application data.

## Application rollback

Revert the focused changes to `adaptive_grok.util.run`, the factory disposable harness, its verifier dispatch, and the associated regressions as one unit. Do not remove existing labelled volumes during rollback; preserve them for the original TTL-bound recovery logic or manual inspection.

## Data recovery / forward-fix

There is no database migration or durable data rollback. If a disposable resource remains after rollback, allow the harness's exact nonce/label/age reaper to reclaim it after TTL. Do not use Docker prune or delete a resource based on name alone.

## Verification after rollback

Run the focused `util.run` timeout process-tree test and factory cleanup/reaper tests against the reverted behavior, then run the repository verifier only after other serialized verification work is clear.
