# Rollback plan — M1 Typed Intent Evidence Rebuild

## Trigger conditions

Legacy spec/attestation incompatibility, validator bypass, false-green criterion coverage, or Trust CI runner instability.

## Application rollback

Revert the M1 source commits through a pull request. Keep deployed Trust CI on its previous immutable policy/holdout/image until a separately approved rollout is proven.

## Data recovery / forward-fix

No schema migration or destructive data write is included. Stored legacy attestations remain byte-verifiable; any new optional metadata can be ignored by old readers.

## Verification after rollback

Run root and Trust CI suites, compileall, PR-mode verification, and confirm the current App-owned exact-SHA check under the deployed policy epoch.
