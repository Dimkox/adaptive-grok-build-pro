# Rollback plan — Fix issue157 repository language classifier: bounded Swift and other language signal detection, symlink-safe manifests, truncation and unknown reporting without suppressing detected signals.

## Trigger conditions

Unexpected specialist routing, classifier exceptions, unintended unsafe reads, undisclosed truncation or downstream profile incompatibility.

## Application rollback

Revert the responsible isolated classifier PR through a new PR. This restores the earlier source behavior without rewriting shared history or touching retained dirty trees.

## Data recovery / forward-fix

No persisted schema migration or production write. A forward fix may adjust the bounded scanner after its own exact-head tests/reviews; previously persisted route profiles remain historical evidence and do not acquire new authority.

## Verification after rollback

Run the existing router tests and full applicable verifier on the rollback candidate, then independent review and exact-head Trust CI before merge.
