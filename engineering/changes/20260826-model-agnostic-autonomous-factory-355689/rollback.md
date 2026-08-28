# Rollback plan — Model Agnostic Autonomous Factory

## Trigger conditions

Any M3/M4 contract, lifecycle, fencing, capacity, budget, kill, audit, Unix-socket authentication, or trust-separation invariant fails; scope leaks into Trust CI, providers, systemd activation, bot deployment, or external writes; or exact review evidence is stale.

## Application rollback

Before M4 durable intake, revert/close the stacked feature PR normally. After durable intake, enable the factory kill switch and stop new claims; do not down-migrate or delete audit evidence. M3 v1 semantics and M4 migrations are forward-fixed with new versions.

## Data recovery / forward-fix

Back up the explicitly named `factory` schema before migration. Restore into a separate database for recovery validation or ship migration `004+`; never touch `trust_ci.*`. Bot code/service/token state is outside these PRs; token rotation is a human security operation and is not rolled back to an exposed token.

## Verification after rollback

Run the affected focused M3/M4 regression tests, the PostgreSQL recovery probe when data behavior changed, then one final verifier/review wave on the repaired exact fingerprint. Verify the kill switch, audit chain, socket auth, and Trust CI separation before resuming claims.
