# Rollback plan — Repair L5 current landing source binding

## Trigger conditions

Current exact source fails rendering, protected stylesheet identity drifts,
artifact inventory is incomplete/non-deterministic, or a provider/publisher/
target effect is observed.

## Application rollback

Revert the single repair commit. With the current landing clone the prior code
then fails closed at `source_identity`; no data or target rollback is needed.

## Data recovery / forward-fix

No migration or persistent data change. A future source advance requires a new
exact pin review; never follow the branch implicitly or dual-accept epochs.

## Verification after rollback

Confirm old code rejects the current source before workspace creation,
published `v2.0.14` checksums remain unchanged, landing worktree remains clean,
and no provider, publisher, or live target was touched.
