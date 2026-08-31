# Release plan — Fix the M3 branch after accepted M2 changed: merge exact M2 head 022411b05924618cfde0cb97b8c8aff4955e6013 into M3, resolve integration conflicts without changing M3 requirements, add or update regression tests if needed, run verification and reviews, and prepare PR #11 for fresh exact-SHA Trust CI; no external writes without exact delegated grants.

## Deployment

No deployment. Deliver only as a stacked source pull request against accepted M2,
after separate explicit authorization for push/PR update.

## Feature flags / staged rollout

None. This change adds no runtime behavior.

## Metrics and alerts

Exact parent/ancestor checks, final tree fingerprint, local verifier status, review
receipt count, and later App-owned exact-head Trust-CI check state.

## Go/no-go criteria

Go for local readiness only when the final head contains exact M2, focused and
full checks pass, and code/test/security receipts bind one current fingerprint.
Go for merge only after separately authorized PR delivery, the required App-owned
exact-SHA policy-epoch check, and all deployed-policy signed scopes. Local evidence
and grants never substitute for those external gates.
