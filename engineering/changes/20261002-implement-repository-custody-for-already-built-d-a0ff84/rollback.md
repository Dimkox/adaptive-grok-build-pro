# Rollback plan — Implement repository custody for already-built deterministic v2.1.0 package bytes from source e5856acfd4bc7a186f40a740b54ec86459462db5: add ZIP and checksum, update candidate state documentation and binding tests without publication or activation

## Trigger conditions

Hash, provenance, or state-binding mismatch.

## Application rollback

Remove the candidate pair and forward-fix candidate state. Do not change v2.0.19.

## Data recovery / forward-fix

Rebuild twice from the exact clean source and compare bytes before custody.

## Verification after rollback

Rerun focused structure, state, and manifest tests.
