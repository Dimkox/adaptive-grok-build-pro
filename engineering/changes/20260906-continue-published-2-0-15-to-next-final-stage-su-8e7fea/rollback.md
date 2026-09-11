# Rollback

## Trigger conditions

- Any server command fails to import after dispatch.
- Envelope bytes/schema or `/approvals` behavior diverges.
- Later path/policy/holdout/workspace/runner tests regress.
- New CLI tests read or write key material.

## Application rollback

Revert the successor commit or close the successor PR. No image/policy/holdout change is required; API/worker keep running on current images until a later rebuild.

## Data recovery / forward-fix

None. No SQL, no envelopes rewritten. Old envelopes remain verifiable.

## Verification after rollback

`python -m adaptive_trust_ci.cli --help` may again require FastAPI (pre-fix behavior). Unmodified Trust CI suites must still pass.
